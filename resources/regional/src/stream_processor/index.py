from datetime import datetime
import json
import os

import boto3

EVENT_BUS = f"{os.getenv('NAMESPACE')}-communitypatch"

events_client = boto3.client("events")


def lambda_handler(event, context):
    events_to_put = []

    for record in event["Records"]:
        print(f"Event: {record['eventName']}/{record['eventID']}")
        table_arn, _ = record["eventSourceARN"].split("/stream")
        events_to_put.append(
            {
                "Time": datetime.utcnow(),
                "Source": "communitypatch.table",
                "Resources": [table_arn],
                "DetailType": "Table Change",
                "Detail": json.dumps(record),
                "EventBusName": EVENT_BUS,
            }
        )

    if events_to_put:
        print(f"Publishing {len(events_to_put)} events to {EVENT_BUS}")
        events_client.put_events(Entries=events_to_put)

    return "ok"
