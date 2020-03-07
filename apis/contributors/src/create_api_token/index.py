import json
import logging
import os
import secrets
import time
import uuid

import boto3
from botocore.exceptions import ClientError
import jwt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DOMAIN_NAME = os.getenv("DOMAIN_NAME")

communitypatchtable = boto3.resource("dynamodb").Table(
    os.getenv("COMMUNITY_PATCH_TABLE")
)


def lambda_handler(event, context):
    """(Not implemented) JSON Payload:

    {
        "expires_in": 12345,
    }

    Expiration time limited to 1 year (31536000)
    """
    authenticated_claims = event["requestContext"]["authorizer"]["claims"]
    new_api_token = create_api_token(authenticated_claims["sub"])

    try:
        write_token_to_table(authenticated_claims["sub"], new_api_token)
    except ClientError as error:
        logger.exception("Unable to write token entry.")
        raise

    return response(
        {"id": new_api_token["id"], "api_token": new_api_token["api_token"]}, 201
    )


def create_api_token(contributor_id, expires_in=31536000):
    token_id = str(uuid.uuid4())
    token_secret = secrets.token_hex()

    issued_time = int(time.time())
    expiration_time = issued_time + expires_in

    api_token = jwt.encode(
        {
            "sub": contributor_id,
            "token_use": "access",
            # "scope": "",
            "iss": f"https://contributors.{DOMAIN_NAME}",
            "aud": f"https://api.{DOMAIN_NAME}",
            "jti": token_id,
            "exp": expiration_time,
            "iat": issued_time,
        },
        token_secret,
        algorithm="HS256",
    ).decode()

    return {
        "id": token_id,
        "secret": token_secret,
        "api_token": api_token,
        "expiration": expiration_time,
    }


def write_token_to_table(contributor_id, token):
    communitypatchtable.put_item(
        Item={
            "contributor_id": contributor_id,
            "type": f"TOKEN#{token['id']}",
            "token_id": token["id"],
            "token_secret": token["secret"],
            "ttl": token["expiration"],
        },
        ConditionExpression="attribute_not_exists(#type)",
        ExpressionAttributeNames={"#type": "type"},
    )


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
