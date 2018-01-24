import json
import os

import boto3
from botocore.exceptions import ClientError
import requests

dynamodb = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
s3_bucket = boto3.resource('s3').Bucket(os.environ['S3_BUCKET'])


def response(message, status_code):
    print(message)
    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def initial_subscription_request(subscription):
    resp = requests.get(subscription['json_url'], headers={'Accept': 'application/json'})

    try:
        resp.raise_for_status()
        resp.json()
    except requests.HTTPError as error:
        return response({'error': error}, 400)
    except json.JSONDecodeError:
        return response({'error': f'Bad Request: URL did not return JSON content'}, 400)

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
            return response({'error': f"Conflict: The software title ID '{subscription['id']}' already exists"}, 409)
        else:
            return response({'error': f'Internal Server Error: {error}'}, 500)

    try:
        s3_bucket.put_object(Body=resp.text.encode(), Key=f"{subscription['id']}.json")
    except ClientError as error:
        return response({'error': f'Internal Server Error: {error}'}, 500)

    return  response(
        {'success': f"PatchServer has subscribed to title '{subscription['id']}' at {subscription['json_url']}"}, 201)


def lambda_handler(event, context):
    if not event['headers'].get('Content-Type') == 'application/json':
        return response({'error': "Unsupported Media Type: must be 'application/json'"}, 415)

    body = json.loads(event['body'])
    print(body)
    if not all(k in body for k in ('id', 'json_url')):
        return response({'error': "Bad Request: 'id' and 'json_url' keys are required"}, 400)

    return initial_subscription_request(body)
