import os

import boto3

ses_client = boto3.client(os.getenv('EMAIL_QUEUE_URL'))
sqs_queue = boto3.resource('sqs').Queue(os.getenv('EMAIL_QUEUE_URL'))


def lambda_handler(event, context):
    return {}
