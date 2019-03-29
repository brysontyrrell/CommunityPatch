Delete a Software Title
=======================

DELETE /api/v1/titles/{ID}
--------------------------

Delete a software title from your submitted titles.

.. warning::

    This does not remove the patch definition from any Jamf Pro instance that
    has subscribed to it. Those objects will continue to exist until the admin
    deletes them, but will no longer be updated.

.. code-block:: text

    DELETE /api/v1/titles/{ID}

Response
--------

On success you will recieve a message stating the title has been deleted.

.. code-block:: text

    200 OK
    Content-Type: application/json

.. code-block:: json

    {
        "message": "Title '{ID}' has been deleted"
    }

Examples
--------

An example using ``curl``:

.. code-block:: bash

    curl https://beta2.communitypatch.com/api/v1/titles/{ID} \
        -X DELETE \
        -H 'Authorization: Bearer {API-KEY}'

