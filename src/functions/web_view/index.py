import logging
import os

from botocore.vendored import requests
import jinja2

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DOMAIN_NAME = os.getenv('DOMAIN_NAME')

session = requests.Session()
function_dir = os.path.dirname(os.path.abspath(__file__))

jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(function_dir, 'templates')),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

template = jinja2_env.get_template('index.html')


def get_contributors():
    resp = session.get(f'https://{DOMAIN_NAME}/api/v1/contributors')
    return resp.json()


def lambda_handler(event, context):
    return template.render(
        contributors=get_contributors(), domain_name=DOMAIN_NAME)
