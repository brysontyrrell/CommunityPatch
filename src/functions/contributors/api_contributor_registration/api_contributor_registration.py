import hashlib
import json
import logging
import os
import sys
import time
from urllib.parse import urlencode, urlunparse
import uuid

# Add '/opt' to the PATH for Lambda Layers
sys.path.append('/opt')

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from jsonschema import validate, ValidationError

from api_helpers import response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

CONTRIBUTORS_TABLE = os.getenv('CONTRIBUTORS_TABLE')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')
EMAIL_SNS_TOPIC = os.getenv('EMAIL_SNS_TOPIC')


def get_database_key(name):
    ssm_client = boto3.client('ssm')
    resp = ssm_client.get_parameter(Name=name, WithDecryption=True)
    return resp['Parameter']['Value']


fernet = Fernet(get_database_key(os.getenv('DB_KEY_PARAMETER')))

with open('schemas/schema_request.json', 'r') as f_obj:
    schema_request = json.load(f_obj)


def send_email(recipient, name, url):
    sns_client = boto3.client('sns')

    try:
        resp = sns_client.publish(
            TopicArn=EMAIL_SNS_TOPIC,
            Message=json.dumps(
                {
                    'recipient': recipient,
                    'message_type': 'verification',
                    'message_data': {
                        'display_name': name,
                        'url': url
                    }
                }
            ),
            MessageStructure='string'
        )
    except ClientError as error:
        logger.exception(f'Error sending SNS notification: {error}')
        raise


def write_new_contributor(id_, name, email, verification_code):
    contributors_table = boto3.resource('dynamodb').Table(CONTRIBUTORS_TABLE)

    try:
        contributors_table.put_item(
            Item={
                'id': id_,
                'display_name': name,
                'email': fernet.encrypt(email.encode()),
                'verification_code': verification_code,
                'token_id': None,
                'verified_account': False,
                'date_registered': int(time.time())
            },
            ConditionExpression='attribute_not_exists(id) AND '
                                'attribute_not_exists(display_name)'
        )
    except ClientError:
        logger.exception(
            'Error encountered writing a new entry to the icon table')
        raise


def lambda_handler(event, context):
    """
    1) Load request body
    2) Check if 'contributor' exists in database
    3) If not, create, initiate confirmation email
    """
    try:
        request_data = json.loads(event['body'])
    except (TypeError, json.JSONDecodeError):
        logger.exception('Bad Request: No JSON content found')
        return response('Bad Request: No JSON content found', 400)

    try:
        validate(request_data, schema_request)
    except ValidationError:
        logger.exception('Bad Request: One or more required fields are missing')
        return response('Bad Request: One or more required fields are missing',
                        400)

    id_ = hashlib.md5(request_data['name'].encode()).hexdigest()
    verification_code = uuid.uuid4().hex

    verification_url = urlunparse(
        (
            'https',
            DOMAIN_NAME,
            'api/v1/contributors/verify',
            None,
            urlencode(
                {
                    'id': id_,
                    'code': verification_code
                }
            ),
            None
        )
    )

    try:
        write_new_contributor(
            id_,
            request_data['name'],
            request_data['email'],
            verification_code
        )
    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response("Conflict: The provided name is already in use",
                            409)
        else:
            raise

    send_email(request_data['email'], request_data['name'], verification_url)

    return response('Success', 201)
