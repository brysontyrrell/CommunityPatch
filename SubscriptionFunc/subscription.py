import json
import os

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError
import requests

dynamodb = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
s3_bucket = boto3.resource('s3').Bucket(os.environ['S3_BUCKET'])

with open('schema_full_definition.json', 'r') as f_obj:
    definition_schema = json.load(f_obj)


def response(message, status_code):
    print(message)
    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def get_subscription_json(url):
    resp = requests.get(url, headers={'Accept': 'application/json'}, timeout=3)

    try:
        resp.raise_for_status()
        resp.json()
    except requests.HTTPError as error:
        return response({'error': error}, 400)
    except json.JSONDecodeError:
        return response({'error': 'Bad Request: Subscription URL '
                                  'did not return JSON content'}, 400)

    try:
        validate(resp.json(), definition_schema)
    except ValidationError as error:
        return response(
            {'error': f"Validation Error on Subscription URL JSON: "
                      f"{error.message} for item: "
                      f"/{'/'.join([str(i) for i in error.path])}"},
            400
        )

    return resp


def subscription_request(subscription):
    resp = get_subscription_json(subscription['json_url'])
    if not isinstance(resp, requests.Response):
        return resp

    try:
        dynamodb.put_item(
            Item={
                'id': subscription['id'],
                'json_url': subscription['json_url']
            },
            ConditionExpression='attribute_not_exists(id)'
        )
    except ClientError as error:
        if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return response(
                {'error': f"Conflict: The software title ID "
                          f"'{subscription['id']}' already exists"},
                409
            )
        else:
            return response({'error': f'Internal Server Error: {error}'}, 500)

    try:
        s3_bucket.put_object(
            Body=resp.text.encode(),
            Key=f"{subscription['id']}.json"
        )
    except ClientError as error:
        return response({'error': f'Internal Server Error: {error}'}, 500)

    return  response(
        {'success': f"PatchServer has subscribed to title "
                    f"'{subscription['id']}' at {subscription['json_url']}"},
        201
    )


def new_subscription(event):
    if not event['headers'].get('Content-Type') == 'application/json':
        return response(
            {'error': "Unsupported Media Type: must be 'application/json'"},
            415
        )

    body = json.loads(event['body'])
    print(body)
    if not all(k in body for k in ('id', 'json_url')):
        return response(
            {'error': "Bad Request: 'id' and 'json_url' keys are required"},
            400
        )

    return subscription_request(body)


def delete_subscription(title):
    if not dynamodb.get_item(Key={'id': title}).get('Item'):
        return response(
            {'error': f"Not Found: '{title}' is not "
                      f"a subscribed software title"},
            404
        )

    print(f"Deleting '{title}' from the database")
    dynamodb.delete_item(Key={'id': title})

    print(f"Deleting '{title}.json' from the S3 bucket")
    s3_bucket.delete_objects(
        Delete={
            'Objects': [{'Key': f'{title}.json'}]
        }
    )

    return response(
        {'success': f"PatchServer has unsubscribed from the title '{title}'"},
        200
    )


def sync_subscriptions():
    subscriptions = dynamodb.scan()
    for item in subscriptions['Items']:
        print(f"Downloading definition for '{item['id']}'")
        resp = get_subscription_json(item['json_url'])
        if not isinstance(resp, requests.Response):
            print(f"An error occured when downloading the definition for "
                  f"'{item['id']}'")
            continue

        print(f"Writing updated definition for '{item['id']}' to S3 bucket")
        try:
            s3_bucket.put_object(
                Body=resp.text.encode(),
                Key=f"{item['id']}.json"
            )
        except ClientError as error:
            print(f"Encountered an exception syncing '{item['id']}': {error}")
            raise


def lambda_handler(event, context):
    if event.get('source') and event.get('detail-type') == 'Scheduled Event':
        print('Scheduled subscription sync started!')
        sync_subscriptions()
    else:
        resource = event['resource']
        parameter = event['pathParameters']

        print(resource, parameter, event)

        if resource == '/subscribe':
            print('HTTP request for new subscription started!')
            return new_subscription(event)
        elif resource == '/unsubscribe/{title}' and parameter:
            print('HTTP request for an unsubscribe started!')
            return delete_subscription(parameter['title'])
        else:
            return response({'error': f"Bad Request: {event['path']}"}, 400)
