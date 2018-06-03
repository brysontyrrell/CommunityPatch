import json
import logging
from operator import itemgetter
import os
import time

# import boto3
import jinja2

logger = logging.getLogger()
logger.setLevel(logging.INFO)

function_dir = os.path.dirname(os.path.abspath(__file__))

jinja2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(function_dir, 'templates')),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

template = jinja2_env.get_template('index.html')


def lambda_handler(event, context):
    return template.render(titles=list())
