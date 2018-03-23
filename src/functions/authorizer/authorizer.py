import logging
import os

import boto3
from botocore.exceptions import ClientError
import jwt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SECRET_KEY = os.getenv('SECRET_KEY')

dynamodb = boto3.resource('dynamodb').Table(os.getenv('DEFINITIONS_TABLE'))


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


def lambda_handler(event, context):
    """Order of operations:
    1) Validate 'Authorization' header
        a) Validate 'Authorization' method (Bearer)
    2) Validate token signature
    3) Validate token 'sub' matches the title ID in the 'methodArn'
    4) Validate token 'jti' matches the 'token_id' in the database
        b) The 'token_id' changes on token resets - invalidating old tokens
    """
    method_arn = event['methodArn']

    try:
        method, token = event['authorizationToken'].split()
    except (ValueError, AttributeError) as err:
        logger.error("Bad authorization header: "
                     f"{event['authorizationToken']}: {err}")
        raise Exception('Unauthorized')

    if method != 'Bearer':
        logger.error(f"Bad authorization header: {event['authorizationToken']}")
        raise Exception('Unauthorized')

    logger.info('Validating token')
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms='HS256')
    except jwt.InvalidTokenError as err:
        logger.error(f'Authentication failed: {err}')
        raise Exception('Unauthorized')

    logger.info("Validating token 'sub' with requested title")
    if not validate_title_id(method_arn, decoded_token):
        logger.error(f"Authentication failed: Arn: '{method_arn}', "
                     f"Token: '{decoded_token}'")
        return generate_policy(token, 'Deny', method_arn)

    logger.info(f"Looking up title '{decoded_token['sub']}' in database")
    try:
        resp = dynamodb.get_item(Key={'id': decoded_token['sub']})
    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        return

    logger.info("Validating token 'jti' with title data")
    if resp.get('Item') and \
            resp['Item']['token_id'] == decoded_token['jti']:
        logger.info('Authentication successful!')
        return generate_policy(token, 'Allow', method_arn, decoded_token)
    else:
        logger.error(f"Token ID {resp['Item']['token_id']} is invalid")
        return generate_policy(token, 'Deny', method_arn)
