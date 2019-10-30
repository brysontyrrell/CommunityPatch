import json
import logging
import os

from aws_xray_sdk.core import patch
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

TITLES_TABLE = os.getenv("TITLES_TABLE")

dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    resource = event["resource"]
    parameters = event["pathParameters"]
    query_string_parameters = event["queryStringParameters"]

    if (
        isinstance(query_string_parameters, dict)
        and "extend" in query_string_parameters.keys()
    ):
        extend = True
    else:
        extend = False

    if resource == "/jamf/v1/{contributor}/software":
        return list_software_titles(parameters["contributor"], extend=extend)

    elif resource == "/jamf/v1/{contributor}/software/{titles}":
        return list_select_software_titles(
            parameters["contributor"], parameters["titles"]
        )

    else:
        raise response("Not Found", 404)


def list_software_titles(contributor_id, extend=False):
    titles_table = dynamodb.Table(TITLES_TABLE)

    if extend:
        projection_expression = "last_sync_result,last_sync_time,summary"
    else:
        projection_expression = "summary"

    try:
        resp = titles_table.query(
            KeyConditionExpression=Key("contributor_id").eq(contributor_id),
            ProjectionExpression=projection_expression,
        )
    except ClientError:
        logger.exception("Unable to read title entry from DynamoDB!")
        raise

    if extend:
        results = list()
        for i in resp["Items"]:
            t = dict()
            t.update(i["summary"])
            t["last_sync_result"] = i["last_sync_result"]
            t["last_sync_time"] = i["last_sync_time"]
            results.append(t)
    else:
        results = [i["summary"] for i in resp["Items"]]

    return results, 200


def list_select_software_titles(contributor_id, path_parameter):
    titles = path_parameter.split(",")

    def get_title(title_id):
        titles_table = dynamodb.Table(TITLES_TABLE)

        try:
            resp = titles_table.get_item(
                Key={"contributor_id": contributor_id, "title_id": title_id}
            )
        except ClientError:
            logger.exception("Unable to read title entry from DynamoDB!")
            return None

        if resp.get("Item"):
            return resp["Item"]["summary"]
        else:
            return None

    title_list = list()

    for title in titles:
        result = get_title(title)
        if result:
            title_list.append(result)

    return title_list, 200


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
