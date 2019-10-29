from functools import lru_cache
import os

import boto3

AWS_REGION = os.getenv("AWS_REGION")
NAMESPACE = os.getenv("NAMESPACE")

SYNC_REGIONS = [
    r for r in ("us-east-2", "eu-central-1", "ap-southeast-2") if r != AWS_REGION
]


@lru_cache()
def titles_bucket(region):
    return boto3.resource("s3").Bucket(f"{NAMESPACE}-communitypatch-{region}-titles")


def lambda_handler(event, context):
    for record in event["Records"]:
        process_record(record)


def process_record(record):
    event_name = record["s3"]["eventName"]
    source_bucket = record["s3"]["bucket"]["name"]
    source_key = record["s3"]["object"]["key"]

    print(f"S3 Event: {event_name}: {source_bucket}/{source_key}")

    for region in SYNC_REGIONS:
        target_bucket = titles_bucket(region)
        if record["eventName"] in ("ObjectCreated:Put", "ObjectCreated:Post"):
            print(f"Copying to {region}: {source_key}")
            copy_source = {"Bucket": source_bucket, "Key": source_key}
            target_bucket.copy(CopySource=copy_source, Key=source_key)

        elif record["eventName"] in (
            "ObjectRemoved:Delete",
            "ObjectRemoved:DeleteMarkerCreated",
        ):
            print(f"Deleting {region}: {source_key}")
            target_bucket.delete_objects(Delete={"Objects": [{"Key": source_key}]})
