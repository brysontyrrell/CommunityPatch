import os

import requests

CLIENT_ID = os.getenv("CLIENT_ID")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")

session = requests.Session()


def lambda_handler(event, context):
    response = session.post(
        url=f"https://auth.{DOMAIN_NAME}/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "redirect_uri": f"https://contributors.{DOMAIN_NAME}/oauth2/appleid/token",
            "code": event["queryStringParameters"]["code"],
        },
    )

    return {
        "isBase64Encoded": False,
        "statusCode": response.status_code,
        "body": response.text,
        "headers": {"Content-Type": "application/json"},
    }
