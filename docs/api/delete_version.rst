Delete a Version from a Software Title
======================================

DELETE /api/v1/titles/{ID}/versions/{VERSION}
---------------------------------------------

Delete a version from a software title's definition. The advertised
``currentVersion`` will be updated to reflect whatever the most 'recent" version
is after the operation.

.. note::

    You must have at least one (1) version defined for a software title. The
    API will respond with a 400 error if you attempt to delete the last
    remaining version.

.. warning::

    Use caution and judgement when deleting a version from a software title.
    You may negatively impact other admins using the definition for their own
    patch reports and policies!

.. code-block:: text

    DELETE /api/v1/titles/{ID}/versions/{VERSION}

Response
--------

On success you will receive a message stating the version has been removed from
the title.

.. code-block:: text

    200 OK
    Content-Type: application/json

.. code-block:: json

    {
        "message": "Version '{VERSION}' deleted from title"
    }

Examples
--------

An example using ``curl``:

.. code-block:: bash

    curl https://beta2.communitypatch.com/api/v1/titles/{ID}/versions/{VERSION} \
        -X DELETE \
        -H 'Authorization: Bearer {API-KEY}'
