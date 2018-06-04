import json
import logging
import os

# from aws_xray_sdk.core import xray_recorder
# from aws_xray_sdk.core import patch
import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# xray_recorder.configure(service='CommunityPatch')
# patch(['boto3'])

TITLES_TABLE = os.getenv('TITLES_TABLE')

dynamodb = boto3.resource('dynamodb')


def response(message, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param message: Message for JSON body of response
    :type message: str or dict or list

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


def list_software_titles(contributor_id):
    titles_table = dynamodb.Table(TITLES_TABLE)

    try:
        resp = titles_table.query(
            KeyConditionExpression=
            Key('contributor_id').eq(contributor_id),
            ProjectionExpression='summary'
        )
    except ClientError:
        logger.exception('Unable to read title entry from DynamoDB!')
        raise

    return response([i['summary'] for i in resp['Items']], 200)


def list_select_software_titles(contributor_id, path_parameter):
    titles = path_parameter.split(',')

    def get_title(title_id):
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
            return None

        if resp.get('Item'):
            return resp['Item']['summary']
        else:
            return None

    title_list = list()

    for title in titles:
        result = get_title(title)
        if result:
            title_list.append(result)

    return response(title_list, 200)


def lambda_handler(event, context):
    logger.info(event)
    resource = event['resource']
    parameters = event['pathParameters']

    if resource == '/jamf/v1/{contributor}/software':
        return list_software_titles(parameters['contributor'])

    elif resource == '/jamf/v1/{contributor}/software/{titles}':
        return list_select_software_titles(
            parameters['contributor'],
            parameters['titles']
        )

    else:
        return response('Not Found', 404)
