# Contributors API

The Contributors API provides the abiltiy to manage your profile and API tokens.

### Quick Links

[Main Page](../../README.md) | [Jamf Pro Setup](../../docs/JamfProSetup.md) | [Titles API](../titles/TitlesAPI.md)

## Contributors

### GET /v1/contributors

Return a list of all contributors. `No Authentication`

#### Request

n/a

#### Response

n/a

## API Token Management

These endpoints require an `Access Token`. These tokens are obtained after signing in with an Apple ID (see the main page for more details).

### POST /v1/tokens

Create an API token.

#### Request

| JSON Key | Description | Allowed Values | Required/Optional |
|-----|-------------|----------------|-------------------|
| expires_in_days | Set an expiration for the API token in days. | Integer: 1-365 (365 is default if not provided) | Optional |
| titles_in_scope | Pass an array of existing Title IDs that the token will be allowed permissions to modify. If this value is set, the API token will be rejected for any Titles that are not a part of the scope. | Array of Strings: must be valid Title ID(s) for your Contributor ID. The default scope allows permissions to all Titles. | Optional

```
POST /v1/tokens
Authorization: <<Access Token>>
Content-Type: application-json
 
{
    "expires_in_days": 365
    "titles_in_scope": ["<<Title ID>>"]
}
```

#### Response

| JSON Key | Description |
|-----|-------------|
| id | The token's unique ID. |
| api_token | The API token.

```
201 Created
Content-Type: application/json

{
    "id": "8c118ac0-daeb-4710-ab68-54d8b73eb441",
    "api_token": "eyJ0eXQk3e-No6QQqAXCRkwaiLEOUQP1m-No6QQqAXCRkwai..."
}
```

#### POST /v1/tokens/{token_id}/invalidate


Invalidate an API token. This action will revoke the token's access to the CommunityPatch APIs. _**This action cannot be reversed!**_

#### Request

| Path Parameter | Description |
|-----|-------------|
| token_id | The API token ID that will be invalidated. |

```
POST /v1/tokens/{token_id}/invalidate
Authorization: <<Access Token>>
```

#### Response

```
204 No Content
```
