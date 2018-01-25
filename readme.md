# Stupid Simple Patch Server

A serverless Patch Server for Jamf Pro using AWS.

## Prerequisites

You will need the AWS command line utility to deploy a copy of this application to your AWS account. You can get instructions for [installing the awscli here](https://docs.aws.amazon.com/cli/latest/userguide/installing.html).

Your AWS `IAM User` will require permissions for creating resources in your AWS account including:

- API Gateway
- Lambda Functions
- S3 Buckets
- IAM Roles/Permissions

Here is an example `IAM Policy` you can use for your `IAM User`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "apigateway:DELETE",
                "apigateway:GET",
                "apigateway:PATCH",
                "apigateway:POST",
                "cloudformation:CreateChangeSet",
                "cloudformation:DescribeChangeSet",
                "cloudformation:DescribeStacks",
                "cloudformation:ExecuteChangeSet",
                "cloudformation:ListChangeSets",
                "iam:AttachRolePolicy",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:DeleteRolePolicy",
                "iam:DetachRolePolicy",
                "iam:GetRole",
                "iam:PassRole",
                "iam:PutRolePolicy",
                "lambda:AddPermission",
                "lambda:CreateFunction",
                "lambda:DeleteFunction",
                "lambda:GetFunctionConfiguration",
                "lambda:ListTags",
                "lambda:RemovePermission",
                "lambda:TagResource",
                "lambda:UntagResource",
                "lambda:UpdateFunctionCode",
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "*"
        }
    ]
}
```

## Deploy the Patch Server

Clone this repo to your computer and go to it in your `Terminal`.

```bash
$ cd /path/to/StupidSimplePatchServer
```

Using the AWS CLI, package the application for `CloudFormation`:

```bash
$ aws cloudformation package --template-file template.yaml --s3-bucket <Your-S3-Bucket> --output-template-file deployment.yaml
```

> If the S3 bucket specified for `aws cloudformation package` does not exist it will be created.

Use the created `deployment.yaml` file to create the application in `CloudFormation` (you can change the `--stack-name` value to whatever you prefer):

```bash
$ aws cloudformation deploy --template-file deployment.yaml --stack-name ssps --capabilities CAPABILITY_IAM
```

You should see the following output on your screen:

```bash
Waiting for changeset to be created..
Waiting for stack create/update to complete
Successfully created/updated stack - ssps
```

## Populate the S3 Bucket

To make patch titles available for your Patch Server, upload the JSON file of the full patch definition into the root of the S3 bucket created for the application.

**The JSON filename must match the ID of the patch.**

Examples taken from Jamf's official patch server would be saved to the S3 bucket as:

```
AdobeAcrobatProDC.json
Composer.json
GoogleChrome.json
JavaSEDevelopmentKit8.json
macOS.json
MicrosoftWord2016.json
```

To update your patch definitions, replace the existing file in S3 with the new, updated file.

## Access Your Patch Server

Once complete, go to the `AWS Console` in your browser and go to the `CloudFormation` page (be sure you are in the correct region).

You should see in the list the stack name used in the `deploy` command. Select it and click on the `Resources` tab. This will show you all of the resources that were created for the application.

To get the URL for your Patch Server, go to the `API Gateway` page in the `AWS Console`.

Select the Patch Server (it will have the same name as the stack), go to `Stages` in the sidebar, and click on `Prod`. You should see a URL string similar to this:

**https://`<API-GATEWAY-ID>`.execute-api.`<REGION>`.amazonaws.com/Prod**

The following endpoints are exposed for this service for your Jamf Pro server to view and subscribe avaialable patch titles:

- `/software`: Lists all available patch titles that are hosted on your Patch Server. They will be returned in the following JSON format:

```json
[
  {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName1"
  },
  {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName2"
  },
  {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName3"
  }
]
```

- `/software/TitleName1,TitleName2`: Returns a subset of patch titles. The titles must have their IDs passed in a commma separated string as shown. The returned data is the same as the `/sofware` endpoint.

```json
[
  {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName1"
  },
  {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName2"
  }
]
```

- `/patch/TitleName`: Returns the full JSON patch definition for the provided patch title ID (see Jamf's documentation for more details on the patch title schema).

```json
{
  "name": "TitleName",
  "publisher": "string",
  "appName": "string",
  "bundleId": "string",
  "lastModified": "ISO date string",
  "currentVersion": "string",
  "requirements": ["Array of Requirement Objects"],
  "patches": ["Array of Patch Objects"],
  "extensionAttributes": ["Array of Extension Attribute Objects"],
  "id": "TitleName"
}
```

Each endpoint's full URL would be entered into your browser as:

- https://`<API-GATEWAY-ID>`.execute-api.`<REGION>`.amazonaws.com/Prod/software
- https://`<API-GATEWAY-ID>`.execute-api.`<REGION>`.amazonaws.com/Prod/software/TitleName1,TitleName2
- https://`<API-GATEWAY-ID>`.execute-api.`<REGION>`.amazonaws.com/Prod/patch/TitleName

## Subscribe to the Patch Server in Jamf Pro (10.2+)

To add your Patch Server as a `Patch External Source` in Jamf Pro, go to:

**Settings > Computer Management > Patch Management**

- Click the `+ New` button next to `Patch External Source`.
- Give the Patch Server a name.
- Enter the URL without the schema (i.e. `https://`) in the `SERVER AND PORT` field (e.g. ```<API-GATEWAY-ID>.execute-api.<REGION>.amazonaws.com/Prod/```) and 443 for the `PORT`.
- Check the `Use SSL` box.

The Patch Server will now be available to subscribe to when adding new titles under `Patch Management`:

**Computers > Patch Management**

## About AWS Costs

This application is created and deployed within your AWS account. While you are responsible for the costs of running the service, it is highly likely that this will fall within AWS's Free Tier.

Refer to AWS's pricing guides for more information:

- API Gateway: https://aws.amazon.com/api-gateway/pricing
- Lambda: https://aws.amazon.com/lambda/pricing
- S3: https://aws.amazon.com/s3/pricing
- DynamoDB: https://aws.amazon.com/dynamodb/pricing
