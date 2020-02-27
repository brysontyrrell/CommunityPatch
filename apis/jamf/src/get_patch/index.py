import io
import json
import logging
import os

from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

s3_bucket = boto3.resource("s3").Bucket(os.getenv("TITLES_BUCKET"))


def lambda_handler(event, context):
    parameters = event["pathParameters"]

    contributor_id = parameters["contributor"]
    title_id = parameters["title"]

    try:
        definition = read_definition_from_s3(contributor_id, title_id)
    except ClientError:
        return response("Not Found", 404)

    return response(definition, 200)


def read_definition_from_s3(contributor_id, title_id):
    f_obj = io.BytesIO()
    try:
        s3_bucket.download_fileobj(
            Key=os.path.join("titles", contributor_id, title_id), Fileobj=f_obj
        )
    except ClientError:
        logger.exception("Unable to read title JSON from S3")
        raise

    return json.loads(f_obj.getvalue())


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
