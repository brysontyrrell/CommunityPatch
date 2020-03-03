import json

import boto3
import requests

client = boto3.client("dynamodb")


def lambda_handler(event, context):
    stream_arn = ""

    if event["RequestType"] != "Delete":
        try:
            table_name = event["ResourceProperties"]["TableName"]
            response = client.describe_table(TableName=table_name)
            stream_arn = response["Table"]["LatestStreamArn"]
        except Exception as error:
            cfnresponse(
                event,
                context,
                "FAILED",
                {"Error": type(error).__name__, "Message": str(error)},
            )

    cfnresponse(event, context, "SUCCESS", {"Arn": stream_arn})


def cfnresponse(
    event,
    context,
    response_status,
    response_data,
    physical_resource_id=None,
    no_echo=False,
):
    request_body = json.dumps(
        {
            "Status": response_status,
            "Reason": f"See the details in CloudWatch Log Stream: {context.log_stream_name}",
            "PhysicalResourceId": physical_resource_id or context.log_stream_name,
            "StackId": event["StackId"],
            "RequestId": event["RequestId"],
            "LogicalResourceId": event["LogicalResourceId"],
            "NoEcho": no_echo,
            "Data": response_data,
        }
    )

    print(f"Request URL:\n{event['ResponseURL']}")
    print(f"Request body:\n{request_body}")

    try:
        response = requests.put(
            event["ResponseURL"],
            data=request_body,
            headers={"content-type": "", "content-length": str(len(request_body))},
        )
        print(f"Request result: {response.status_code} {response.reason}")
        response.raise_for_status()
    except Exception as e:
        print("send(..) failed executing requests.put(..): " + str(e))
