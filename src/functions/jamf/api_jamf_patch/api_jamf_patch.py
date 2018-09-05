import io
import json
import logging
import os
from urllib.parse import urlunparse

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

DOMAIN_NAME = os.getenv('DOMAIN_NAME')

s3_bucket = boto3.resource('s3').Bucket(os.getenv('TITLES_BUCKET'))


def response(message, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param message: Message for JSON body of response
    :type message: str or dict

    :param int status_code: HTTP status code of response

    :rtype: dict
    """
    if isinstance(message, str):
        message = {'message': message}

    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def redirect(contributor_id, title_id):
    """Returns a response for API Gateway that redirects to the CloudFront
    location of a patch definition's JSON file.

    :param str contributor_id: The contributor ID
    :param str title_id: The title ID

    :rtype: dict
    """
    def redirect_url():
        return urlunparse(
            (
                'http',
                DOMAIN_NAME,
                os.path.join('titles', contributor_id, title_id),
                None,
                None,
                None
            )
        )

    return {
        'isBase64Encoded': False,
        'statusCode': 301,
        'body': '',
        'headers': {'Location': redirect_url()}
    }


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


def lambda_handler(event, context):
    parameters = event['pathParameters']

    contributor_id = parameters['contributor']
    title_id = parameters['title']

    # return redirect(contributor_id, title_id)
    try:
        definition = read_definition_from_s3(contributor_id, title_id)
    except ClientError:
        return response('Not Found', 404)

    return response(definition, 200)
