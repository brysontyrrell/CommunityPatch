import base64
from decimal import Decimal
from functools import lru_cache
import json
import logging
import os
from urllib.parse import urlencode, urlunparse

from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

DOMAIN_NAME = os.getenv("DOMAIN_NAME")
EMAIL_SERVICE_TOPIC = os.getenv("EMAIL_SERVICE_TOPIC")
NAMESPACE = os.getenv("NAMESPACE")


def lambda_handler(event, context):
    logger.info(event)
    fernet = get_fernet()

    for record in event["Records"]:
        data = dict()
        data.update(parse_stream(record["dynamodb"]["Keys"]))

        if record["eventName"] == "INSERT":
            data.update(parse_stream(record["dynamodb"]["NewImage"]))

            verification_url = urlunparse(
                (
                    "https",
                    DOMAIN_NAME,
                    "api/v1/contributors/verify",
                    None,
                    urlencode({"id": data["id"], "code": data["verification_code"]}),
                    None,
                )
            )

            try:
                email_sns_client().publish(
                    TopicArn=EMAIL_SERVICE_TOPIC,
                    Message=json.dumps(
                        {
                            "recipient": fernet.decrypt(data["email"]).decode(),
                            "message_type": "verification",
                            "message_data": {
                                "display_name": data["display_name"],
                                "url": verification_url,
                            },
                        }
                    ),
                    MessageStructure="string",
                )
            except ClientError as error:
                logger.exception(f"Error sending SNS notification: {error}")

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
        elif v.get("B"):
            result[k] = base64.b64decode(v["B"])
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
