import base64
from decimal import Decimal
import json
import logging
import os
import time

from aws_xray_sdk.core import patch
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

DOMAIN_NAME = os.getenv("DOMAIN_NAME")
REGISTRATION_SERVICE = os.getenv("REGISTRATION_SERVICE")
NAMESPACE = os.getenv("NAMESPACE")

sf_client = boto3.client("stepfunctions")


def lambda_handler(event, context):
    logger.info(event)
    stream_records = load_sns_event(event)

    for record in stream_records:

        if record["eventName"] == "INSERT":
            # INSERT only occurs on new registrations
            new_image = parse_dynamodb_stream(record, 'NewImage')
            sf_client.start_execution(
                stateMachineArn=REGISTRATION_SERVICE,
                name=f"{new_image['display_name']}-{int(time.time())}",
                input=json.dumps(new_image),
            )

        elif record["eventName"] == "MODIFY":
            new_image = parse_dynamodb_stream(record, 'NewImage')
            old_image = parse_dynamodb_stream(record, 'OldImage')
            # Determine the delta from the OldImage and discard AWS keys
            delta = {
                k: new_image[k]
                for k in new_image
                if k in old_image
                and new_image[k] != old_image[k]
                and not k.startswith("aws:")
            }
            logger.info(f"Delta: {delta}")

    return "ok"


def load_sns_event(event):
    """An SNS event should only contain one Record."""
    record = event['Records'][0]
    return json.loads(record['Sns']['Message'])['Records']


def parse_dynamodb_stream(record, image):
    result = dict()

    def stream_to_dict(data):
        stream = dict()
        for k, v in data.items():
            if v.get("NULL"):
                stream[k] = None
            elif v.get("S"):
                stream[k] = str(v["S"])
            elif v.get("N"):
                number = Decimal(v["N"])
                if number % 1 == 0:
                    stream[k] = int(number)
                else:
                    stream[k] = float(number)
            elif v.get("BOOL") is not None:
                stream[k] = bool(v["BOOL"])
            elif v.get("B"):
                stream[k] = base64.b64decode(v["B"])
            elif v.get("M"):
                stream[k] = stream_to_dict(v["M"])
        return stream

    result.update(stream_to_dict(record["dynamodb"]["Keys"]))
    result.update(stream_to_dict(record["dynamodb"][image]))
    return result
