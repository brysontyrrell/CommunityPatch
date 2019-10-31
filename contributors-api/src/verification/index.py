import json
import logging
import os
from urllib.parse import urlencode, urlunparse

from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import InvalidToken


logger = logging.getLogger()
logger.setLevel(logging.INFO)

patch(["boto3"])

CONTRIBUTORS_TABLE = os.getenv("CONTRIBUTORS_TABLE")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")
EMAIL_SNS_TOPIC = os.getenv("EMAIL_SNS_TOPIC")

dynamodb = boto3.resource("dynamodb")
fernet = get_fernet()


def redirect_url(status):
    return urlunparse(
        ("https", DOMAIN_NAME, "", None, urlencode({"status": status}), None)
    )


def response(status):
    return {
        "isBase64Encoded": False,
        "statusCode": 302,
        "body": json.dumps(""),
        "headers": {
            "Content-Type": "application/json",
            "Location": redirect_url(status),
        },
    }


def send_email(recipient, name, token):
    sns_client = boto3.client("sns")

    try:
        resp = sns_client.publish(
            TopicArn=EMAIL_SNS_TOPIC,
            Message=json.dumps(
                {
                    "recipient": recipient,
                    "message_type": "api_token",
                    "message_data": {"display_name": name, "api_token": token},
                }
            ),
            MessageStructure="string",
        )
    except ClientError as error:
        logger.exception(f"Error sending SNS notification: {error}")
        raise


def get_contributor(contributor_id):
    contributors_table = dynamodb.Table(CONTRIBUTORS_TABLE)

    try:
        resp = contributors_table.get_item(Key={"id": contributor_id})
    except ClientError as error:
        logger.exception(
            f"Error retrieving the contributor {contributor_id}: " f"{error.response}"
        )
        raise

    contributor = resp.get("Item")

    try:
        contributor["email"] = fernet.decrypt(contributor["email"].value).decode()
    except (TypeError, InvalidToken):
        logger.exception("Unable to decrypt the contributor email address!")
        raise

    return contributor


def update_contributor(contributor_id, token_id):
    contributors_table = dynamodb.Table(CONTRIBUTORS_TABLE)

    try:
        resp = contributors_table.update_item(
            Key={"id": contributor_id},
            UpdateExpression="set token_id = :ti, verified_account = :v",
            ExpressionAttributeValues={":ti": token_id, ":v": True},
            ReturnValues="UPDATED_NEW",
        )
        logger.info(f"Contributor updated: {resp['Attributes']}")

    except ClientError as error:
        logger.exception(f"DynamoDB: {error.response}")
        raise


def lambda_handler(event, context):
    logger.info(event)
    try:
        contributor_id = event["queryStringParameters"]["id"]
        verification_code = event["queryStringParameters"]["code"]
    except (KeyError, TypeError):
        logger.error("Bad Request: Required values are missing")
        return response("missing-values")

    try:
        contributor = get_contributor(contributor_id)
    except:
        return response("error")

    if not contributor:
        logger.error(f"The ID '{contributor_id}' was not found on lookup")
        return response("not-found")

    if contributor["verified_account"]:
        logger.error("This contributor has already been verified")
        return response("already-verified")

    if verification_code != contributor["verification_code"]:
        logger.error("The verification codes do not match!")
        return response("invalid-code")

    api_token, token_id = create_token(contributor_id)

    try:
        update_contributor(contributor_id, token_id)
    except ClientError:
        return response("error")

    send_email(contributor["email"], contributor["display_name"], api_token)
    return response("success")
