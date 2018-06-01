import json
import logging
import os

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

CONTRIBUTORS_TABLE = os.getenv('CONTRIBUTORS_TABLE')
EMAIL_SNS_TOPIC = os.getenv('EMAIL_SNS_TOPIC')


def get_database_key(name):
    ssm_client = boto3.client('ssm')
    resp = ssm_client.get_parameter(Name=name, WithDecryption=True)
    return resp['Parameter']['Value']


fernet = Fernet(get_database_key(os.getenv('DB_KEY_PARAMETER')))


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


def send_email(recipient, name, url):
    sns_client = boto3.client('sns')

    try:
        resp = sns_client.publish(
            TopicArn=EMAIL_SNS_TOPIC,
            Message=json.dumps(
                {
                    'recipient': recipient,
                    'message_type': 'api_token',
                    'message_data': {
                        'display_name': name,
                        'api_token': url
                    }
                }
            ),
            MessageStructure='string'
        )
    except ClientError as error:
        logger.exception(f'Error sending SNS notification: {error}')
        raise


def get_contributor(contributor_id):
    contributors_table = boto3.resource('dynamodb').Table(CONTRIBUTORS_TABLE)
    return ''


def lambda_handler(event, context):
    logger.info(event)
    try:
        contributor_id = event['queryStringParameters']['id']
        verification_code = event['queryStringParameters']['code']
    except (KeyError, TypeError):
        logger.error("Bad Request: Required values are missing")
        return response("Bad Request: Required values are missing", 400)

    try:
        contributor = get_contributor(contributor_id)
    except ClientError:
        logger.exception(f'Error retrieving the contributor {contributor_id}')
        raise

    return response('OK', 200)
