import logging
import os
import sys

# Add '/opt' to the PATH for Lambda Layers
sys.path.append('/opt')

import boto3
from botocore.exceptions import ClientError

from security_helpers import validate_token

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BLACKLIST_TABLE = os.getenv('BLACKLIST_TABLE')


def generate_policy(principal_id, effect=None, resource=None, context=None):
    auth_response = {
        'principalId': principal_id
    }

    if effect and resource:
        auth_response['policyDocument'] = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': '/'.join(resource.split('/')[:2] + ['*'])
                }
            ]
        }

    if context:
        auth_response['context'] = dict()
        for k, v in context.items():
            auth_response['context'][k] = str(v)

    logger.info(auth_response)
    return auth_response


def read_token_from_header(event):
    try:
        type_, token = event['authorizationToken'].split()
    except (ValueError, AttributeError):
        logger.error("No token found")
        raise Exception('Unauthorized')

    if type_ != 'Bearer':
        logger.error("Incorrect authentication type: "
                     f"{event['authorizationToken']}")
        raise Exception('Unauthorized')

    return token


def is_token_blacklisted(token_id):
    blacklist_table = boto3.resource('dynamodb').Table(BLACKLIST_TABLE)

    try:
        resp = blacklist_table.get_item(Key={'token_id': token_id})
    except ClientError:
        logger.exception('Unable to read from DynamoDB!')
        raise Exception('Internal Server Error')

    return bool(resp.get('Item'))


def lambda_handler(event, context):
    method_arn = event['methodArn']
    token = read_token_from_header(event)

    logger.info('Validating token...')
    decoded_token = validate_token(token)

    logger.info('Checking token blacklist...')

    if is_token_blacklisted(decoded_token['jti']):
        return generate_policy(token, 'Deny', method_arn)

    return generate_policy(token, 'Allow', method_arn, decoded_token)
