import json
import logging
import os
from urllib.parse import urlencode, urlunparse

from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

DOMAIN_NAME = os.getenv("DOMAIN_NAME")

# Registration state machine only exists in us-east-2
sf_client = boto3.client("stepfunctions", region_name='us-east-2')


def redirect_url(status):
    return urlunparse(
        ("https", DOMAIN_NAME, "", None, urlencode({"status": status}), None)
    )


def lambda_handler(event, context):
    logger.info(event)
    try:
        verification_code = event["queryStringParameters"]["code"]
    except (KeyError, TypeError):
        logger.error("Bad Request: 'code' is missing")
        return response("missing-values", 400)

    try:
        sf_client.send_task_success(taskToken=verification_code, output='{}')
    except ClientError:
        logger.exception('Invalid task token')
        return response('Invalid task token', 403)

    return response("Success", 200)


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
