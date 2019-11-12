import base64
from functools import lru_cache
import os
import time
import uuid

import boto3
from cryptography.fernet import Fernet
import jwt

NAMESPACE = os.getenv("NAMESPACE")


def lambda_handler(event, context):
    encrypted_token, token_id = create_token(event["id"])
    return {"token": encrypted_token, "id": token_id}


def create_token(contributor_id):
    token_id = uuid.uuid4().hex
    now = int(time.time())

    api_token = jwt.encode(
        {
            "jti": token_id,
            "sub": contributor_id,
            "iat": now,
            "exp": now + 31536000,  # one year
        },
        get_signing_key(),
        algorithm="RS256",
    )
    return get_fernet().encrypt(api_token).decode(), token_id


@lru_cache()
def boto3_session():
    return boto3.Session()


@lru_cache()
def ssm_client():
    return boto3_session().client("ssm")


@lru_cache()
def get_signing_key():
    resp = ssm_client().get_parameter(
        Name=f"/communitypatch/{NAMESPACE}/token_private_key", WithDecryption=True
    )
    return base64.b64decode(resp["Parameter"]["Value"])


@lru_cache()
def get_fernet():
    resp = ssm_client().get_parameter(
        Name=f"/communitypatch/{NAMESPACE}/database_key", WithDecryption=True
    )
    return Fernet(resp["Parameter"]["Value"])
