REST API
========

How to programmatically manage your patch definitions on your patch server.

.. note::

    **JSON Schema Validation:**

    All API endpoints use JSON schema validation to ensure the submitted JSON is valid for patch definitions and versions. Invalid definitions can cause issues with Jamf Pro when it retrieves data from an external patch source. The API will provide feedback on where a validation error occurred to assist you in troubleshooting your definitions. Because the API performs this validation, it is considered a safer method to loading your patch definitions than manually uploading the files to S3.

POST ``/api/title``
-------------------

Create a new patch definition for a software title on the Patch Server. The new patch title name will be taken from the ``id`` of the submitted definition.

Request::

    POST https://<patch-server-url>/api/title
    Content-Type: application/json
    Body: {"<Patch-Definition-JSON"}

Successful response::

    Status Code: 201
    Content-Type: application/json
    Body: {"success": "Successfully created patch definition for '<patch-title-name>'"}

PUT ``/api/title/<patch-title-name>``
-------------------------------------

Replace an existing patch definition for a software title on the Patch Server that is not a subscription. This action does not perform any logic for merging changes between the current and submitted patch definitions.

Request::

    POST https://<patch-server-url>/api/title/<patch-title-name>
    Content-Type: application/json
    Body: {"<Patch-Definition-JSON"}

Successful response::

    Status Code: 200
    Content-Type: application/json
    Body: {"success": "Successfully updated the patch definition for '<patch-title-name>'"}

POST ``/api/title/<patch-title-name>/version``
----------------------------------------------

Add a new patch version to an existing patch definition that is not a subscription. The ``lastModified`` and ``version`` values of the patch definition will be updated as a part of this operation.

Request::

    POST https://<patch-server-url>/api/title/<patch-title-name>/version
    Content-Type: application/json
    Body: {"<Patch-Definition-JSON"}

Successful response::

    Status Code: 201
    Content-Type: application/json
    Body: {"success": "Successfully updated the version for patch definition '<patch-title-name>'"}
