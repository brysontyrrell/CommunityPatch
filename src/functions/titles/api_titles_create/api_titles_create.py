import json
import logging
import os
import time

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TITLES_TABLE = os.getenv('TITLES_TABLE')

dynamodb = boto3.resource('dynamodb')
s3_bucket = boto3.resource('s3').Bucket(os.getenv('TITLES_BUCKET'))

with open('schema_full_definition.json', 'r') as f_obj:
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
    titles_table = dynamodb.Table(TITLES_TABLE)

    try:
        titles_table.put_item(
            Item={
                "contributor_id": contributor_id,
                "title_id": patch_definition['id'],
                "last_sync_result": None,
                "last_sync_time": int(time.time()),
                "title_summary": {
                    "id": patch_definition['id'],
                    "name": patch_definition['name'],
                    "publisher": patch_definition['publisher'],
                    "currentVersion": patch_definition['currentVersion'],
                    "lastModified": patch_definition['lastModified']
                }
            },
            ConditionExpression='attribute_not_exists(title_id)'
        )
    except ClientError:
        logger.exception('Unable to write title entry to DynamoDB!')
        raise
    else:
        logger.info(f'Wrote title entry to DynamoDB')


def definition_from_json(data):
    logger.info('Loading definition from request body')
    patch_definition = data.get('definition')
    return create_definition(patch_definition, data)


def create_definition(patch_definition, contributor):
    """Create the definition in DynamoDB and S3"""


    try:
        resp = s3_bucket.put_object(
            Body=json.dumps(patch_definition),
            Key=patch_definition['id']
        )
    except ClientError as error:
        logger.exception(f'S3: {error}')
        return response(f'Internal Server Error: {error}', 500)
    else:
        logger.info(f'Wrote file to S3: {resp}')

    return response(
        'Software title created - check your email for your API token!', 201)


def lambda_handler(event, context):
    try:
        token = event['requestContext']['authorizer']['jti']
    except KeyError:
        logger.error('Token data not found!')
        return response('Bad Request', 400)

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
        create_table_entry('', data)
    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response("Conflict: You have already created a title with "
                            f"the ID '{data['id']}'", 409)
        else:
            return response(f'Internal Server Error', 500)

    return response('', 201)
