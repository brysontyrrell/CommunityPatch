Add a new Version to a Software Title
=====================================

POST /api/v1/titles/{ID}/versions
---------------------------------

Update a software title's definition with a new version. The JSON payload should
only contain the data for the version.

.. code-block:: text

    POST /api/v1/titles/{ID}/version
    Content-Type: application/json

.. code-block:: json

    {
        "version": "",
        "releaseDate": "",
         "standalone": true,
        "minimumOperatingSystem": "",
        "reboot": false,
        "killApps": [],
        "components": [],
        "capabilities": [],
        "dependencies": []
    }

Response
--------

On success you will receive a message stating the new version has been added to
the title.

.. code-block:: text

    201 Created
    Content-Type: application/json

.. code-block:: json

    {
        "message": "Version '{VERSION}' added to title '{ID}'"
    }

Examples
--------

An example using ``curl`` and ``Patch-Starter-Script``:

.. code-block:: bash

    curl https://beta2.communitypatch.com/api/v1/titles/{ID}/versions \
        -X POST \
        -d "$(python patchstarter.py '/Applications/{APP}' --patch-only)" \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer {API-KEY}'

The default behavior for this request is to add the new version as the
``latest`` version of this definition.

Options
-------

.. note::

   If you make a request using the ``insert_after`` or ``insert_before`` options
   and the placement of the new version is not at the ``latest`` position, the
   definition's ``currentVersion`` will not be updated, but the ``lastModified``
   timestamp will be.

insert_after
^^^^^^^^^^^^

To specify the position of the new version in the ``patches`` array of the
definition, use the ``insert_after={VERSION}`` or ``insert_before={VERSION}``
parameters where ``VERSION`` is an existing version in the definition.

.. code-block:: text

    POST /api/v1/titles/{ID}/version?insert_after={VERSION}
    Content-Type: application/json

.. code-block:: bash

    curl https://beta2.communitypatch.com/api/v1/titles/{ID}/versions?insert_after={VERSION} \
        -X POST \
        -d "$(python patchstarter.py '/Applications/{APP}' --patch-only)" \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer {API-KEY}'

insert_before
^^^^^^^^^^^^^

.. code-block:: text

    POST /api/v1/titles/{ID}/version?insert_before={VERSION}
    Content-Type: application/json

.. code-block:: bash

    curl https://beta2.communitypatch.com/api/v1/titles/{ID}/versions?insert_before={VERSION} \
        -X POST \
        -d "$(python patchstarter.py '/Applications/{APP}' --patch-only)" \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer {API-KEY}'

