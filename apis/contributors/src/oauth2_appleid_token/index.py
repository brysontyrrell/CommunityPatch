import os

import requests

CLIENT_ID = os.getenv("CLIENT_ID")
DOMAIN_NAME = os.getenv('DOMAIN_NAME')


def lambda_handler(event, context):
    response = requests.post(
        url=f"https://auth.{DOMAIN_NAME}/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "redirect_uri": f"https://contrinbutors.{DOMAIN_NAME}/oauth2/appleid/token",
            "code": event["queryStringParameters"]["code"]
        }
    )

    return response.json()
