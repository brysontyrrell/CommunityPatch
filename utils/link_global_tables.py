#!/usr/bin/env python3

import argparse

import boto3

REGIONS = ("us-east-2", "eu-central-1", "ap-southeast-2")

parser = argparse.ArgumentParser()
parser.add_argument("profile")
parser.add_argument("table")
args = parser.parse_args()

session = boto3.Session(region_name="us-east-2", profile_name=args.profile)
dydb_client = session.client("dynamodb")

print(f"Creating Global DynamoDB Table: {args.table}")
dydb_client.create_global_table(
    GlobalTableName=args.table, ReplicationGroup=[{"RegionName": v} for v in REGIONS]
)
