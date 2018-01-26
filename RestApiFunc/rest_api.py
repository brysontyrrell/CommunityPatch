import json
import os

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
s3_bucket = boto3.resource('s3').Bucket(os.environ['S3_BUCKET'])

with open('schema_full_definition.json', 'r') as f_obj:
    definition_schema = json.load(f_obj)

with open('schema_version.json', 'r') as f_obj:
    version_schema = json.load(f_obj)


def response(message, status_code):
    print(message)
    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def post_definition():
    """
    - Check if title exists
        - Return 409 if it does
    - Check if title is a subscription
        - Return 400 if it is
    - Validate JSON
        - Return 400 if invalid
    - Return 201

    """
    pass


def put_definition():
    """
    - Check if title exists
        - Return 404 if not found
    - Check if title is a subscription
        - Return 400 if it is
    - Validate JSON
        - Return 400 if invalid
    - Return 200

    """
    pass


def post_version():
    """
    - Check if title exists
        - Return 404 if not found
    - Check if title is a subscription
        - Return 400 if it is
    - Validate JSON
        - Return 400 if invalid
    - Check if version exists
        - Return 400 if it does
    - Return 201

    """
    pass


def lambda_handler(event, context):
    return response({'success': 'invoked'}, 200)
