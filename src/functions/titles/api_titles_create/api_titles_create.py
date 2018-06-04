import json
import logging
import os

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

TITLES_TABLE = os.getenv('TITLES_TABLE')

dynamodb = boto3.resource('dynamodb')
s3_bucket = boto3.resource('s3').Bucket(os.getenv('TITLES_BUCKET'))

with open('schemas/schema_full_definition.json', 'r') as f_obj:
    schema_definition = json.load(f_obj)


def response(message, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param message: Message for JSON body of response
    :type message: str or dict

    :param int status_code: HTTP status code of response

    :rtype: dict
    """
    if isinstance(message, str):
        message = {'message': message}

    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def create_table_entry(patch_definition, contributor_id):
    """Write the definition to DynamoDB table"""
    titles_table = dynamodb.Table(TITLES_TABLE)

    try:
        titles_table.put_item(
            Item={
                "contributor_id": contributor_id,
                "title_id": patch_definition['id'],
                "api_allowed": True,
                "summary": {
                    "id": patch_definition['id'],
                    "name": patch_definition['name'],
                    "publisher": patch_definition['publisher'],
                    "currentVersion": patch_definition['currentVersion'],
                    "lastModified": patch_definition['lastModified']
                },
                "last_sync_result": None,
                "last_sync_time": None
            },
            ConditionExpression='attribute_not_exists(title_id)'
        )
    except ClientError:
        logger.exception('Unable to write title entry to DynamoDB!')
        raise


def delete_table_entry(patch_id, contributor_id):
    pass


def write_definition_to_s3(patch_definition, contributor_id):
    """Save the definition to S3 bucket"""
    try:
        s3_bucket.put_object(
            Body=json.dumps(patch_definition),
            Key=os.path.join(contributor_id, patch_definition['id']),
            ContentType='application/json'
        )
    except ClientError:
        logger.exception('Unable to write title JSON to S3')
        raise


def lambda_handler(event, context):
    try:
        contributor_id = event['requestContext']['authorizer']['sub']
    except KeyError:
        logger.error('Token data not found!')
        return response('Forbidden', 403)

    try:
        data = json.loads(event['body'])
    except (TypeError, json.JSONDecodeError):
        logger.exception('Bad Request: No JSON content found')
        return response('Bad Request: No JSON content found', 400)

    try:
        validate(data, schema_definition)
    except ValidationError as error:
        logger.error('Bad Request: One or more required fields are missing')
        return response(
            {
                'message': 'Bad Request: The definition failed validation',
                'validation_error': f"{str(error.message)} for item: "
                                    f"{'/'.join([str(i) for i in error.path])}"
            },
            400
        )

    try:
        create_table_entry(data, contributor_id)
    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response("Conflict: You have already created a title with "
                            f"the ID '{data['id']}'", 409)
        else:
            return response(f'Internal Server Error', 500)

    try:
        write_definition_to_s3(data, contributor_id)
    except ClientError:
        # Delete the DynamoDB entry for cleanup
        return response('Internal Server Error', 500)

    return response(f"Title '{data['id']}' created", 201)
