import json
import logging
import os

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

communitypatchtable = boto3.resource("dynamodb").Table(
    os.getenv("COMMUNITY_PATCH_TABLE")
)


def lambda_handler(event, context):
    # Not consistent with Cognito auth
    authenticated_claims = event["requestContext"]["authorizer"]

    if event["resource"] == "/v1/titles":
        result = communitypatchtable.query(
            IndexName="ContributorSummaries",
            KeyConditionExpression=Key("contributor_id").eq(
                authenticated_claims["sub"]
            ),
        )
        return response({"titles": [i["summary"] for i in result["Items"]]}, 200)

    elif event["resource"] == "/v1/titles/{title_id}":
        title_id = event["pathParameters"]["title_id"]

        result = communitypatchtable.get_item(
            Key={
                "contributor_id": authenticated_claims["sub"],
                "type": f"TITLE#{title_id}",
            }
        )
        try:
            return {
                "statusCode": 200,
                "body": result["Item"]["body"],
                "headers": {"Content-Type": "application/json"},
            }
        except KeyError:
            return response("Not Found", 404)


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
