Add a New Software Title Definition
===================================

.. note::

   If you are creating a definition file for the first time, you can use the
   `Patch-Starter-Script <https://github.com/brysontyrrell/Patch-Starter-Script>`_
   available on GitHub.

   The examples provided below will reference this script.

Add a Title Using JSON
----------------------

Create a new patch definition on CommunityPatch by providing the entire
definition JSON body. You must provide a JSON payload containing an
``author_name`` and an ``author_email`` in addition to the full software title
definition under the ``definition`` key.

.. code-block:: text

    POST /api/v1/title

.. code-block:: json

   {
      "author_name": "<NAME>",
      "author_email": "<EMAIL>",
      "definition": {}
   }

The ``id`` and ``name`` values of the provided software title definition will be
modified to include the ``author_name`` (as a unique identifier for the title).

On success, an API token to manage this software title will be sent to the
provided email address. The modified ``id`` and ``name`` values will be returned
with the API request as well as included in the email.

.. note::

   Your email address is not stored in a usable format. It is saved as a hashed
   value with the record of the software title. This hash is only used to
   validate requests to reset the API token for a definition.

An example using ``curl`` and ``Patch-Starter-Script``:

.. code-block:: bash

   curl https://beta.communitypatch.com/api/v1/title \
      -X POST \
      -d "{\"author_name\": \"<NAME>\", \"author_email\": \"<EMAIL>\", \"definition\": $(python patchstarter.py /Applications/<APP> -p "<PUBLISHER>")}" \
      -H 'Content-Type: application/json'

Add a Synced Title Using a URL
------------------------------

Create a sycned patch definition on CommunityPatch by providing a source URL
to a definition hosted on another server. AFter a successful creation, the
definition will be synced every 30 minutes from the source URL. You must provide
a JSON payload containing an ``author_name`` and an ``author_email`` in addition
to a ``definition_url`` key containing the source URL.

.. code-block:: text

    POST /api/v1/title

.. code-block:: json

    {
      "author_name": "<NAME>",
      "author_email": "<EMAIL>",
      "definition_url": "<URL>"
   }

The ``id`` and ``name`` values of the provided software title definition will be
modified to include the ``author_name`` (as a unique identifier for the title).

On success, an API token to manage this software title will be sent to the
provided email address. The modified ``id`` and ``name`` values will be returned
with the API request as well as included in the email.

.. note::

    A synced definition cannot be updated using the API. THe token can only be
    used to delete the title.

An example ``curl`` command:

.. code-block:: bash

   curl https://beta.communitypatch.com/api/v1/title \
      -X POST \
      -d "{\"author_name\": \"<NAME>\", \"author_email\": \"<EMAIL>\", \"definition_url\": \"<URL>\"}" \
      -H 'Content-Type: application/json'
