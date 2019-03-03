import base64
import os
import uuid

import boto3
from cryptography.fernet import Fernet
import jwt

PARAM_STORE_PATH = os.getenv('PARAM_STORE_PATH')

ssm_client = boto3.client('ssm')


def get_parameters(param_names):
    return_params = dict()

    resp = ssm_client.get_parameters(
        Names=[os.path.join(PARAM_STORE_PATH, i) for i in param_names],
        WithDecryption=True
    )

    for parameter in resp['Parameters']:
        name = os.path.basename(parameter['Name'])

        if name.startswith('token'):
            value = base64.b64decode(parameter['Value'])
        else:
            value = parameter['Value']

        return_params[name] = value

    return return_params


parameters = get_parameters(
    ('database_key', 'legacy_api_key', 'token_private_key', 'token_public_key')
)


def get_fernet():
    return Fernet(parameters['database_key'])


def create_token(contributor_id):
    token_id = uuid.uuid4().hex
    api_token = jwt.encode(
        {
            'jti': token_id,
            'sub': contributor_id
        },
        parameters['token_private_key'],
        algorithm='RS256'
    ).decode()
    return api_token, token_id


def create_legacy_token(contributor_id):
    token_id = uuid.uuid4().hex
    api_token = jwt.encode(
        {
            'jti': token_id,
            'sub': contributor_id
        },
        parameters['legacy_api_key'],
        algorithm='HS256'
    ).decode()
    return api_token, token_id


def validate_token(token):
    headers = jwt.get_unverified_header(token)

    if headers['alg'] == 'HS256':
        algorithm = 'HS256'
        signing_secret = parameters['legacy_api_key']

    elif headers['alg'] == 'RS256':
        algorithm = 'RS256'
        signing_secret = parameters['token_public_key']

    else:
        raise Exception('Unauthorized')

    try:
        decoded_token = jwt.decode(token, signing_secret, algorithms=algorithm)
    except jwt.InvalidTokenError:
        raise Exception('Unauthorized')

    return decoded_token
