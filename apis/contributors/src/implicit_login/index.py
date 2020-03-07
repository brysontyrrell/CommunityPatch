import os

CLIENT_ID = os.getenv("CLIENT_ID")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")


def lambda_handler(event, context):
    """Redirect for an Implicit auth flow."""
    return {
        "isBase64Encoded": False,
        "statusCode": 301,
        "headers": {
            "Location": f"https://auth.{DOMAIN_NAME}/login?response_type=token&client_id={CLIENT_ID}&redirect_uri=https://{DOMAIN_NAME}"
        },
    }
