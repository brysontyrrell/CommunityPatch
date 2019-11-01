from functools import lru_cache
import hashlib
import json
import logging
import os
import time
from urllib.parse import urlencode, urlunparse
import uuid

from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

CONTRIBUTORS_TABLE = os.getenv("CONTRIBUTORS_TABLE")
NAMESPACE = os.getenv("NAMESPACE")


def lambda_handler(event, context):
    body = json.loads(event["body"])

    id_ = hashlib.md5(body["name"].encode()).hexdigest()
    verification_code = uuid.uuid4().hex

    try:
        write_new_contributor(id_, body["name"], body["email"], verification_code)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response("Conflict: The provided name is already in use", 409)
        else:
            raise

    return response("Success", 201)


def write_new_contributor(id_, name, email, verification_code):
    contributors_table = table_resource(CONTRIBUTORS_TABLE)
    fernet = get_fernet()

    try:
        contributors_table.put_item(
            Item={
                "id": id_,
                "display_name": name,
                "email": fernet.encrypt(email.encode()),
                "verification_code": verification_code,
                "token_id": None,
                "verified_account": False,
                "date_registered": int(time.time()),
            },
            ConditionExpression="attribute_not_exists(id) AND "
            "attribute_not_exists(display_name)",
        )
    except ClientError:
        logger.exception("Error encountered writing a new entry to the icon table")
        raise


@lru_cache()
def boto3_session():
    return boto3.Session()


@lru_cache()
def table_resource(table):
    return boto3_session().resource("dynamodb").Table(table)


@lru_cache()
def get_fernet():
    ssm_client = boto3_session().client("ssm")
    resp = ssm_client.get_parameter(
        Name=f"/communitypatch/{NAMESPACE}/database_key", WithDecryption=True
    )
    return Fernet(resp["Parameter"]["Value"])


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
