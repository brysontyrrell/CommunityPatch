import io
import json
import logging
import os
import queue
import threading

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

xray_recorder.configure(service='CommunityPatch')
patch(['boto3'])

s3_bucket_name = os.getenv('DEFINITIONS_BUCKET')

s3_client = boto3.client('s3')


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


def get_title_summary(title, client):
    resp = client.select_object_content(
        Bucket=s3_bucket_name,
        Key=title,
        ExpressionType='SQL',
        Expression="SELECT s.id,s.name,s.publisher,s.lastModified,s.currentVersion FROM S3Object s",
        InputSerialization={
            'CompressionType': 'NONE',
            'JSON': {
                'Type': 'DOCUMENT',
            }
        },
        OutputSerialization={
            'JSON': {}
        }
    )

    for i in resp['Payload']:
        if i.get('Records'):
            return json.loads(i['Records']['Payload'])


def queue_worker(q, title_list, thread_num):
    client = boto3.client('s3')
    while not q.empty():
        title = q.get()
        logger.info(f'Thread {thread_num}: Querying title {title}')
        title_list.append(get_title_summary(title, client))


def list_operation(path_parameter=None):
    if path_parameter:
        list_to_query = path_parameter.split(',')
    else:
        bucket_list = s3_client.list_objects(Bucket=s3_bucket_name)['Contents']
        list_to_query = [key['Key'] for key in bucket_list]

    number_of_threads = 16 if len(list_to_query) >= 16 else len(list_to_query)
    logger.info(f'Starting {number_of_threads} threads for the list operation')

    query_queue = queue.Queue()
    for i in list_to_query:
        query_queue.put(i)

    title_list = list()

    threads = list()
    for i in range(number_of_threads):
        t = threading.Thread(target=queue_worker, args=(query_queue, title_list, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return response(title_list, 200)


def list_software_titles():
    title_list = list()

    bucket_list = s3_client.list_objects(Bucket=s3_bucket_name)['Contents']

    definition_list = list()
    for key in bucket_list:
        definition_list.append(key['Key'])

    for definition in definition_list:
        title_list.append(get_title_summary(definition))

    return response(title_list, 200)


def list_select_software_titles(path_parameter):
    match_titles = path_parameter.split(',')

    title_list = list()

    for title in match_titles:
        result = get_title_summary(title)
        if result:
            title_list.append(result)

    return response(title_list, 200)


def get_patch_definition(title):
    f_obj = io.BytesIO()

    try:
        s3_client.download_fileobj(s3_bucket_name, title, f_obj)
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

    if resource == '/jamf2/v1/software':
        # return list_software_titles()
        return list_operation()

    elif resource == '/jamf2/v1/software/{proxy+}':
        # return list_select_software_titles(parameter['proxy'])
        return list_operation(parameter['proxy'])

    elif resource == '/jamf2/v1/patch/{proxy+}':
        return get_patch_definition(parameter['proxy'])

    else:
        return response('Not Found', 404)
