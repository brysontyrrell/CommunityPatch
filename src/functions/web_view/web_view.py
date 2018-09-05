import logging
import os

import boto3
import jinja2

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONTRIBUTORS_TABLE = os.getenv('CONTRIBUTORS_TABLE')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')
TITLES_TABLE = os.getenv('TITLES_TABLE')

dynamodb = boto3.resource('dynamodb')
function_dir = os.path.dirname(os.path.abspath(__file__))

jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(function_dir, 'templates')),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

template = jinja2_env.get_template('index.html')


def scan_contributors_table():
    contributors_table = dynamodb.Table(CONTRIBUTORS_TABLE)

    results = contributors_table.scan()
    while True:
        for row in results['Items']:
            yield row
        if results.get('LastEvaluatedKey'):
            results = dynamodb.scan(
                ExclusiveStartKey=results['LastEvaluatedKey'])
        else:
            break


def get_contributors():
    contributors = [
        {
            'id': i['id'],
            'name': i['display_name'],
            'url': '/'.join(['jamf/v1', i['id'], 'software?extend'])
        }
        for i in scan_contributors_table()
        if i['verified_account']
    ]

    return contributors


def lambda_handler(event, context):
    return template.render(
        contributors=get_contributors(), domain_name=DOMAIN_NAME)
