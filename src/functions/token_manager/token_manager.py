import json
import logging
import os
import uuid

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError
import jwt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

xray_recorder.configure(service='CommunityPatch')
patch(['boto3'])

SECRET_KEY = os.getenv('SECRET_KEY')
SNS_TOPIC_ARN_EMAIL = os.getenv('SNS_TOPIC_ARN_EMAIL')

dynamodb = boto3.resource('dynamodb').Table(os.getenv('DEFINITIONS_TABLE'))
sns_client = boto3.client('sns')


def message_success(api_token, software_title_id):
    # The HTML body of the email.
    body_html = f"""<html>
    <head></head>
    <body>
      <h1>Your Community Patch Software Title API Token:</h1>
      <p>{api_token}</p>
      <h2>Software Title:</h2>
      <p>{software_title_id}</p>
      <h3>Amazon SES Test (SDK for Python)</h3>
      <p>This email was sent with
        <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
        <a href='https://aws.amazon.com/sdk-for-python/'>
          AWS SDK for Python (Boto)</a>.</p>
    </body>
    </html>
    """

    # The email body for recipients with non-HTML email clients.
    body_text = f"Your Community Patch Software Title Token:\n{api_token}\n\n" \
                f"Software Title ID: {software_title_id}\n\n" \
                "Amazon SES (Python)\nThis email was sent with Amazon SES " \
                "using the AWS SDK for Python (Boto)."

    return body_html, body_text


def create_token(data):
    token_id = str(uuid.uuid4())

    api_token = jwt.encode(
        {
            'jti': token_id,
            'sub': data['software_title_id']
        },
        SECRET_KEY,
        algorithm='HS256'
    ).decode()

    logger.info("Updating database 'token_id' for software title: "
                f"{data['software_title_id']}")
    try:
        resp = dynamodb.update_item(
            Key={
                'id': data['software_title_id']
            },
            UpdateExpression="set token_id = :i",
            ExpressionAttributeValues={
                ':i': token_id
            },
            ReturnValues="UPDATED_NEW"
        )
        logger.info(f"DynamoDB updated: {resp['Attributes']}")

    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        # Create error messages for the email here
        return

    else:
        body_html, body_text = message_success(
            api_token, data['software_title_id'])

    logging.info('Sending SNS notification to token manager')
    try:
        resp = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN_EMAIL,
            Message=json.dumps(
                {
                    'recipient_address': data['recipient_address'],
                    'body_html': body_html,
                    'body_text': body_text
                }
            ),
            MessageStructure='string',
        )
    except ClientError as error:
        logger.exception('Error sending SNS notification to token manager')
    else:
        logger.info(f'SNS notification to token manager sent: {resp}')


def lambda_handler(event, context):
    """This function is meant to be triggered by an SNS event. The expceted
    JSON body of the SNS message should be formatted as:

    .. code-block: json

        {
            "recipient_address": "",
            "action": "",
            "software_title_id": ""
        }
    """
    if event.get('Records'):
        logging.info('Processing SNS records...')
        for record in event['Records']:
            data = json.loads(record['Sns']['Message'])
            create_token(data)

    else:
        logging.warning('No SNS records found in the event')

    return {}
