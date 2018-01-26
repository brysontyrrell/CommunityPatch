About Patch Endpoints
=====================

All about the patch endpoints that deliver the patch definitions to Jamf Pro.

The following endpoints are exposed for this service for your Jamf Pro server to view and subscribe avaialable patch titles:

* `/software`: Lists all available patch titles that are hosted on your Patch Server. They will be returned in the following JSON format:

.. code-block:: json

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

* `/software/TitleName1,TitleName2`: Returns a subset of patch titles. The titles must have their IDs passed in a commma separated string as shown. The returned data is the same as the `/sofware` endpoint.

.. code-block:: json

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

* `/patch/TitleName`: Returns the full JSON patch definition for the provided patch title ID (see Jamf's documentation for more details on the patch title schema).

.. code-block:: json

    {
        "name": "string",
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

Each endpoint's full URL would be entered into your browser as::

    https://`<API-GATEWAY-ID>`.execute-api.`<REGION>`.amazonaws.com/Prod/software
    https://`<API-GATEWAY-ID>`.execute-api.`<REGION>`.amazonaws.com/Prod/software/TitleName1,TitleName2
    https://`<API-GATEWAY-ID>`.execute-api.`<REGION>`.amazonaws.com/Prod/patch/TitleName
