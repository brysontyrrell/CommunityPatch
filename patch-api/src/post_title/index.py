import json
import logging
import os

from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

TITLES_TABLE = os.getenv("TITLES_TABLE")

dynamodb = boto3.resource("dynamodb")
s3_bucket = boto3.resource("s3").Bucket(os.getenv("TITLES_BUCKET"))


def lambda_handler(event, context):
    contributor_id = event["requestContext"]["authorizer"]["sub"]
    data = json.loads(event["body"])

    try:
        create_table_entry(data, contributor_id)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(
                "Conflict: You have already created a title with "
                f"the ID '{data['id']}'",
                409,
            )
        else:
            return response(f"Internal Server Error", 500)

    try:
        write_definition_to_s3(data, contributor_id)
    except ClientError:
        # Delete the DynamoDB entry for cleanup
        return response("Internal Server Error", 500)

    return response(f"Title '{data['id']}' created", 201)


def create_table_entry(patch_definition, contributor_id):
    """Write the definition to DynamoDB table"""
    titles_table = dynamodb.Table(TITLES_TABLE)

    try:
        titles_table.put_item(
            Item={
                "contributor_id": contributor_id,
                "title_id": patch_definition["id"],
                "api_allowed": True,
                "summary": {
                    "id": patch_definition["id"],
                    "name": patch_definition["name"],
                    "publisher": patch_definition["publisher"],
                    "currentVersion": patch_definition["currentVersion"],
                    "lastModified": patch_definition["lastModified"],
                },
                "last_sync_result": None,
                "last_sync_time": None,
            },
            ConditionExpression="attribute_not_exists(title_id)",
        )
    except ClientError:
        logger.exception("Unable to write title entry to DynamoDB!")
        raise


def write_definition_to_s3(patch_definition, contributor_id):
    try:
        s3_bucket.put_object(
            Body=json.dumps(patch_definition),
            Key=os.path.join("titles", contributor_id, patch_definition["id"]),
            ContentType="application/json",
        )
    except ClientError:
        logger.exception("Unable to write title JSON to S3")
        raise


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
