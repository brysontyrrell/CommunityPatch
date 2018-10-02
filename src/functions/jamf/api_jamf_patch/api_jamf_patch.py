import io
import json
import logging
import os

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError

from opossum import api
from opossum.exc import APINotFound

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

DOMAIN_NAME = os.getenv('DOMAIN_NAME')

s3_bucket = boto3.resource('s3').Bucket(os.getenv('TITLES_BUCKET'))


def read_definition_from_s3(contributor_id, title_id):
    f_obj = io.BytesIO()
    try:
        s3_bucket.download_fileobj(
            Key=os.path.join('titles', contributor_id, title_id),
            Fileobj=f_obj
        )
    except ClientError:
        logger.exception('Unable to read title JSON from S3')
        raise

    return json.loads(f_obj.getvalue())


@api.handler
def lambda_handler(event, context):
    parameters = event['pathParameters']

    contributor_id = parameters['contributor']
    title_id = parameters['title']

    # return redirect(contributor_id, title_id)
    try:
        definition = read_definition_from_s3(contributor_id, title_id)
    except ClientError:
        raise APINotFound('Not Found')

    return definition, 200
