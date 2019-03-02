import logging
import os
import sys

# Add '/opt' to the PATH for Lambda Layers
sys.path.append('/opt')

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError

from opossum import api
from opossum.exc import APIBadRequest, APINotFound

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

TITLES_BUCKET = os.getenv('TITLES_BUCKET')
TITLES_TABLE = os.getenv('TITLES_TABLE')

dynamodb = boto3.resource('dynamodb')


def read_table_entry(contributor_id, title_id):
    titles_table = dynamodb.Table(TITLES_TABLE)

    try:
        resp = titles_table.get_item(
            Key={
                'contributor_id': contributor_id,
                'title_id': title_id
            }
        )
    except ClientError:
        logger.exception('Unable to read title entry from DynamoDB!')
        raise

    return resp.get('Item')


def delete_table_entry(contributor_id, title_id):
    titles_table = dynamodb.Table(TITLES_TABLE)

    try:
        titles_table.delete_item(
            Key={
                'contributor_id': contributor_id,
                'title_id': title_id
            }
        )
    except ClientError:
        logger.exception('Unable to delete title entry from DynamoDB!')
        raise


def delete_definition_from_s3(contributor_id, title_id):
    client = boto3.client('s3')
    s3_key = os.path.join('titles', contributor_id, title_id)

    try:
        client.delete_object(
            Bucket=TITLES_BUCKET,
            Key=s3_key,
        )
    except ClientError:
        logger.exception(f"Unable to delete the file {s3_key}")
        raise


@api.handler
def lambda_handler(event, context):
    parameters = event['pathParameters']
    title_id = parameters['title']

    try:
        contributor_id = event['requestContext']['authorizer']['sub']
    except KeyError:
        logger.error('Token data not found!')
        raise APIBadRequest('Bad Request')

    entry = read_table_entry(contributor_id, title_id)

    if not entry:
        raise APINotFound(f"The title '{title_id}' was not found")

    delete_table_entry(contributor_id, title_id)
    delete_definition_from_s3(contributor_id, title_id)

    return f"Title '{title_id}' has been deleted", 200
