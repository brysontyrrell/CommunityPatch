import json
import logging
import os
import time

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SENDER_ADDRESS = os.getenv('SENDER_ADDRESS')

ses_client = boto3.client('ses', region_name='us-east-1')
sqs_queue = boto3.resource('sqs').Queue(os.getenv('METRICS_QUEUE_URL'))


def send_metric(name, value, metric):
    logger.info(f"Sending metric '{name}:{value}:{metric}' to queue")
    sqs_queue.send_message(
        MessageBody=json.dumps(
            {
                'name': name,
                'value': value,
                'metric': metric,
                'timestamp': time.time()
            }
        )
    )


def send_email(data):
    send_metric('EmailService', 'SentEmail', 'SentCount')
    return ses_client.send_email(
        Destination={
            'ToAddresses': [data['recipient_address']],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': 'UTF-8',
                    'Data': data['body_html'],
                },
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': data['body_text'],
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': 'Community Patch API Token',
            },
        },
        Source=f'Commuinity Patch <{SENDER_ADDRESS}>'
    )


def lambda_handler(event, context):
    """This function is meant to be triggered by an SNS event. The expceted
    JSON body of the SNS message should be formatted as:

    .. code-block: json

        {
            "recipient_address": "",
            "body_html": "",
            "body_text": ""
        }
    """
    if event.get('Records'):
        logging.info('Processing SNS records...')
        for record in event['Records']:
            data = json.loads(record['Sns']['Message'])
            send_email(data)

    else:
        logging.warning('No SNS records found in the event')

    return {}
