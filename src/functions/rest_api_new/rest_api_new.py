import base64
import hashlib
import json
import logging
import os
import time
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SNS_TOPIC_ARN_TOKEN = os.getenv('SNS_TOPIC_ARN_TOKEN')

dynamodb = boto3.resource('dynamodb').Table(os.getenv('DEFINITIONS_TABLE'))
s3_bucket = boto3.resource('s3').Bucket(os.getenv('DEFINITIONS_BUCKET'))
sns_client = boto3.client('sns')

with open('schema_request.json', 'r') as f_obj:
    request_schema = json.load(f_obj)

with open('schema_full_definition.json', 'r') as f_obj:
    definition_schema = json.load(f_obj)


def response(message, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param str message: Message for JSON body of response
    :param int status_code: HTTP status code of response

    :rtype: dict
    """
    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps({'message': message}),
        'headers': {'Content-Type': 'application/json'}
    }


def hash_value(email, salt=None):
    if not salt:
        salt = os.urandom(16)

    hashed = hashlib.pbkdf2_hmac(
        'sha256', email.encode(), salt, 250000)

    return base64.b64encode(salt + hashed).decode()


# def validate_hash(email, encoded_hash):
#     decoded = base64.decode(encoded_hash)
#     salt = decoded[:16]
#     hash = decoded[16:]
#     return secrets.compare_digest(hash_value(email, salt), hash)


def definition_from_url(data):
    logger.info('Loading definition from URL')
    parsed_url = urlparse(data['definition_url'])
    if not (parsed_url.scheme and parsed_url.netloc):
        return response('Bad Request: Invalid definition URL', 400)

    resp = requests.get(
        data['definition_url'],
        headers={'Accept': 'application/json'},
        timeout=3
    )

    try:
        resp.raise_for_status()
    except requests.HTTPError as error:
        return response(f'An error occurred attempting to read the definition '
                        f'URL: {error}', 400)

    try:
        patch_definition = resp.json()
    except json.JSONDecodeError:
        return response('Bad Request: The definition URL did not return JSON '
                        'content', 400)

    return create_definition(patch_definition, data, synced=True)


def definition_from_json(data):
    logger.info('Loading definition from request body')
    patch_definition = data.get('definition')
    return create_definition(patch_definition, data)


def create_definition(patch_definition, data, synced=False):
    """Create the definition in DynamoDB and S3"""
    try:
        validate(patch_definition, definition_schema)
    except ValidationError as error:
        logger.error('The software title JSON failed validation')
        return response("Bad Request: The patch definition failed validation: "
                        f"{error.message} for path: "
                        f"/{'/'.join([str(i) for i in error.path])}", 400)

    patch_definition['id'] = \
        f"{patch_definition['id']}_{data['author_name'].replace(' ', '_')}"
    patch_definition['name'] = \
        f"{patch_definition['name']} ({data['author_name']})"

    try:
        resp = dynamodb.put_item(
            Item={
                "id": patch_definition['id'],
                "author_name": data['author_name'],
                "author_email_hash": hash_value(data['author_email']),
                "token_id": None,
                "is_synced": synced,
                "last_sync_result": True if synced else None,
                "last_sync_time": int(time.time()) if synced else None,
                "title_summary": {
                    "id": patch_definition['id'],
                    "name": patch_definition['name'],
                    "publisher": patch_definition['publisher'],
                    "currentVersion": patch_definition['currentVersion'],
                    "lastModified": patch_definition['lastModified']
                }
            },
            ConditionExpression='attribute_not_exists(id)'
        )
    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response("Conflict: A title with this the ID "
                            f"'{patch_definition['id']}' already exists", 409)
        else:
            logger.exception(f'DynamoDB: {error.response}')
            return response(f'Internal Server Error: {error}', 500)
    else:
        logger.info(f'Wrote entry to DynamoDB: {resp}')

    try:
        resp = s3_bucket.put_object(
            Body=json.dumps(patch_definition),
            Key=patch_definition['id']
        )
    except ClientError as error:
        logger.exception(f'S3: {error}')
        return response(f'Internal Server Error: {error}', 500)
    else:
        logger.info(f'Wrote file to S3: {resp}')

    logging.info('Sending SNS notification to token manager')
    try:
        resp = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN_TOKEN,
            Message=json.dumps(
                {
                    "software_title_id": patch_definition['id'],
                    "action": "new_token",
                    "recipient_address": data['author_email']
                }
            ),
            MessageStructure='string',
        )
    except ClientError as error:
        logger.exception('Error sending SNS notification to token manager')
    else:
        logger.info(f'SNS notification to token manager sent: {resp}')

    return response('Software title created - check your email for your API '
                    'token!', 201)


def lambda_handler(event, context):
    try:
        data = json.loads(event['body'])
    except (TypeError, json.JSONDecodeError):
        return response('Bad Request: Data must be JSON', 400)

    try:
        validate(data, request_schema)
    except ValidationError as error:
        logger.error(f'The request JSON failed validation: {error.message}')
        return response(
            f'Bad Request: One or more required fields are missing', 400)

    if data.get('definition'):
        return definition_from_json(data)
    elif data.get('definition_url'):
        return definition_from_url(data)
