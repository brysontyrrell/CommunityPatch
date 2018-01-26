Patch Definition Subscriptions
==============================

How to subscribe to someone else's patch definition.

Subscribe to a Patch Definition
-------------------------------

To subscribe to the URL of a patch definition, make a POST request to the `/subscribe` endpoint with a JSON payload containing the software title ID ('`id'`) and the URL to the JSON file (`'json_url'`)::

    POST https://<patch-server-url>/subscribe
    Content-Type: application/json
    Body: {"id": "<patch-title-name>", "json_url": "<url-to-JSON-file>"}

.. note::

    The Patch Server performs validations on all patch definitions it retrieves. If the validation fails, the subscription request will be rejected.

Patch Definition Syncing
------------------------

Every five (5) minutes, the Patch Server will sync all subscribed patch definitions. It will download the source from the provided URL and write the definition into the S3 bucket, overwriting the last version of the patch definition.

.. note::

    The Patch Server will perform validation on the patch definitions that it is syncing. If the validation fails, the downloaded patch definition will not be written to the S3 bucket and the existing version will be preserved.

Unsubscribe from a Patch Definition
-----------------------------------

To unsubscribe from a patch definition, make a POST request to the `/unsubscribe` endpoint with the name of the software title::

    POST https://<patch-server-url>/unsubscribe/<patch-title-name>

This will remove the patch definition from syncing and delete the patch definition file from the S3 bucket.
