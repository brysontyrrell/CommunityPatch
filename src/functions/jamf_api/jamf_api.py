import json
import os
import shutil
import tempfile

import boto3
from botocore.exceptions import ClientError

s3_bucket = boto3.resource('s3').Bucket(os.environ['S3_BUCKET'])
tempdir = ''

# Downloading files from S3 is time consuming. ~40 patch definitions that need
# to be loaded range from 4-5 seconds for the entire request. There are a few
# options for bringing this response time down:
#
#  - Increase function memory: 128->256 cuts time down by nearly %50, but
#    will consume more GB-seconds.
#  - Implement parallel downloading: local processing of files is quick. The
#    longest execution comes from downloading from S3. Writing in parallel
#    downloads will yield faster responses.
#  - Drop S3, move definitions to DynamoDB: the nuclear solution, but will
#    likely yield the fastest speeds.


def response(message, status_code):
    print(message)
    shutil.rmtree(tempdir)
    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def title_list():
    titles = os.listdir(tempdir)
    print(f'Temp Dir Contents: {titles}')
    software_titles = list()

    for title in titles:
        with open(os.path.join(tempdir, title), 'r') as f_obj:
            data = json.load(f_obj)

            software_titles.append(
                {
                    'name': data['name'],
                    'publisher': data['publisher'],
                    'lastModified': data['lastModified'],
                    'currentVersion': data['currentVersion'],
                    'id': data['id']
                }
            )

    return software_titles


def software():
    for title in s3_bucket.objects.all():
        try:
            path = os.path.join(tempdir, title.key)
            s3_bucket.download_file(title.key, path)
        except ClientError:
            return response(
                {'error': f'Internal Server Error: '
                          f'Unable to load data for: {title.key}'},
                500
            )

    return response(title_list(), 200)


def select_software(titles):
    print(f"Selected software titles requested: {', '.join(titles)}")
    print(titles)
    for title in s3_bucket.objects.all():
        title_name = title.key.split('.')[0]
        print(f'Title Name: {title_name}')
        if title.key.split('.')[0] in titles:
            print('Matched!')
            try:
                path = os.path.join(tempdir, title.key)
                s3_bucket.download_file(title.key, path)
            except ClientError:
                return response(
                    {'error': f'Title Not Found: {title_name}'}, 404)

    return response(title_list(), 200)


def patch_title(title):
    path = os.path.join(tempdir, title)

    try:
        s3_bucket.download_file(f'{title}.json', path)
    except ClientError:
        return response({'error': f'Title Not Found: {title}'}, 404)

    with open(path, 'r') as f_obj:
        data = json.load(f_obj)

    return response(data, 200)


def lambda_handler(event, context):
    global tempdir
    tempdir = tempfile.mkdtemp()

    resource = event['resource']
    parameter = event['pathParameters']

    if resource == '/jamf/v1/software':
        return software()

    elif resource == '/jamf/v1/software/{proxy+}' and parameter:
        return select_software(parameter['proxy'].split(','))

    elif resource == '/jamf/v1/patch/{proxy+}' and parameter:
        return patch_title(parameter['proxy'])
