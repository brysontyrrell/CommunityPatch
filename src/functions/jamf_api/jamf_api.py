import json
import logging
import os
import shutil
import tempfile

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb').Table(os.getenv('DEFINITIONS_TABLE'))
s3_bucket = boto3.resource('s3').Bucket(os.getenv('DEFINITIONS_BUCKET'))


def response(body_data, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param body_data: Content for JSON body of response
    :type body_data: str or dict or list

    :param int status_code: HTTP status code of response

    :rtype: dict
    """
    if isinstance(body_data, str):
        body = json.dumps({'message': body_data})
    else:
        body = json.dumps(body_data)

    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': body,
        'headers': {'Content-Type': 'application/json'}
    }


def scan_table():
    results = dynamodb.scan()
    while True:
        for row in results['Items']:
            yield row
        if results.get('LastEvaluatedKey'):
            results = dynamodb.scan(
                ExclusiveStartKey=results['LastEvaluatedKey'])
        else:
            break


def list_software_titles():
    try:
        titles = [item['title_summary'] for item in scan_table()]
    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        return response(f'Internal Server Error: {error}', 500)

    return response(titles, 200)


def list_select_software_titles(path_parameter):
    match_titles = path_parameter.split(',')

    try:
        titles = [
            item['title_summary'] for item in scan_table()
            if item['id'] in match_titles
        ]
    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        return response(f'Internal Server Error: {error}', 500)

    return response(titles, 200)


def get_patch_definition(title):
    tempdir = tempfile.mkdtemp()
    path = os.path.join(tempdir, title)

    try:
        s3_bucket.download_file(title, path)
    except ClientError:
        shutil.rmtree(tempdir)
        return response(f'Title Not Found: {title}', 404)

    with open(path, 'r') as f_obj:
        data = json.load(f_obj)

    shutil.rmtree(tempdir)
    return response(data, 200)


def lambda_handler(event, context):
    logger.info(event)
    path = event['path']
    resource = event['resource']
    parameter = event['pathParameters']

    logger.info(f'Generating response for {path}')

    if resource == '/jamf/v1/software':
        return list_software_titles()

    elif resource == '/jamf/v1/software/{proxy+}':
        return list_select_software_titles(parameter['proxy'])

    elif resource == '/jamf/v1/patch/{proxy+}':
        return get_patch_definition(parameter['proxy'])

    else:
        return response('Not Found', 404)
