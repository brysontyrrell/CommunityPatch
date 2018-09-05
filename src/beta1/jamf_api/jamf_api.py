import io
import json
import logging
import os
import time

import boto3
from botocore.exceptions import ClientError

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


def scan_titles():
    results = dynamodb.scan()
    while True:
        for row in results['Items']:
            yield row
        if results.get('LastEvaluatedKey'):
            results = dynamodb.scan(
                ExclusiveStartKey=results['LastEvaluatedKey'])
        else:
            break


def get_title(title):
    try:
        resp = dynamodb.get_item(
            Key={'id': title},
            ProjectionExpression='title_summary'
        )
    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        return None

    if not resp.get('Item'):
        logger.error(f"The title '{title}' was not found on lookup: {resp}")
        return None

    return resp['Item']['title_summary']


def list_software_titles():
    try:
        titles = [item['title_summary'] for item in scan_titles()]
    except ClientError as error:
        logger.exception(f'DynamoDB: {error.response}')
        return response(f'Internal Server Error: {error}', 500)

    return response(titles, 200)


def list_select_software_titles(path_parameter):
    match_titles = path_parameter.split(',')

    title_list = list()
    for title in match_titles:
        result = get_title(title)
        if result:
            title_list.append(result)
            send_metric('SoftwareTitles', title, 'SubscribedCount')

    return response(title_list, 200)


def get_patch_definition(title):
    f_obj = io.BytesIO()

    try:
        s3_bucket.download_fileobj(title, f_obj)
    except ClientError:
        return response(f'Title Not Found: {title}', 404)

    data = json.loads(f_obj.getvalue())

    return response(data, 200)


def lambda_handler(event, context):
    logger.info(event)
    path = event['path']
    resource = event['resource']
    parameter = event['pathParameters']

    logger.info(f'Generating response for {path}')

    if resource == '/jamf/v1/software':
        send_metric('JamfEndpoints', '/jamf/v1/software', 'Requested')
        return list_software_titles()

    elif resource == '/jamf/v1/software/{proxy+}':
        send_metric(
            'JamfEndpoints', '/jamf/v1/software/<Title,Title>', 'Requested')
        return list_select_software_titles(parameter['proxy'])

    elif resource == '/jamf/v1/patch/{proxy+}':
        send_metric('JamfEndpoints', '/jamf/v1/patch/<Title>', 'Requested')
        return get_patch_definition(parameter['proxy'])

    else:
        return response('Not Found', 404)
