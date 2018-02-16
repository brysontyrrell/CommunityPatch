import base64
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


def get_api_secret_key():
    ssm_client = boto3.client('ssm')
    response = ssm_client.get_parameters(
        Names=[os.getenv('API_SECRET_KEY')],
        WithDecryption=True
    )
    for parameter in response['Parameters']:
        return base64.b64decode(parameter['Value'])


secret_key = get_api_secret_key()

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
        validator.validate(data)
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
            'aud': 'activation'
        },
        secret_key,
        'HS256'
    )

    url_token = '/'.join(activation_token.decode().split('.')[-2:])

    # Need to add in a check to see if the account exists but the activation
    # state is False. A new URL token should be generated in that event.
    try:
        dynamodb.put_item(
            Item={
                'id': account_id.hex,
                'email': data['email'],
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
        'Subject': 'Verify Your CommunityPatch Account',
        'Recipient': data['email'],
        'TextBody': 'Click here to verify your account:\n'
                    f'https://api.communitypatch.com/activation/{url_token}',
        'HtmlBody': ''
    }

    send_to_queue(email_payload)
    return response({'success': 'Account verification email sent'}, 200)


def activate_account(url_token):
    activation_token = '.'.join(
        ['eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9'] + url_token.split('/'))

    try:
        decoded_token = jwt.decode(
            activation_token, secret_key, audience='activation')
    except jwt.InvalidTokenError:
        return response({'error': 'Invalid activation URL'}, 400)

    print(decoded_token)
    account_id = uuid.UUID(decoded_token['sub'])

    try:
        resp = dynamodb.get_item(
            Key={
                'id': account_id.hex,
            }
        )
        account = resp['Item']
    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response(
                {'error': "No account matching this activation could be found"},
                400
            )
        else:
            return response({'error': f'Internal Server Error: {error}'}, 500)

    if account['account_verified']:
        return response(
            {'error': 'This account has already been activated'}, 400)

    dynamodb.update_item = {
        'id': account['id'],
        'account_verified': True
    }

    api_token = jwt.encode(
        {
            'jti': '',
            'sub': account_id.hex,
            'exp': exp_timestamp(365),
            'aud': 'api',
            'ver': 1
        },
        secret_key,
        'HS256'
    )

    email_payload = {
        'Subject': 'Your CommunityPatch API Token',
        'Recipient': account['id'],
        'TextBody': 'Your account has been activated. Use the token below to '
                    'manage your software titles and patch definitions using '
                    f'the API.\n/{api_token.decode()}',
        'HtmlBody': ''
    }

    send_to_queue(email_payload)
    return response({'success': 'Your account is activated. CHeck your inbox '
                                'for your API token and Account ID'}, 200)


def lambda_handler(event, context):
    resource = event['resource']
    parameter = event['pathParameters']
    method = event['httpMethod']

    if resource == '/accounts/register' and method == 'POST':
        print('Registration request received!')
        if not event['body'] or \
                not event['headers'].get('Content-Type') == 'application/json':
            return response({'error': 'JSON payload required'}, 400)

        return new_account(event['body'])

    elif resource == '/accounts/activation/{proxy+}' \
            and method == 'GET' and parameter:
        print('Account activation request received!')
        activate_account(parameter['proxy'])
        return {}

    else:
        return response({'error': f"Bad Request: {event['path']}"}, 400)
