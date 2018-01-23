import json
import os
import shutil
import tempfile

import boto3
from botocore.exceptions import ClientError

s3_bucket = boto3.resource('s3').Bucket(os.environ['S3_BUCKET'])
tempdir = ''


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
            return response({'error': f'Internal Server Error: Unable to load data for: {title.key}'}, 500)

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
                return response({'error': f'Title Not Found: {title_name}'}, 404)

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

    path = event['pathParameters']['proxy'].split('/')

    if path[0] == 'software' and len(path) == 1:
        return software()
    elif path[0] == 'software' and len(path) == 2:
        titles = path[1].split(',')
        return select_software(titles)
    elif path[0] == 'patch' and len(path) == 2:
        title = path[1]
        return patch_title(title)
    else:
        return response({'error': f"Bad Request: {event['path']}"}, 400)
