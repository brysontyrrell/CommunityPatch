Add a New Software Title Definition
===================================

.. note::

   If you are creating a definition file for the first time, you can use the
   `Patch-Starter-Script <https://github.com/brysontyrrell/Patch-Starter-Script>`_
   available on GitHub.

   The examples provided below will reference this script.

POST /api/v1/titles
-------------------

Create a new patch definition. The JSON payload should contain the data for the
full patch definition.

.. code-block:: text

    POST /api/v1/titles
    Content-Type: application/json

.. code-block:: json

    {
        "id": "",
        "name": "",
        "publisher": "",
        "appName": "",
        "bundleId": "",
        "requirements": [],
        "patches": [],
        "extensionAttributes": []
    }

Response
--------

On success you will receive a message stating the new title has been created.

.. code-block:: text

    201 Created
    Content-Type: application/json

.. code-block:: json

    {
        "message": "Title '{ID}' created"
    }

Examples
--------

An example using ``curl`` and ``Patch-Starter-Script``:

.. code-block:: bash

    curl https://beta2.communitypatch.com/api/v1/titles \
        -X POST \
        -d "$(python patchstarter.py '/Applications/{APP}' -p '{PUBLISHER}')" \
        -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer {API-KEY}'
