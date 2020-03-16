import json
import logging
import os
import secrets
import time
import uuid

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError
import jwt

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def read_schema(schema):
    with open(f"schemas/{schema}.json", "r") as f_obj:
        return json.load(f_obj)


DOMAIN_NAME = os.getenv("DOMAIN_NAME")

schema_definition = read_schema("token")

communitypatchtable = boto3.resource("dynamodb").Table(
    os.getenv("COMMUNITY_PATCH_TABLE")
)


def lambda_handler(event, context):
    """JSON payload values are optional.

    Expiration time limited/defaults to 1 year (60 * 60 * 24 * 365)
    Title scope defaults to "titles/full_access"
    """
    authenticated_claims = event["requestContext"]["authorizer"]["claims"]

    try:
        request_body = json.loads(event.get("body") or "{}")
    except (TypeError, json.JSONDecodeError):
        logger.exception("Bad Request: No JSON content found")
        return response("Bad Request: No JSON content found", 400)

    try:
        validate(request_body, schema_definition)
    except ValidationError as error:
        validation_error = (
            f"Validation Error {str(error.message)} "
            f"for item: {'/'.join([str(i) for i in error.path])}"
        )
        logger.error(validation_error)
        return response(validation_error, 400)

    new_api_token = create_api_token(
        contributor_id=authenticated_claims["sub"],
        expires_in=get_expires_in(request_body.get("expires_in_days")),
        scope=get_scope_string(request_body.get("titles_in_scope")),
    )

    try:
        write_token_to_table(authenticated_claims["sub"], new_api_token)
    except ClientError as error:
        logger.exception("Unable to write token entry.")
        raise

    return response(
        {"id": new_api_token["id"], "api_token": new_api_token["api_token"]}, 201
    )


def get_expires_in(time_in_days):
    if not time_in_days:
        time_in_days = 365
    return 60 * 60 * 24 * time_in_days


def get_scope_string(title_ids):
    if not title_ids:
        return "titles-api/full_access"
    return " ".join([f"titles-api/{i}" for i in title_ids])


def create_api_token(contributor_id, expires_in, scope):
    token_id = str(uuid.uuid4())
    token_secret = secrets.token_hex()

    issued_time = int(time.time())
    expiration_time = issued_time + expires_in

    api_token = jwt.encode(
        {
            "sub": contributor_id,
            "token_use": "access",
            "scope": scope,
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
