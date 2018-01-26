Deploy on AWS
=============

How to deploy the patch server in your AWS account.

Prerequisites
-------------

You will need the AWS command line utility to deploy a copy of this application to your AWS account. You can get instructions for [installing the awscli here](https://docs.aws.amazon.com/cli/latest/userguide/installing.html).

Your AWS `IAM User` will require permissions for creating resources in your AWS account including:

* API Gateway
* Lambda Functions
* S3 Buckets
* IAM Roles/Permissions

Here is an example `IAM Policy` you can use for your `IAM User`:

.. code-block:: json

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
                    "dynamodb:CreateTable",
                    "dynamodb:DeleteTable",
                    "dynamodb:DescribeTable",
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

Deploy the Patch Server
-----------------------

Clone this repo to your computer and go to it in your `Terminal`.

.. code-block:: bash

    $ cd /path/to/StupidSimplePatchServer

Using the AWS CLI, package the application for `CloudFormation`:

.. code-block:: bash

    $ aws cloudformation package --template-file template.yaml --s3-bucket <Your-S3-Bucket> --output-template-file deployment.yaml


.. note::

    If the S3 bucket specified for `aws cloudformation package` does not exist, you can create it from the CLI with the following command: `aws s3 mb s3://<Your-S3-Bucket>`

Use the created `deployment.yaml` file to create the application in `CloudFormation` (you can change the `--stack-name` value to whatever you prefer):

.. code-block:: bash

    $ aws cloudformation deploy --template-file deployment.yaml --stack-name ssps --capabilities CAPABILITY_IAM

You should see the following output on your screen::

    Waiting for changeset to be created..
    Waiting for stack create/update to complete
    Successfully created/updated stack - ssps


Access Your Patch Server
------------------------

Once complete, go to the `AWS Console` in your browser and go to the `CloudFormation` page (be sure you are in the correct region).

You should see in the list the stack name used in the `deploy` command. Select it and click on the `Resources` tab. This will show you all of the resources that were created for the application.

To get the URL for your Patch Server, go to the `API Gateway` page in the `AWS Console`.

Select the Patch Server (it will have the same name as the stack), go to `Stages` in the sidebar, and click on `Prod`. You should see a URL string similar to this::

    **https://`<API-GATEWAY-ID>`.execute-api.`<REGION>`.amazonaws.com/Prod**

About AWS Costs
---------------

This application is created and deployed within your AWS account. While you are responsible for the costs of running the service, it is highly likely that this will fall within AWS's Free Tier.

Refer to AWS's pricing guides for more information:

* API Gateway: https://aws.amazon.com/api-gateway/pricing
* Lambda: https://aws.amazon.com/lambda/pricing
* S3: https://aws.amazon.com/s3/pricing
* DynamoDB: https://aws.amazon.com/dynamodb/pricing
