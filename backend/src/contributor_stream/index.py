from decimal import Decimal
import json
import logging
import os

from aws_xray_sdk.core import patch
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

CONTRIBUTOR_STREAM_TOPIC = os.getenv("CONTRIBUTOR_STREAM_TOPIC")

sns_topic = boto3.resource("sns").Topic(CONTRIBUTOR_STREAM_TOPIC)


def lambda_handler(event, context):
    logger.info(event)
    sns_topic.publish(Message=json.dumps(event, cls=DecimalEncoder))
    return "ok"


class DecimalEncoder(json.JSONEncoder):
    """A custom JSON decoder to handle the use of ``decimal.Decimal`` objects in
    returned data from ``boto3`` DynamoDB resource.
    """

    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return json.JSONEncoder.default(self, obj)
