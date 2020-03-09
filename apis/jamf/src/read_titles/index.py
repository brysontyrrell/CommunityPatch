import json
import logging
import os

import boto3
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

communitypatchtable = boto3.resource("dynamodb").Table(
    os.getenv("COMMUNITY_PATCH_TABLE")
)


def lambda_handler(event, context):
    # There's an issue with the HTTP API event where the "resource" key is not the route
    # string defined in the template with the parameters but is the same value as the
    # "path" key. The following attempts to work around this.

    contributor_id = event["pathParameters"]["contributor_id"]
    title_ids = event["pathParameters"].get("title_ids")  # /software
    title_id = event["pathParameters"].get("title_id")  # /patch

    if event["resource"] == f"/v1/{contributor_id}/software":
        result = communitypatchtable.query(
            IndexName="ContributorSummaries",
            KeyConditionExpression=Key("contributor_id").eq(contributor_id),
        )

        return response([i["summary"] for i in result["Items"]], 200)

    elif event["resource"] == f"/v1/{contributor_id}/software/{title_ids}":
        results = list()

        for i in set(title_ids.split(",")):
            query_result = communitypatchtable.query(
                IndexName="ContributorSummaries",
                KeyConditionExpression=Key("contributor_id").eq(contributor_id)
                & Key("title_id").eq(i),
            )
            if query_result.get("Items"):
                results.append(query_result["Items"][0]["summary"])

        return response(results, 200)

    elif event["resource"] == f"/v1/{contributor_id}/patch/{title_id}":
        # Returns the full definition body of the selected title for a contributor

        result = communitypatchtable.get_item(
            Key={"contributor_id": contributor_id, "type": f"TITLE#{title_id}",}
        )
        try:
            return {
                "statusCode": 200,
                "body": result["Item"]["body"],
                "headers": {"Content-Type": "application/json"},
            }
        except KeyError:
            return response("Not Found", 404)

    else:
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
