Update a Software Title Version
===============================

Update a software title's definition with a new version. The JSON payload should
only contain the data for the version.

An example using ``curl`` and ``Patch-Starter-Script``:

.. code-block:: text

    POST /api/v1/title/<ID>/version

.. code-block:: bash

   curl http://beta.communitypatch.com/api/v1/title/<ID>/version \
      -X POST \
      -d "$(python patchstarter.py /Applications/<APP> --patch-only)" \
      -H 'Content-Type: application/json' \
      -H 'Authorization: Bearer <TOKEN>'

The default behavior for this request is to add the new version as the
``latest`` version of this definition.

Using ``insert_before`` and ``insert_after``
--------------------------------------------

To specify the position of a version in the ``patches`` array of the definition,
use the ``insert_after=<VERSION>`` or ``insert_before=<VERSION>`` parameters
where ``VERSION`` is an existing version in the definition.

.. code-block:: text

    POST /api/v1/title/<ID>/version?insert_before=<VERSION>

    POST /api/v1/title/<ID>/version?insert_after=<VERSION>

.. code-block:: bash

   curl 'http://beta.communitypatch.com/api/v1/title/<ID>/version?insert_after=<VERSION>' \
      -X POST \
      -d "$(python patchstarter.py /Applications/<APP> --patch-only)" \
      -H 'Content-Type: application/json' \
      -H 'Authorization: Bearer <TOKEN>'

   curl 'http://beta.communitypatch.com/api/v1/title/<ID>/version?insert_before=<VERSION>' \
      -X POST \
      -d "$(python patchstarter.py /Applications/<APP> --patch-only)" \
      -H 'Content-Type: application/json' \
      -H 'Authorization: Bearer <TOKEN>'

.. note::

   If you make a request using the ``insert_after`` or ``insert_before`` options
   and the placement of the new version is not at the ``latest`` position, the
   definition's ``currentVersion`` will not be updated, but the ``lastModified``
   timestamp will be.
