import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def read_schema(schema):
    with open(f"schemas/{schema}.json", "r") as f_obj:
        return json.load(f_obj)


communitypatchtable = boto3.resource("dynamodb").Table(
    os.getenv("COMMUNITY_PATCH_TABLE")
)

schema_definition = read_schema("full_definition")


def lambda_handler(event, context):
    # Not consistent with Cognito auth
    authenticated_claims = event["requestContext"]["authorizer"]

    try:
        title_body = json.loads(event["body"])
    except (TypeError, json.JSONDecodeError):
        logger.exception("Bad Request: No JSON content found")
        return response("Bad Request: No JSON content found", 400)

    try:
        validate(title_body, schema_definition)
    except ValidationError as error:
        validation_error = (
            f"Validation Error {str(error.message)} "
            f"for item: {'/'.join([str(i) for i in error.path])}"
        )
        logger.error(validation_error)
        return response(validation_error, 400)

    try:
        create_table_entry(authenticated_claims["sub"], title_body)
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(
                f"Conflict: You have already created a title with the ID '{title_body['id']}'",
                409,
            )
        else:
            logger.exception("Unknown ClientError writing new title.")
            return response(f"Internal Server Error", 500)

    return response(f"Title '{title_body['id']}' created", 201)


def create_table_entry(contributor_id, title_body):
    communitypatchtable.put_item(
        Item={
            "contributor_id": contributor_id,
            "type": f"TITLE#{title_body['id'].lower()}",
            "search_index": "TITLE",
            "aws_region": os.getenv("AWS_REGION"),
            "title_id": title_body["id"].lower(),
            "body": json.dumps(title_body),
            "summary": {
                "id": title_body["id"],
                "name": title_body["name"],
                "publisher": title_body["publisher"],
                "currentVersion": title_body["currentVersion"],
                "lastModified": title_body["lastModified"],
            },
        },
        ConditionExpression="attribute_not_exists(#type)",
        ExpressionAttributeNames={"#type": "type"},
    )


def response(message, status_code):
    if isinstance(message, str):
        message = {"message": message}

    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(message),
        "headers": {"Content-Type": "application/json"},
    }
