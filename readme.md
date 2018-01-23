# Stupid Simple Patch Server

A serverless Patch Server for Jamf Pro using AWS.

## Prerequisites

You will need the AWS command line utility to deploy a copy of this application to your AWS account. You can get instructions for installing the [awscli here](https://docs.aws.amazon.com/cli/latest/userguide/installing.html).

Your AWS account will require permissions for creating resources in your AWS account including:

- API Gateway
- Lambda Functions
- S3 Buckets
- IAM Roles/Permissions

You will need a pre-existing S3 bucket for the deployment step described below.

## Deploy the Patch Server

Clone this repo to your computer and go to it in your `Terminal`.

```bash
$ cd /path/to/StupidSimplePatchServer
```

Using the AWS CLI, package the application for `CloudFormation`:

```bash
$ aws cloudformation package --template-file template.yaml --s3-bucket <Your-S3-Bucket> --output-template-file deployment.yaml
```

Use the created `deployment.yaml` file to create the application in `CloudFormation` (you can change the `--stack-name` value to whatever you prefer):

```bash
$ aws cloudformation --template-file deployment.yaml --stack-name ssps --capabilities CAPABILITY_IAM
```

You should see the following output on your screen:

```bash
Waiting for changeset to be created..
Waiting for stack create/update to complete
Successfully created/updated stack - ssps
```

## Access Your Patch Server

Once complete, go to the `AWS Console` in your browser and go to the `CloudFormation` page (be sure you are in the correct region).

You should see in the list the stack name used in the `deploy` command. Select it and click on the `Resources` tab. This will show you all of the resources that were created for the application.

To get the URL for your Patch Server, go to the `API Gateway` page in the `AWS Console`.

Select the Patch Server (it will have the same name as the stack), go to `Stages` in the sidebar, and click on `Prod`. You should see a URL string similar to this:

**https://<ID-STRING>.execute-api.<REGION>.amazonaws.com/Prod**

The following endpoints are exposed for this service for your Jamf Pro server to view and subscribe avaialable patch titles:

- `/software`: Lists all available patch titles that are hosted on your Patch Server. They will be returned in the following JSON format:

```json
{
  "TitleName1": {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName1"
  },
  "TitleName2": {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName2"
  },
  "TitleName3": {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName3"
  }
}
```

- `/software/TitleName1,TitleName2`: Returns a subset of patch titles. The titles must have their IDs passed in a commma separated string as shown. The returned data is the same as the `/sofware` endpoint.

```json
{
  "TitleName1": {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName1"
  },
  "TitleName2": {
    "name": "string",
    "publisher": "string",
    "lastMondified": "ISO date string",
    "currentVersion": "string",
    "id": "TitleName2"
  }
}
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
