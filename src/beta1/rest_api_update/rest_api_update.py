from datetime import datetime
import io
import json
import logging
import os
import time

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb').Table(os.getenv('DEFINITIONS_TABLE'))
s3_bucket = boto3.resource('s3').Bucket(os.getenv('DEFINITIONS_BUCKET'))
sqs_queue = boto3.resource('sqs').Queue(os.getenv('METRICS_QUEUE_URL'))


def send_metric(name, value, metric):
    logger.info(f"Sending metric '{name}:{value}:{metric}' to queue")
    sqs_queue.send_message(
        MessageBody=json.dumps(
            {
                'name': name,
                'value': value,
                'metric': metric,
                'timestamp': time.time()
            }
        )
    )


with open('schema_version.json', 'r') as f_obj:
    version_schema = json.load(f_obj)


def response(message, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param str message: Message for JSON body of response
    :param int status_code: HTTP status code of response

    :rtype: dict
    """
    if status_code < 300:
        send_metric('RestApi', 'DefinitionUpdate', 'SuccessfulUpdate')
    else:
        send_metric('RestApi', 'DefinitionUpdate', 'FailedUpdate')

    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps({'message': message}),
        'headers': {'Content-Type': 'application/json'}
    }


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
            send_metric('RestApi', 'DefinitionUpdate', 'InsertAfterUsed')
            index = next((index for (index, d) in enumerate(patches) if
                          d["version"] == params.get('insert_after')), None) + 1

        elif params.get('insert_before'):
            send_metric('RestApi', 'DefinitionUpdate', 'InsertBeforeUsed')
            index = next((index for (index, d) in enumerate(patches) if
                          d["version"] == params.get('insert_before')), None)

        else:
            raise ValueError('Parameters have no values')

    if index is None:
        raise ValueError('Provided version not found')

    return index


def lambda_handler(event, context):
    parameters = event['pathParameters']
    query_string_parameters = event['queryStringParameters']

    try:
        token = event['requestContext']['authorizer']['jti']
    except KeyError:
        logger.error('Token data not found!')
        return response('Bad Request', 400)

    logger.info(f"Token data: {token}")

    title = parameters['title']

    logger.info('Loading JSON body')
    try:
        data = json.loads(event['body'])
    except (TypeError, json.JSONDecodeError):
        return response('Bad Request', 400)

    logger.info('Validating version against schema')
    try:
        validate(data, version_schema)
    except ValidationError as error:
        logger.error('The version JSON failed validation')
        send_metric('RestApi', 'VersionSchemaValidation', 'FailedCount')
        return response("Bad Request: The patch definition failed validation: "
                        f"{error.message} for path: "
                        f"/{'/'.join([str(i) for i in error.path])}", 400)

    logger.info(f"Downloading definition")
    f_obj = io.BytesIO()
    try:
        s3_bucket.download_fileobj(title, f_obj)
    except ClientError as error:
        logger.exception(f'S3: {error.response}')
        return response(f'Title Not Found: {title}', 404)

    patch_definition_file = json.loads(f_obj.getvalue())

    if data['version'] in \
            [patch_['version'] for patch_ in patch_definition_file['patches']]:
        logger.error(f"Conflicting version supplied: '{data['version']}'")
        return response(
            f"Conflict: The version '{data['version']}' already exists in "
            "the patch definition", 409)

    try:
        target_index = get_index(
            query_string_parameters, patch_definition_file['patches'])
    except ValueError as error:
        return response(f'Bad Request: {str(error)}', 400)

    logger.info(f"Updating the definition with new version: {data['version']}")
    patch_definition_file['patches'].insert(target_index, data)

    # Use the version of the first patch after the insert operation above
    patch_definition_file['currentVersion'] = \
        patch_definition_file['patches'][0]['version']

    patch_definition_file['lastModified'] = \
        datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.info("Updating database 'currentVersion' and 'lastModified'")
    try:
        resp = dynamodb.update_item(
            Key={'id': title},
            UpdateExpression="set title_summary.currentVersion = :v, "
                             "title_summary.lastModified = :m",
            ExpressionAttributeValues={
                ':v': patch_definition_file['currentVersion'],
                ':m': patch_definition_file['lastModified']
            },
            ReturnValues="UPDATED_NEW"
        )
        logger.info(f"DynamoDB updated: {resp['Attributes']}")
    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        return response(f'Internal Server Error: {error}', 500)

    logger.info('Saving updated definition to S3')
    try:
        s3_bucket.put_object(Body=json.dumps(patch_definition_file), Key=title)
    except ClientError as error:
        logger.exception(f'S3: {error.response}')
        return response(f'Internal Server Error: {error}', 500)

    logger.info(f"Version '{data['version']}' added to '{title}'")
    return response(f"Version '{data['version']}' added to '{title}'", 201)
