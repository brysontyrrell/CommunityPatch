Patch Subscriptions API
=======================

How to subscribe to someone else's patch definition.

POST ``/subscriptions/subscribe``
---------------------------------

To subscribe to the URL of a patch definition, make a POST request to the ``/subscriptions/subscribe`` endpoint with a JSON payload containing the software title ID (``'id'``) and the URL to the JSON file (``'json_url'``)::

    POST https://api.communitypatch.com/subscriptions/subscribe
    Content-Type: application/json
    Body: {"id": "<patch-title-name>", "json_url": "<url-to-JSON-file>"}

Successful response::

    Status Code: 201
    Content-Type: application/json
    Body: {"success": ""PatchServer has subscribed to title '<patch-title-name>' at <url-to-JSON-file>"}

.. note::

    The Patch Server performs validations on all patch definitions it retrieves. If the validation fails, the subscription request will be rejected.

POST ``/subscriptions/unsubscribe/<patch-title-name>``
------------------------------------------------------

To unsubscribe from a patch definition, make a POST request to the ``/subscriptions/unsubscribe`` endpoint with the name of the software title::

    POST https://api.communitypatch.com/subscriptions/unsubscribe/<patch-title-name>

This will remove the patch definition from syncing and delete the patch definition file from the S3 bucket.

Successful response::

    Status Code: 200
    Content-Type: application/json
    Body: {"success": "PatchServer has unsubscribed from the title '<patch-title-name>'"}


Patch Definition Syncing
------------------------

Every five (5) minutes, the Patch Server will sync all subscribed patch definitions. It will download the source from the provided URL and write the definition into the S3 bucket, overwriting the last version of the patch definition.

.. note::

    The Patch Server will perform validation on the patch definitions that it is syncing. If the validation fails, the downloaded patch definition will not be written to the S3 bucket and the existing version will be preserved.
