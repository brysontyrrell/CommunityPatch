import json
import logging
import os
import time

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

METRICS_NAMESPACE = os.getenv('METRICS_NAMESPACE')

cloudwatch_client = boto3.client('cloudwatch')
sqs_queue = boto3.resource('sqs').Queue(os.getenv('METRICS_QUEUE_URL'))


def get_messages():
    return sqs_queue.receive_messages(
        AttributeNames=['All'],
        MaxNumberOfMessages=10,
    )


def process_metrics(metric_list):
    """Produces a dictionary of aggregated counts for collected metrics:

    {
        'JamfEndpoints': [
            {
                'value': '/jamf/v1/software',
                'metric': 'VisitCount',
                'metric_value': 1
            }
        ],
        'SoftwareTitles': [
            {
                'value': 'AdobeAir_Bryson',
                'metric': 'ReadCount',
                'metric_value': 1
            },
            {
                'value': 'CiscoAnyConnectSecureMobilityClient_macmacintosh',
                'metric': 'ReadCount',
                'metric_value': 1
            }
        ]
    }
    """
    metric_data = dict()

    for metric in metric_list:
        if metric['name'] not in metric_data.keys():
            metric_data[metric['name']] = list()

        current_metric = metric_data[metric['name']]

        if metric['value'] not in [i['value'] for i in current_metric]:
            current_metric.append(
                {
                    'value': metric['value'],
                    'metric': metric['metric'],
                    'metric_value': 1
                }
            )
        else:
            for item in current_metric:
                if item['value'] == metric['value']:
                    item['metric_value'] += 1

    logger.info(f'Metric Data: {metric_data}')
    send_metrics(metric_data)


def send_metrics(metric_data):
    for key in metric_data.keys():
        logger.info(f"Sending metric data for '{key}' to CloudWatch")
        for metric in metric_data[key]:
            cloudwatch_client.put_metric_data(
                MetricData=[
                    {
                        'MetricName': metric['metric'],
                        'Dimensions': [
                            {
                                'Name': key,
                                'Value': metric['value']
                            }
                        ],
                        'Unit': 'None',
                        'Value': metric['metric_value']
                    },
                ],
                Namespace=METRICS_NAMESPACE
            )


def start_poll(context, message_list=None, polling_start=None):
    if not polling_start:
        polling_start = time.time()

    if not message_list:
        message_list = list()

    stop_poll = False

    sqs_messages = get_messages()

    if not sqs_messages:
        process_metrics(message_list)
        return

    messages_to_delete = list()

    for message in sqs_messages:
        if float(message.attributes['SentTimestamp']) / 1000 < polling_start:
            message_list.append(json.loads(message.body))
            messages_to_delete.append(message)
        else:
            logger.info('Message timestamp is past the polling start time.')
            stop_poll = True

    sqs_queue.delete_messages(
        Entries=[
            {'Id': message.message_id, 'ReceiptHandle': message.receipt_handle}
            for message in messages_to_delete
        ]
    )

    if stop_poll:
        logger.info('Polling stopped.')
        return

    if context.get_remaining_time_in_millis() > 1000:
        start_poll(context, message_list, polling_start)
    else:
        logger.error('Max execution time reached. Polling stopped before all '
                     'eligible messages have been processed!')


def lambda_handler(event, context):
    start_poll(context)
    return {}
