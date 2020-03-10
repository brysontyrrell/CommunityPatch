import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

communitypatchtable = boto3.resource("dynamodb").Table(
    os.getenv("COMMUNITY_PATCH_TABLE")
)


def lambda_handler(event, context):
    authenticated_claims = event["requestContext"]["authorizer"]
    title_id = event["pathParameters"]["title_id"]

    try:
        communitypatchtable.delete_item(
            Key={
                "contributor_id": authenticated_claims["sub"],
                "type": f"TITLE#{title_id.lower()}",
            },
            ConditionExpression="attribute_exists(#type)",
            ExpressionAttributeNames={"#type": "type"},
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response("Not Found", 404)
        else:
            raise

    return response(f"Title '{title_id}' deleted", 200)


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
