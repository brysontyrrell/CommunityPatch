from datetime import datetime
import io
import json
import logging
import os
import sys

# Add '/opt' to the PATH for Lambda Layers
sys.path.append('/opt')

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError

from api_helpers import response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

TITLES_TABLE = os.getenv('TITLES_TABLE')

titles_table = boto3.resource('dynamodb').Table(os.getenv('TITLES_TABLE'))
s3_bucket = boto3.resource('s3').Bucket(os.getenv('TITLES_BUCKET'))


with open('schemas/schema_version.json', 'r') as f_obj:
    schema_version = json.load(f_obj)


def read_table_entry(title_id, contributor_id):
    try:
        resp = titles_table.get_item(
            Key={
                'contributor_id': contributor_id,
                'title_id': title_id
            }
        )
    except ClientError:
        logger.exception('Unable to read title entry from DynamoDB!')
        raise

    return resp.get('Item')


def read_definition_from_s3(contributor_id, title_id):
    f_obj = io.BytesIO()
    try:
        s3_bucket.download_fileobj(
            Key=os.path.join('titles', contributor_id, title_id),
            Fileobj=f_obj
        )
    except ClientError:
        logger.exception('Unable to read title JSON from S3')
        raise

    return json.loads(f_obj.getvalue())


def update_table_entry(title_data, contributor_id):
    logger.info("Updating database 'currentVersion' and 'lastModified'")
    try:
        titles_table.update_item(
            Key={
                'contributor_id': contributor_id,
                'title_id': title_data['id']
            },
            UpdateExpression="set summary.currentVersion = :cv, "
                             "summary.lastModified = :lm",
            ExpressionAttributeValues={
                ':cv': title_data['currentVersion'],
                ':lm': title_data['lastModified']
            },
            ReturnValues="UPDATED_NEW"
        )
    except ClientError:
        logger.exception('Unable to write title entry to DynamoDB!')
        raise


def write_definition_to_s3(patch_definition, contributor_id):
    """Save the definition to S3 bucket"""
    try:
        s3_bucket.put_object(
            Body=json.dumps(patch_definition),
            Key=os.path.join('titles', contributor_id, patch_definition['id']),
            ContentType='application/json'
        )
    except ClientError:
        logger.exception('Unable to write title JSON to S3')
        raise


def get_index(params, patches):
    """If 'insert_after' or 'insert_before' were passed as parameters, return
    the target index for the provided target version.

    If 'params' is 'None' or empty, return 0.

    :param params: Query string parameters
    :type params: dict or None

    :param list patches: The 'patches' array from a definition
    """
    if not params:
        return 0

    if all(i in params.keys() for i in ['insert_after', 'insert_before']):
        raise ValueError('Conflicting parameters provided')

    index = None
    if any(i in params.keys() for i in ['insert_after', 'insert_before']):

        if params.get('insert_after'):
            index = next((index for (index, d) in enumerate(patches) if
                          d["version"] == params.get('insert_after')), None) + 1

        elif params.get('insert_before'):
            index = next((index for (index, d) in enumerate(patches) if
                          d["version"] == params.get('insert_before')), None)

        else:
            raise ValueError('Parameters have no values')

    if index is None:
        raise ValueError('Provided version not found')

    return index


def add_version(event):
    contributor_id = event['requestContext']['authorizer']['sub']
    title_id = event['pathParameters']['title']
    query_string_parameters = event['queryStringParameters']

    try:
        data = json.loads(event['body'])
    except (TypeError, json.JSONDecodeError):
        logger.exception('Bad Request: No JSON content found')
        return response('Bad Request: No JSON content found', 400)

    try:
        validate(data, schema_version)
    except ValidationError as error:
        logger.error('Bad Request: One or more required fields are missing')
        return response(
            {
                'message': 'Bad Request: The version failed validation',
                'validation_error': f"{str(error.message)} for item: "
                f"{'/'.join([str(i) for i in error.path])}"
            },
            400
        )

    definition = read_definition_from_s3(contributor_id, title_id)

    if data['version'] in \
            [patch_['version'] for patch_ in definition['patches']]:
        logger.error(f"Conflicting version supplied: '{data['version']}'")
        return response(
            f"Conflict: The version '{data['version']}' exists", 409)

    try:
        target_index = get_index(query_string_parameters, definition['patches'])
    except ValueError as error:
        return response(f'Bad Request: {str(error)}', 400)

    logger.info(f"Updating the definition with new version: {data['version']}")
    definition['patches'].insert(target_index, data)

    # Use the version of the first patch after the insert operation above
    definition['currentVersion'] = \
        definition['patches'][0]['version']
    definition['lastModified'] = \
        datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    update_table_entry(definition, contributor_id)
    write_definition_to_s3(definition, contributor_id)
    # Need to revert the DynamoDB entry for cleanup on write failure

    return response(
        f"Version '{data['version']}' added to title '{title_id}'", 201)


def delete_version(event):
    contributor_id = event['requestContext']['authorizer']['sub']
    title_id = event['pathParameters']['title']
    version = event['pathParameters']['version']

    definition = read_definition_from_s3(contributor_id, title_id)

    if len(definition['patches']) < 2:
        return response('A title must contain at least 1 version', 400)

    index = next((idx for (idx, d) in enumerate(definition['patches']) if
                  d['version'] == version), None)

    if index is None:
        return response('Not Found', 404)

    logger.info(f"Removing version from the definition: {version}")
    definition['patches'].pop(index)

    # Use the version of the first patch after the delete operation above
    definition['currentVersion'] = definition['patches'][0]['version']
    definition['lastModified'] = \
        datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    update_table_entry(definition, contributor_id)
    write_definition_to_s3(definition, contributor_id)
    # Need to revert the DynamoDB entry for cleanup on write failure

    return response(f"Version '{version}' deleted from title", 200)


def lambda_handler(event, context):
    resource = event['resource']

    contributor_id = event['requestContext']['authorizer']['sub']
    title_id = event['pathParameters']['title']

    current_entry = read_table_entry(title_id, contributor_id)

    if not current_entry:
        return response('Title Not Found', 404)

    if not current_entry['api_allowed']:
        return response('Forbidden: API not allowed for this title', 403)

    # There is a lot of duplicate code between these two methods. This should
    # be improved/consolidated later.
    if resource == '/api/v1/titles/{title}/version':
        return add_version(event)

    elif resource == '/api/v1/titles/{title}/version/{version}':
        return delete_version(event)
