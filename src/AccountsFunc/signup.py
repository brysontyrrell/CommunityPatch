from datetime import datetime, timedelta
import json
import os
import uuid

import boto3
from botocore.exceptions import ClientError
from jsonschema import Draft4Validator, FormatChecker, ValidationError
import jwt

dynamodb = boto3.resource('dynamodb').Table(os.getenv('TABLE_NAME'))
sqs_queue = boto3.resource('sqs').Queue(os.getenv('EMAIL_QUEUE_URL'))
ssm_client = boto3.client('ssm')

secret_key = ssm_client.get_parameter(
    Name=os.environ['API_SECRET_KEY'],
    WithDecryption=True
)

with open('register_schema.json', 'r') as f_obj:
    validator = Draft4Validator(
        json.load(f_obj), format_checker=FormatChecker())


def response(message, status_code):
    print(message)

    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def exp_timestamp(days):
    """Returns a Unix timestamp for N days in the future.

    :param int days: Number of days

    :returns: Unix timestamp
    :rtype: int
    """
    return (datetime.utcnow() + timedelta(days=days)).strftime('%s')


def send_to_queue(payload):
    """Sends an email message to the Email Queue to be processed.

    :param dict payload:
    """
    resp = sqs_queue.send_message(MessageBody=json.dumps(payload))
    print(f"Email sent to queue: {resp['MessageId']}")


def new_account(body):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return response({'error': f"Unable to read JSON content"}, 400)

    try:
        validator.validate(body, format_checker=FormatChecker())
    except ValidationError as error:
        return response(
            {'error': f"Validation Error on Subscription URL JSON: "
                      f"{error.message} for item: "
                      f"/{'/'.join([str(i) for i in error.path])}"},
            400
        )

    account_id = uuid.uuid4()

    activation_token = jwt.encode(
        {
            'sub': account_id.hex,
            'exp': exp_timestamp(7),
            'type': 'activation'
        },
        secret_key,
        'HS256'
    )

    url_token = '/'.join(activation_token.decode().split('.')[-2:])

    try:
        dynamodb.put_item(
            Item={
                'id': data['email'],
                'account_id': account_id.bytes,
                'account_verified': False
            },
            ConditionExpression='attribute_not_exists(id)'
        )
    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response(
                {'error': "Conflict: An account for this email address "
                          "already exists"}, 409
            )
        else:
            return response({'error': f'Internal Server Error: {error}'}, 500)

    email_payload = {
        'Subject': 'Verify Your Patch Server Account',
        'Recipient': data['email'],
        'TextBody': 'Click here to verify your account '
                    'and recieve your API token:\n'
                    f'https://api.communitypatch.com/activation/{url_token}',
        'HtmlBody': ''
    }

    send_to_queue(email_payload)
    return response({'success': 'Account verification email sent'}, 200)


def activate_account():
    url_token = ''
    activation_token = '.'.join([''] + url_token.split('/'))
    
    decoded = jwt.decode(activation_token, 'secret')
    account_id = uuid.UUID(decoded['sub'])

    dydb_update = {
        'id': account_id.bytes,
        'account_verified': True
    }

    new_api_token = jwt.encode(
        {
            'kid': '',
            'sub': account_id.hex
        },
        'key', 'HS256'
    )


def lambda_handler(event, context):
    resource = event['resource']
    method = event['httpMethod']

    if resource == '/accounts/register' and method == 'POST':
        print('Registration request received!')
        if not event['body'] or \
                not event['headers'].get('Content-Type') == 'application/json':
            return response({'error': 'JSON payload required'}, 400)

        return new_account(event['body'])

    elif resource == '/accounts/activation/{proxy+}' and method == 'GET':
        print('Account activation request received!')
        # activate_account()
        return {}

    else:
        return response({'error': f"Bad Request: {event['path']}"}, 400)
