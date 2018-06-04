import json
import logging
import os
from urllib.parse import urlunparse

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

DOMAIN_NAME = os.getenv('DOMAIN_NAME')


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
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

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
        'statusCode': 302,
        'body': '',
        'headers': {'Location': redirect_url()}
    }


def lambda_handler(event, context):
    parameters = event['pathParameters']

    contributor_id = parameters['contributor']
    title_id = parameters['title']

    return redirect(contributor_id, title_id)
