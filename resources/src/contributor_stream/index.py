from decimal import Decimal
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

DOMAIN_NAME = os.getenv("DOMAIN_NAME")
EMAIL_SNS_TOPIC = os.getenv("EMAIL_SNS_TOPIC")
NAMESPACE = os.getenv("NAMESPACE")


def lambda_handler(event, context):
    print(event)
    fernet = get_fernet()
    sns_client = email_sns_client()

    # for record in event["Records"]:
    #     verification_url = urlunparse(
    #         (
    #             "https",
    #             DOMAIN_NAME,
    #             "api/v1/contributors/verify",
    #             None,
    #             urlencode({"id": id_, "code": verification_code}),
    #             None,
    #         )
    #     )
    #
    #     try:
    #         email_sns_client().publish(
    #             TopicArn=EMAIL_SNS_TOPIC,
    #             Message=json.dumps(
    #                 {
    #                     "recipient": recipient,
    #                     "message_type": "verification",
    #                     "message_data": {"display_name": name, "url": url},
    #                 }
    #             ),
    #             MessageStructure="string",
    #         )
    #     except ClientError as error:
    #         logger.exception(f"Error sending SNS notification: {error}")

    return "ok"


def parse_stream(data):
    result = dict()
    for k, v in data.items():
        if v.get("NULL"):
            result[k] = None
        elif v.get("S"):
            result[k] = str(v["S"])
        elif v.get("N"):
            number = Decimal(v["N"])
            if number % 1 == 0:
                result[k] = int(number)
            else:
                result[k] = float(number)
        elif v.get("M"):
            result[k] = parse_stream(v["M"])
        elif v.get("BOOL") is not None:
            result[k] = bool(v["BOOL"])
    return result


@lru_cache()
def boto3_session():
    return boto3.Session()


@lru_cache()
def get_fernet():
    ssm_client = boto3_session().client("ssm")
    resp = ssm_client.get_parameter(
        Name=f"/communitypatch/{NAMESPACE}/database_key", WithDecryption=True
    )
    return Fernet(resp["Parameter"]["Value"])


@lru_cache()
def email_sns_client():
    return boto3.client("sns", region_name="us-east-2")
