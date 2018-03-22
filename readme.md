# CommunityPatch.com

The source code for www.communitypatch.com - a free, community managed 'external patch source' for Jamf Pro.

## Ideas



## ToDo List

- CloudWatch Metrics
- AWS Xray
- SNS Topics for bounce/complaint/delivery
    - Lambdas for processing
    - Auto-delete new definition on bounce-back/complaint
- Remove token generation from rest_api_new.py and create a separate Lambda service to handle token creation asyncronously and can then be shared by the reset feature
