import hashlib
import io
import json
import logging
import os
import time

import boto3
from boto3.dynamodb import conditions
from botocore.exceptions import ClientError
from jsonschema import validate, ValidationError
import requests

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


with open('schema_full_definition.json', 'r') as f_obj:
    definition_schema = json.load(f_obj)


def scan_table():
    results = dynamodb.scan(
        FilterExpression=conditions.Attr('is_synced').eq(True)
    )
    while True:
        for row in results['Items']:
            yield row
        if results.get('LastEvaluatedKey'):
            results = dynamodb.scan(
                ExclusiveStartKey=results['LastEvaluatedKey'],
                FilterExpression=conditions.Attr('is_synced').eq(True)
            )
        else:
            break


def definition_from_url(title_utl):
    logger.info('Loading definition from URL')

    resp = requests.get(
        title_utl,
        headers={'Accept': 'application/json'},
        timeout=3
    )

    try:
        resp.raise_for_status()
    except requests.HTTPError as error:
        logger.error(
            f'An error occurred attempting to read the definition URL: {error}')
        return None

    try:
        patch_definition = resp.json()
    except json.JSONDecodeError:
        logger.error(
            f'The definition URL did not return JSON content {title_utl}')
        return None

    try:
        validate(patch_definition, definition_schema)
    except ValidationError as error:
        logger.error(
            f'The downloaded software title JSON failed validation: {error}')
        send_metric('RestApi', 'TitleSchemaValidation', 'FailedCount')
        return None

    return patch_definition


def get_definition_from_s3(title):
    f_obj = io.BytesIO()
    s3_bucket.download_fileobj(title, f_obj)
    data = json.loads(f_obj.getvalue())
    return data


def compare_json_hashes(a, b):
    if hashlib.sha256(json.dumps(a).encode()).digest() == \
            hashlib.sha256(json.dumps(b).encode()).digest():
        return True
    else:
        return False


def lambda_handler(event, context):
    synced_titles = scan_table()

    for title in synced_titles:
        logger.info(title)
        title_url = title.get('sync_url')
        if title_url:
            source_definition = definition_from_url(title_url)

            if not source_definition:
                logger.error(f"The sync failed for URL '{title_url}'")
                send_metric('DefinitionSync', 'DefinitionFromUrl', 'FailedCount')
                # Update sync status for definition as failed
                continue
        else:
            logger.error(f"The title '{title['id']}' does not have a sync url")
            # Update sync status for definition as failed
            continue

        source_definition['id'] = \
            f"{source_definition['id']}_" \
            f"{title['author_name'].replace(' ', '_')}"
        source_definition['name'] = \
            f"{source_definition['name']} ({title['author_name']})"

        try:
            stored_definition = get_definition_from_s3(title['id'])
        except ClientError:
            logger.error("Unable to load title definition from S3: "
                         f"{title['id']}")
            # Update sync status for definition as failed
            continue

        if not compare_json_hashes(source_definition, stored_definition):
            logger.info('Definition hashes do not match: updating S3')
            # Store new definition content to S3
            # Write changes to currentVersion, lastModified to DynamoDB
            send_metric('DefinitionSync', 'DefinitionUpdated', 'UpdateCount')
        else:
            logger.info('Definition hashes match: no updates')

    return {}
