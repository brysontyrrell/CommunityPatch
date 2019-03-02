import logging
from operator import itemgetter
import os
import sys

# Add '/opt' to the PATH for Lambda Layers
sys.path.append('/opt')

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from opossum import api, dydb

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

CONTRIBUTORS_TABLE = os.getenv('CONTRIBUTORS_TABLE')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')
TITLES_TABLE = os.getenv('TITLES_TABLE')

dynamodb = boto3.resource('dynamodb')


def get_title_count(contributor_id):
    titles_table = dynamodb.Table(TITLES_TABLE)

    try:
        resp = titles_table.query(
            KeyConditionExpression=
            Key('contributor_id').eq(contributor_id),
            Select='COUNT'
        )
    except ClientError:
        logger.exception('Unable to read title entry from DynamoDB!')
        raise

    return resp['Count']


@api.handler
def lambda_handler(event, context):
    """Order of operations:

    1. Get all contributors
    2. Query for title counts for each
    3. Return JSON array
    """
    results = list()

    for contributor in dydb.scan_table(CONTRIBUTORS_TABLE):
        title_count = get_title_count(contributor['id'])
        uri = '/'.join(['jamf/v1', contributor['id'], 'software'])
        results.append(
            {
                'id': contributor['id'],
                'display_name': contributor['display_name'],
                'title_count': title_count,
                'urn': uri,
                'url': f'https://{DOMAIN_NAME}/{uri}'
            }
        )

    return sorted(results, key=itemgetter('title_count'), reverse=True), 200
