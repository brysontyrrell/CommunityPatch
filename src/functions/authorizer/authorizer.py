import logging
import os

import jwt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SECRET_KEY = os.getenv('SECRET_KEY')


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

    return auth_response


def lambda_handler(event, context):
    method_arn = event['methodArn']

    try:
        method, token = event['authorizationToken'].split()
    except ValueError as err:
        logger.error("Bad authorization header: "
                     f"{event['authorizationToken']}: {err}")
        raise Exception('Unauthorized')

    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms='HS256')

    except jwt.InvalidTokenError as err:
        logger.error(f'Authentication failed: {err}')
        raise Exception('Unauthorized')

    else:
        return generate_policy(token, 'Allow', method_arn, decoded_token)
