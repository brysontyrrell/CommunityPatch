from datetime import datetime
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

schema_definition = read_schema("version")


class ApiException(Exception):
    status_code = 500


class BadRequest(ApiException):
    status_code = 400


class NotFound(ApiException):
    status_code = 404


class Conflict(ApiException):
    status_code = 409


def lambda_handler(event, context):
    # Not consistent with Cognito auth
    authenticated_claims = event["requestContext"]["authorizer"]

    try:
        current_title_body = read_title(
            authenticated_claims["sub"], event["pathParameters"]["title_id"]
        )
    except KeyError:
        return response("Not Found", 404)

    # ADD VERSION
    if (
        event["resource"] == "/v1/titles/{title_id}/versions"
        and event["httpMethod"] == "POST"
    ):
        try:
            version_body = json.loads(event["body"])
        except (TypeError, json.JSONDecodeError):
            logger.exception("Bad Request: No JSON content found")
            return response("Bad Request: No JSON content found", 400)

        try:
            validate(version_body, schema_definition)
        except ValidationError as error:
            validation_error = (
                f"Validation Error {str(error.message)} "
                f"for item: {'/'.join([str(i) for i in error.path])}"
            )
            logger.error(validation_error)
            return response(validation_error, 400)

        try:
            updated_title_body = add_version(
                current_title_body, version_body, event["queryStringParameters"]
            )
            update_title(authenticated_claims["sub"], updated_title_body)
            return response(
                f"Version '{version_body['version']}' added to title '{updated_title_body['id']}'",
                201,
            )
        except ApiException as error:
            return response(str(error), error.status_code)

    # DELETE VERSION
    elif (
        event["resource"] == "/v1/titles/{title_id}/versions/{version}"
        and event["httpMethod"] == "DELETE"
    ):
        target_version = event["pathParameters"]["version"]
        try:
            updated_title_body = delete_version(current_title_body, target_version)
            update_title(authenticated_claims["sub"], updated_title_body)
            return response(f"Version '{target_version}' deleted from title", 200,)
        except ApiException as error:
            return response(str(error), error.status_code)

    else:
        return response("Not Found", 404)


def read_title(contributor_id, title_id):
    result = communitypatchtable.get_item(
        Key={"contributor_id": contributor_id, "type": f"TITLE#{title_id.lower()}"}
    )
    return json.loads(result["Item"]["body"])


def add_version(title_body, version_body, query_string_parameters):
    if version_body["version"] in [
        patch_["version"] for patch_ in title_body["patches"]
    ]:
        logger.error(f"Conflicting version supplied: '{version_body['version']}'")
        raise Conflict(f"Conflict: The version '{version_body['version']}' exists")

    try:
        target_index = get_index(query_string_parameters, title_body["patches"])
    except ValueError as error:
        raise BadRequest(f"Bad Request: {str(error)}")

    logger.info(f"Updating the definition with new version: {version_body['version']}")
    title_body["patches"].insert(target_index, version_body)

    # Use the version of the first patch after the insert operation above
    title_body["currentVersion"] = title_body["patches"][0]["version"]
    title_body["lastModified"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    return title_body


def delete_version(title_body, target_version):
    index = next(
        (
            idx
            for (idx, d) in enumerate(title_body["patches"])
            if d["version"] == target_version
        ),
        None,
    )

    if index is None:
        raise BadRequest("Not Found")

    if len(title_body["patches"]) < 2:
        raise BadRequest("A title must contain at least 1 version")

    logger.info(f"Removing version from the definition: {target_version}")
    title_body["patches"].pop(index)

    # Use the version of the first patch after the delete operation above
    title_body["currentVersion"] = title_body["patches"][0]["version"]
    title_body["lastModified"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    return title_body


def get_index(qs_params, title_patches):
    """If 'insert_after' or 'insert_before' were passed as parameters, return
    the target index for the provided target version.

    If 'params' is 'None' or empty, return 0.

    :param qs_params: Query string parameters
    :type qs_params: dict or None

    :param list title_patches: The 'patches' array from a definition
    """
    if not qs_params:
        return 0

    if all(i in qs_params.keys() for i in ["insert_after", "insert_before"]):
        raise ValueError("Conflicting parameters provided")

    index = None
    if any(i in qs_params.keys() for i in ["insert_after", "insert_before"]):

        if qs_params.get("insert_after"):
            index = (
                next(
                    (
                        idx
                        for (idx, d) in enumerate(title_patches)
                        if d["version"] == qs_params.get("insert_after")
                    ),
                    None,
                )
                + 1
            )

        elif qs_params.get("insert_before"):
            index = next(
                (
                    idx
                    for (idx, d) in enumerate(title_patches)
                    if d["version"] == qs_params.get("insert_before")
                ),
                None,
            )

        else:
            raise ValueError("Parameter has no value")

    if index is None:
        raise ValueError("Provided version not found")

    return index


def update_title(contributor_id, title_body):
    communitypatchtable.update_item(
        Key={"contributor_id": contributor_id, "type": f"TITLE#{title_body['id']}"},
        UpdateExpression="set body = :bd, "
        "summary.currentVersion = :cv, "
        "summary.lastModified = :lm",
        ExpressionAttributeValues={
            ":bd": json.dumps(title_body),
            ":cv": title_body["currentVersion"],
            ":lm": title_body["lastModified"],
        },
        ReturnValues="UPDATED_NEW",
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
