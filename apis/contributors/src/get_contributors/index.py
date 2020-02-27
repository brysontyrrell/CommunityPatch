import logging
from operator import itemgetter
import os

from aws_xray_sdk.core import patch
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

CONTRIBUTORS_TABLE = os.getenv("CONTRIBUTORS_TABLE")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")
TITLES_TABLE = os.getenv("TITLES_TABLE")

dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    results = list()

    for contributor in scan_table(CONTRIBUTORS_TABLE):
        uri = "/".join(["jamf/v1", contributor["id"], "software"])
        results.append(
            {
                "id": contributor["id"],
                "display_name": contributor["display_name"],
                "title_count": contributor["title_count"],
                "urn": uri,
                "url": f"https://{DOMAIN_NAME}/{uri}",
            }
        )

    return sorted(results, key=itemgetter("title_count"), reverse=True), 200


def scan_table(table_name):
    table = dynamodb.Table(table_name)

    results = table.scan()
    while True:
        for row in results["Items"]:
            yield row
        if results.get("LastEvaluatedKey"):
            results = dynamodb.scan(ExclusiveStartKey=results["LastEvaluatedKey"])
        else:
            break
