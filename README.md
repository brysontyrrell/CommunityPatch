# CommunityPatch

CommunityPatch is a free, open-source, external patch source for Jamf Pro administrators to publish patch definitions they maintain for the broader Jamf community to subscribe to. Access CommunityPatch using an Apple ID, and then create and manage API tokens to interact with the service API.

## Jamf Pro Setup

Anyone can subscribed to a contributor's patch titles in Jamf Pro - they are publicly available feeds. All that is required is their `Contributor ID` or their `Contributor Alias`.

See the [Jamf Pro Setup documentation](docs/JamfProSetup.md) for more details.

## Searching Titles

WIP

## Contributor QuickStart Guide

### Obtain an Access Token

Sign into CommunityPatch using an Apple ID by navigating to https://contributors.communitypatch.dev/login and authenticating (you may use any Apple ID you wish as a part of this process).

At this time, CommunityPatch does not have a web UI. There is a landing page at the root domain that will render the generated `Access Token` for you to copy.

### Create API Tokens

Your `Access Token` grants access to the Contributors API. This API allows you to manage your profile and `API Tokens`. API tokens can be created for use in scripting or other automation with CommunityPatch. These tokens can be configured with an expiration of up to 1 year, scoped to all or an individual title ID, 

See the [Contributors API documentation](docs/ContributorsAPI.md) for more details.

### Manage Titles

Once you have created an API token it can be used to create and manage patch title definitions on the Titles API. 

See the [Titles API documentation](docs/TitlesAPI.md) for more details.
