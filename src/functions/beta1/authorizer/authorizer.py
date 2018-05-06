import json
import logging
import os
import time

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

dynamodb = boto3.resource('dynamodb').Table(os.getenv('DEFINITIONS_TABLE'))
sqs_queue = boto3.resource('sqs').Queue(os.getenv('METRICS_QUEUE_URL'))


def send_metric(name, value, metric):
    logger.info(f"Sending metric '{name}:{value}:{metric}' to queue")
    sqs_queue.send_message(
        MessageBody=json.dumps(
            {
                'name': name,
                'value': value,
                'metric': metric,
                'timestamp': time.time()
            }
        )
    )


def generate_policy(principal_id, effect=None, resource=None, context=None):
    auth_response = {
        'principalId': principal_id
    }

    if effect == 'Deny':
        send_metric('Authorization', 'Forbidden', 'Count')
    elif effect == 'Allow':
        send_metric('Authorization', 'Success', 'Count')

    if effect and resource:
        auth_response['policyDocument'] = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }

    if context:
        auth_response['context'] = dict()
        for k, v in context.items():
            auth_response['context'][k] = str(v)

    logger.info(auth_response)
    return auth_response


def validate_title_id(method_arn, decoded_token):
    """Extract the title ID from the 'methodArn' and compare to the token 'sub'.
    Returns True only for a successful validation.

    The location of the title ID in the Arn may change between endpoints.
    """
    split_arn = method_arn.split('/')
    if split_arn[-1] == 'version' and split_arn[-2] == decoded_token['sub']:
            return True
    else:
        return False


def verify_if_sync_restriction(method_arn, is_synced):
    """Extract the 'resource' from the 'methodArn" and check if synced
    definitions are not allowed to be interacted with by it.
    """
    arn_resource = method_arn.split('/')[-1]
    if arn_resource == 'version' and is_synced:
        return True
    else:
        return False


def lambda_handler(event, context):
    """Order of operations:
    1) Validate 'Authorization' header
        a) Validate 'Authorization' method (Bearer)
    2) Validate token signature
    3) Validate token 'sub' matches the title ID in the 'methodArn'
    4) Lookup title ID in database
    5) Verify no sync restriction for the API request
    6) Validate token 'jti' matches the 'token_id' in the database
        b) The 'token_id' changes on token resets - invalidating old tokens
    """
    method_arn = event['methodArn']

    # 1 - Header
    try:
        method, token = event['authorizationToken'].split()
    except (ValueError, AttributeError) as err:
        logger.error("Bad authorization header: "
                     f"{event['authorizationToken']}: {err}")
        send_metric('Authorization', 'Unauthorized', 'Count')
        raise Exception('Unauthorized')

    if method != 'Bearer':
        logger.error(f"Bad authorization header: {event['authorizationToken']}")
        send_metric('Authorization', 'Unauthorized', 'Count')
        raise Exception('Unauthorized')

    # 2 - Signature
    logger.info('Validating token')
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms='HS256')
    except jwt.InvalidTokenError as err:
        logger.error(f'Authentication failed: {err}')
        send_metric('Authorization', 'Unauthorized', 'Count')
        raise Exception('Unauthorized')

    # 3 - Subject match
    logger.info("Validating token 'sub' with requested title")
    if not validate_title_id(method_arn, decoded_token):
        logger.error(f"Authentication failed: Arn: '{method_arn}', "
                     f"Token: '{decoded_token}'")
        return generate_policy(token, 'Deny', method_arn)

    # 4 - Database lookup
    logger.info(f"Looking up title '{decoded_token['sub']}' in database")
    try:
        resp = dynamodb.get_item(
            Key={'id': decoded_token['sub']},
            ProjectionExpression='id,token_id,is_synced'
        )
    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        return generate_policy(token, 'Deny', method_arn)

    if not resp.get('Item'):
        logger.error(f"The title '{decoded_token['sub']}' was not found on "
                     f"lookup: {resp}")
        return generate_policy(token, 'Deny', method_arn)

    # 5 - Sync restriction check
    logger.info('Verifying no sync restrictions for this API request')
    if verify_if_sync_restriction(method_arn, resp['Item'].get('is_synced')):
        logger.error('This API request is not allowed for synced definitions')
        return generate_policy(token, 'Deny', method_arn)

    # 6 - Token ID match
    logger.info("Validating token 'jti' with title data")
    if resp['Item']['token_id'] == decoded_token['jti']:
        logger.info('Authentication successful!')
        return generate_policy(token, 'Allow', method_arn, decoded_token)
    else:
        logger.error(f"Token ID {resp['Item']['token_id']} is invalid")
        return generate_policy(token, 'Deny', method_arn)
