from datetime import datetime
import json
import logging
import os
import shutil
import tempfile

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb').Table(os.getenv('DEFINITIONS_TABLE'))
s3_bucket = boto3.resource('s3').Bucket(os.getenv('DEFINITIONS_BUCKET'))

with open('schema_version.json', 'r') as f_obj:
    version_schema = json.load(f_obj)


def response(message, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param str message: Message for JSON body of response
    :param int status_code: HTTP status code of response

    :rtype: dict
    """
    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps({'message': message}),
        'headers': {'Content-Type': 'application/json'}
    }


def main(title, body):
    """
    """
    logger.info('Loading JSON body')
    try:
        data = json.loads(body)
    except (TypeError, json.JSONDecodeError):
        return response('Bad Request', 400)

    logger.info('Validating version against schema')
    try:
        validate(data, version_schema)
    except ValidationError as error:
        logger.error('The software title JSON failed validation')
        return response("Bad Request: The patch definition failed validation: "
                        f"{error.message} for path: "
                        f"/{'/'.join([str(i) for i in error.path])}", 400)

    logger.info(f"Looking up title '{title}' in database")
    try:
        resp = dynamodb.get_item(Key={'id': title})
    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        return response(f'Internal Server Error: {error}', 500)

    if not resp.get('Item'):
        return response(f'Not Found: {title}', 404)

    tempdir = tempfile.mkdtemp()
    path = os.path.join(tempdir, title)

    logger.info(f"Downloading definition to {path}")
    try:
        s3_bucket.download_file(title, path)
    except ClientError as error:
        shutil.rmtree(tempdir)
        logger.exception(f'S3: {error.response}')
        return response(f'Title Not Found: {title}', 404)

    logger.info('Loading definition JSON')
    with open(path, 'r') as f_obj:
        patch_definition_file = json.load(f_obj)

    logger.info(f'Removing {path}')
    shutil.rmtree(tempdir)

    if data['version'] in \
            [patch['version'] for patch in patch_definition_file['patches']]:
        logger.error(f"Conflicting version supplied: '{data['version']}'")
        return response(
            f"Conflict: The version '{data['version']}' already exists in "
            "the patch definition", 409)

    logger.info(f"Updating the definition with new version: {data['version']}")
    patch_definition_file['patches'].insert(0, data)
    patch_definition_file['lastModified'] = \
        datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    patch_definition_file['currentVersion'] = data['version']

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

    logger.info(f"Software title update for '{title}' successful!")
    return response(f"'{title}' updated to version '{data['version']}'", 201)


def lambda_handler(event, context):
    parameter = event['pathParameters']
    try:
        token = event['requestContext']['authorizer']['jti']
    except KeyError:
        logger.error('Token data not found!')
        return response('Bad Request', 400)

    logger.info(f"Token data: {token}")

    return main(parameter['title'], event['body'])
