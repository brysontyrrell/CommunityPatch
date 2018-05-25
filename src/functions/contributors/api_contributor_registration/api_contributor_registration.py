import base64
import hashlib
import json
import logging
import os
from urllib.parse import urlencode, urlunparse
import uuid

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONTRIBUTORS_TABLE = os.getenv('CONTRIBUTORS_TABLE')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')
EMAIL_SNS_TOPIC = os.getenv('EMAIL_SNS_TOPIC')

with open('schema_request.json', 'r') as f_obj:
    schema_request = json.load(f_obj)


def response(message, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param str message: Message for JSON body of response
    :param int status_code: HTTP status code of response

    :rtype: dict
    """
    if isinstance(message, str):
        message = {'message': message}

    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def send_email(name, url):
    sns_client = boto3.client('sns')

    try:
        resp = sns_client.publish(
            TopicArn=EMAIL_SNS_TOPIC,
            Message=json.dumps(
                {
                    'recipient': '',
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


def hash_value(email, salt=None):
    if not salt:
        salt = os.urandom(16)

    hashed = hashlib.pbkdf2_hmac('sha256', email.encode(), salt, 100000)

    return base64.b64encode(salt + hashed).decode()


def write_new_contributor(id_, name, email, verification_code):
    contributors_table = boto3.resource('dynamodb').Table(CONTRIBUTORS_TABLE)

    try:
        contributors_table.put_item(
            Item={
                'id': id_,
                'display_name': name,
                'email_hash': hash_value(email),
                'verification_code': verification_code,
                'token_id': None,
                'verified_account': False
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
            'beta.communitypatch.com',
            'api/v1/verify',
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

    send_email(request_data['name'], verification_url)

    return response('Success', 201)
