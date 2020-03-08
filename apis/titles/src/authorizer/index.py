import logging
import os

import boto3
import jwt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DOMAIN_NAME = os.getenv("DOMAIN_NAME")

communitypatchtable = boto3.resource("dynamodb").Table(
    os.getenv("COMMUNITY_PATCH_TABLE")
)


def lambda_handler(event, context):
    """Details on errors must never be provided back to the authenticating client."""
    token = event["authorizationToken"]
    unverified_claims = jwt.decode(token, verify=False)

    try:
        token_entry = token_lookup(unverified_claims["sub"], unverified_claims["jti"])
        jwt.decode(
            token,
            token_entry["token_secret"],
            issuer=f"https://contributors.{DOMAIN_NAME}",
            audience=f"https://api.{DOMAIN_NAME}",
            algorithms=["HS256"],
        )
    except:
        logger.exception("Token verification failed")
        raise Exception("Unauthorized")

    return generate_policy(token, "Allow", event["methodArn"], unverified_claims)


def token_lookup(contributor_id, token_id):
    response = communitypatchtable.get_item(
        Key={"contributor_id": contributor_id, "type": f"TOKEN#{token_id}"}
    )
    return response["Item"]


def generate_policy(principal_id, effect=None, resource=None, context=None):
    auth_response = {"principalId": principal_id}

    if effect and resource:
        auth_response["policyDocument"] = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": "/".join(resource.split("/")[:2] + ["*"]),
                }
            ],
        }

    if context:
        # Context path in API event becomes "event['requestContext']['authorizer']"
        auth_response["context"] = dict()
        for k, v in context.items():
            auth_response["context"][k] = str(v)

    logger.info(auth_response)
    return auth_response
