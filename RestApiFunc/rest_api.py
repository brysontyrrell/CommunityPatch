from datetime import datetime
import json
import os
import shutil
import tempfile

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError

dynamodb = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
s3_bucket = boto3.resource('s3').Bucket(os.environ['S3_BUCKET'])
tempdir = ''

with open('schema_full_definition.json', 'r') as f_obj:
    definition_schema = json.load(f_obj)

with open('schema_version.json', 'r') as f_obj:
    version_schema = json.load(f_obj)


def response(message, status_code):
    print(message)
    if os.path.exists(tempdir):
        shutil.rmtree(tempdir)

    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def validate_definition(data, use_version=False):
    try:
        validate(data, version_schema if use_version else definition_schema)
    except ValidationError as error:
        return response(
            {'error': f"Validation Error in submitted JSON : {error.message} "
                      f"for path: /{'/'.join([str(i) for i in error.path])}"},
            400
        )

    return None


def check_if_title_exists(title):
    try:
        s3_bucket.Object(f'{title}.json').metadata
    except ClientError:
        return False

    return True


def check_if_subscription(title):
    try:
        db_check = dynamodb.get_item(
            Key={'id': title}
        )
    except ClientError as error:
        return response({'error': f'Internal Server Error: {error}'}, 500)

    if db_check.get('Item'):
        return response(
            {'error': f"Bad Request: The software title ID '{title}' is a "
                      f"subscribed patch definition!"},
            400
        )

    return None


def post_definition(data):
    """
    - Validate JSON
        - Return 400 if invalid
    - Check if title exists
        - Return 409 if it does
    - Return 201

    """
    validation = validate_definition(data)
    if validation:
        return validation

    title = data['id']

    if check_if_title_exists(title):
        return response(
            {'error': 'Conflict: The patch definition already exists'}, 409)

    try:
        s3_bucket.put_object(
            Body=json.dumps(data),
            Key=f"{title}.json"
        )
    except ClientError as error:
        return response({'error': f'Internal Server Error: {error}'}, 500)

    return response(
        {'success': f"Successfully created patch definition for '{title}'"},
        201
    )


def put_definition(title, data):
    """
    - Validate JSON
        - Return 400 if invalid
    - Check if title is a subscription
        - Return 400 if it is
    - Check if title exists
        - Return 404 if not found
    - Verify title in URL and in definition
        - Return 409 if mismatched
    - Return 200

    """
    validation = validate_definition(data)
    if validation:
        return validation

    is_subscription = check_if_subscription(title)
    if is_subscription:
        return is_subscription

    if not check_if_title_exists(title):
        return response(
            {'error': 'Not Found: The patch definition does not exist'}, 404)

    if title != data['id']:
        return response(
            {'error': f"Conflict: The software title ID '{title}' does not "
                      f"match the patch definition ID '{data['id']}'"},
            409
        )

    try:
        s3_bucket.put_object(
            Body=json.dumps(data),
            Key=f"{title}.json"
        )
    except ClientError as error:
        return response({'error': f'Internal Server Error: {error}'}, 500)

    return response(
        {'success': f"Successfully updated patch definition for '{title}'"},
        200
    )


def post_version(title, data):
    """
    - Validate JSON
        - Return 400 if invalid
    - Check if title is a subscription
        - Return 400 if it is
    - Check if title exists
        - Return 404 if not found
    - Check if version exists
        - Return 400 if it does
    - Return 201

    """
    validation = validate_definition(data, use_version=True)
    if validation:
        return validation

    is_subscription = check_if_subscription(title)
    if is_subscription:
        return is_subscription

    if not check_if_title_exists(title):
        return response(
            {'error': 'Not Found: The patch definition does not exist'}, 404)

    global tempdir
    tempdir = tempfile.mkdtemp()
    key = f'{title}.json'

    try:
        path = os.path.join(tempdir, key)
        s3_bucket.download_file(key, path)
    except ClientError:
        return response(
            {'error': f'Internal Server Error: '
                      f'Unable to load data for: {key}'},
            500
        )

    with open(os.path.join(path), 'r') as f_obj:
        patch_definition = json.load(f_obj)

    if data['version'] in [i['version'] for i in patch_definition['patches']]:
        return response(
            {'error': f"Bad Request: The version '{data['version']}' already "
                      f"exists in the patch definition"},
            409
        )

    patch_definition['patches'].insert(0, data)
    patch_definition['lastModified'] = \
        datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    patch_definition['currentVersion'] = data['version']

    try:
        s3_bucket.put_object(Body=json.dumps(patch_definition), Key=key)
    except ClientError as error:
        return response({'error': f'Internal Server Error: {error}'}, 500)

    return response(
        {'success': f"Successfully updated the version for patch definition "
                    f"'{title}'"},
        201
    )


def lambda_handler(event, context):
    resource = event['resource']
    parameter = event['pathParameters']
    method = event['httpMethod']

    if not event['body'] or \
            not event['headers'].get('Content-Type') == 'application/json':
        return response({'error': 'JSON payload required'}, 400)

    body = json.loads(event['body'])

    if resource == '/api/title' and method == 'POST':
        print('HTTP request for a new definition POST started!')
        return post_definition(body)

    elif resource == '/api/title/{title}' and method == 'PUT' and parameter:
        print('HTTP request for a definition PUT started!')
        return put_definition(parameter['title'], body)

    elif resource == '/api/title/{title}/version' and \
            method == 'POST' and parameter:
        print('HTTP request for a version POST started!')
        return post_version(parameter['title'], body)

    else:
        return response({'error': f"Bad Request: {event['path']}"}, 400)
