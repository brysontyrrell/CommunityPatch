import base64
import hashlib
import json
import logging
import os
import uuid

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError
import jwt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SECRET_KEY = os.getenv('SECRET_KEY')
SENDER_ADDRESS = os.getenv('SENDER_ADDRESS')

dynamodb = boto3.resource('dynamodb').Table(os.getenv('DEFINITIONS_TABLE'))
s3_bucket = boto3.resource('s3').Bucket(os.getenv('DEFINITIONS_BUCKET'))
ses_client = boto3.client('ses', region_name='us-east-1')

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


def send_email(recipient, api_token):
    # The email body for recipients with non-HTML email clients.
    body_text = f"Your Community Patch Software Title Token:\n{api_token}\n\n" \
                "Amazon SES (Python)\nThis email was sent with Amazon SES " \
                "using the AWS SDK for Python (Boto)."

    # The HTML body of the email.
    body_html = f"""<html>
    <head></head>
    <body>
      <h1>Your Community Patch Software Title API Token:</h1>
      <p>{api_token}</p>
      <h2>Amazon SES Test (SDK for Python)</h1>
      <p>This email was sent with
        <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
        <a href='https://aws.amazon.com/sdk-for-python/'>
          AWS SDK for Python (Boto)</a>.</p>
    </body>
    </html>
    """

    return ses_client.send_email(
        Destination={
            'ToAddresses': [recipient],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': 'UTF-8',
                    'Data': body_html,
                },
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': body_text,
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': 'Community Patch API Token',
            },
        },
        Source=f'Commuinity Patch <{SENDER_ADDRESS}>',
    )


def main(body):
    """Order of operations:
    1) Validate JSON (must have author_name, author_email, definition)
    2) Validate Software Title Definition JSON
    3) Update the 'id' and 'name' values of the definition with author_name
    2) Ensure a unique Software Title ID
    """
    try:
        data = json.loads(body)
    except (TypeError, json.JSONDecodeError):
        return response('Bad Request', 400)

    try:
        validate(data, request_schema)
    except ValidationError as error:
        logger.error(f'The request JSON failed validation: {error.message}')
        return response(f'Bad Request: {error.message}', 400)

    patch_definition = data.get('definition')
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

    token_id = str(uuid.uuid4())

    api_token = jwt.encode(
        {
            'jti': token_id,
            'sub': patch_definition['id']
        },
        SECRET_KEY,
        algorithm='HS256'
    ).decode()

    try:
        resp = dynamodb.put_item(
            Item={
              "id": patch_definition['id'],
              "author_name": data['author_name'],
              "author_email_hash": hash_value(data['author_email']),
              "token_id": token_id,
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

    try:
        resp = send_email(data['author_email'], api_token)
    except ClientError as error:
        logger.exception(f'SES: {error.response}')
        return response('Internal Server Error: The email failed to send - '
                        'contact support', 500)
    else:
        logger.info(f'Sent Email via SES: {resp}')

    return response(api_token, 201)


def lambda_handler(event, context):
    return main(event['body'])
