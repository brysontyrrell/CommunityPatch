import json
import logging
import os

from aws_xray_sdk.core import patch
import boto3
import jinja2

logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

DOMAIN_NAME = os.getenv("DOMAIN_NAME")

function_dir = os.path.dirname(os.path.abspath(__file__))

jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(function_dir, "templates")),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)

ses_client = boto3.client("ses", region_name="us-east-1")


def lambda_handler(event, context):
    """This function is meant to be triggered by an SNS event. The expected
    JSON body of the SNS message should be formatted as:

    .. code-block: json

        {
            "recipient": "bryson.tyrrell@gmail.com",
            "message_type": "verification",
            "message_data": {
                "display_name": "bryson",
                "url": "https://beta.communitypatch.com/api/v1/verify?id=0dc38324342ab156f65d016675827d41&code=9b0ca3fd24f0460ba90256009c1a9cef"
            }
        }
    """
    if event.get("Records"):
        logging.info("Processing SNS records...")
        for record in event["Records"]:
            data = json.loads(record["Sns"]["Message"])
            send_email(data)

    else:
        logging.warning("No SNS records found in the event")

    return {}


def send_email(data):
    message_type = data["message_type"]

    html_template = jinja2_env.get_template(f"{message_type}.html")
    text_template = jinja2_env.get_template(f"{message_type}.txt")

    if data["message_data"].get("display_name"):
        subject = f"Community Patch ({data['message_data']['display_name']})"
    else:
        subject = "Community Patch"

    return ses_client.send_email(
        Destination={"ToAddresses": [data["recipient"]]},
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
