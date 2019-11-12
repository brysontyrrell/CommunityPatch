import base64
from functools import lru_cache
import json
import logging
import os
from urllib.parse import urlencode, urlunparse

from aws_xray_sdk.core import patch
import boto3
from cryptography.fernet import Fernet
import jinja2

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

DOMAIN_NAME = os.getenv("DOMAIN_NAME")
FUNCTION_DIR = os.path.dirname(os.path.abspath(__file__))
NAMESPACE = os.getenv("NAMESPACE")

jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(FUNCTION_DIR, "templates")),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)


def lambda_handler(event, context):
    """This function is meant to be triggered by an SNS event. The expected
    JSON body of the SNS message should be formatted as:

    .. code-block: json

        {
            "recipient": "<bryson.tyrrell@gmail.com>",  # Encrypted
            "message_type": "verification",
            "message_data": {
                "display_name": "bryson",
                "url": "https://beta.communitypatch.com/api/v1/verify?id=0dc38324342ab156f65d016675827d41&code=9b0ca3fd24f0460ba90256009c1a9cef"
            }
        }
    """
    if event.get("Records"):
        # Invoked by SNS
        logging.info("Processing SNS records...")
        for record in event["Records"]:
            data = json.loads(record["Sns"]["Message"])
            send_email(data)

    else:
        # Invoked directly
        logging.info("Processing event...")
        send_email(event)

    return {}


@lru_cache()
def boto3_session():
    return boto3.Session()


@lru_cache()
def ses_client():
    return boto3_session().client("ses", region_name="us-east-1")


@lru_cache()
def get_fernet():
    ssm_client = boto3_session().client("ssm")
    resp = ssm_client.get_parameter(
        Name=f"/communitypatch/{NAMESPACE}/database_key", WithDecryption=True
    )
    return Fernet(resp["Parameter"]["Value"])


def send_email(data):
    message_type = data["message_type"]

    if message_type == "verification":
        data['message_data']['url'] = urlunparse(
            (
                'https',
                f"contributors.{DOMAIN_NAME}",
                'v1/verify',
                None,
                urlencode({'code': base64.b64encode(data['task_token'].encode()).decode()}),
                None
            )
        )

    html_template = jinja2_env.get_template(f"{message_type}.html")
    text_template = jinja2_env.get_template(f"{message_type}.txt")

    if data["message_data"].get("display_name"):
        subject = f"Community Patch ({data['message_data']['display_name']})"
    else:
        subject = "Community Patch"

    decrypted_recipient = get_fernet().decrypt(data["recipient"])

    return ses_client().send_email(
        Destination={"ToAddresses": [decrypted_recipient]},
        Message={
            "Body": {
                "Html": {
                    "Charset": "UTF-8",
                    "Data": html_template.render(message=data["message_data"]),
                },
                "Text": {
                    "Charset": "UTF-8",
                    "Data": text_template.render(message=data["message_data"]),
                },
            },
            "Subject": {"Charset": "UTF-8", "Data": subject},
        },
        Source=f"Commuinity Patch <noreply@{DOMAIN_NAME}>",
    )
