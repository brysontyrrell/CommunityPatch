import os
import uuid

import boto3
import jwt

PARAM_STORE_PATH = os.getenv('PARAM_STORE_PATH')

ssm_client = boto3.client('ssm')


def get_database_key():
    resp = ssm_client.get_parameter(
        Name=f'{PARAM_STORE_PATH}/database_key', WithDecryption=True
    )
    return resp['Parameter']['Value']


def get_legacy_api_key():
    resp = ssm_client.get_parameter(
        Name=f'{PARAM_STORE_PATH}/legacy_api_key', WithDecryption=True
    )
    return resp['Parameter']['Value']


LEGACY_SECRET_KEY = get_legacy_api_key()


def create_legacy_token(contributor_id):
    token_id = uuid.uuid4().hex
    api_token = jwt.encode(
        {
            'jti': token_id,
            'sub': contributor_id
        },
        LEGACY_SECRET_KEY,
        algorithm='HS256'
    ).decode()
    return api_token, token_id


def validate_token(token):
    try:
        decoded_token = jwt.decode(token, LEGACY_SECRET_KEY, algorithms='HS256')
    except jwt.InvalidTokenError:
        logger.exception('Authentication failed')
        raise Exception('Unauthorized')

    return decoded_token
