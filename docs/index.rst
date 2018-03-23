CommunityPatch.com
==================

CommunityPatch.com is a free, open-source patch server for Jamf Pro
administrators to post patch definitions they maintain for the broader Jamf
community to subscribe to.

Create a New Software Title Definition
--------------------------------------

.. note::

   If you are creating a definition file for the first time, you can use the
   `Patch-Starter-Script <https://github.com/brysontyrrell/Patch-Starter-Script>`_
   available on GitHub.

   The examples provided below will reference this script.

``POST /api/v1/title``
^^^^^^^^^^^^^^^^^^^^^^

Create a new patch definition on CommunityPatch.com. You
must provide a JSON payload containing an `author_name` and an `author_email` in
addition to the full software title definition under the `definition` key.


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
      -d "{\"author_name\": \"Bryson\", \"author_email\": \"bryson.tyrrell@gmail.com\", \"definition\": $(python patchstarter.py /Applications/GitHub\ Desktop.app -p "GitHub")}" \
      -H 'Content-Type: application/json'

Update a Software Title Version
-------------------------------

``POST /api/v1/title/{title}/version``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Update a software title's definition with
a new version. The JSON payload should only contain the data for the version.

An example using ``curl`` and ``Patch-Starter-Script``:

.. code-block:: bash

   curl http://beta.communitypatch.com/api/v1/title/GitHubDesktop_Bryson/version \
      -X POST \
      -d "$(python patchstarter.py /Applications/GitHub\ Desktop.app -p "GitHub" --patch-only)" \
      -H 'Content-Type: application/json' \
      -H 'Authorization: Bearer <TOKEN>'

Add CommunityPatch.com to Jamf Pro
==================================

Configure as an External Patch Source in Jamf Pro.

.. note::

    "External Patch Sources" is a feature of Jamf Pro v10.2+.

To add your CommunityPatch.com as a **Patch External Source** in Jamf Pro, go to
**Settings > Computer Management > Patch Management** in the management console.

.. image:: _static/jamf_setup_01.png
   :align: center

Click the **+ New** button next to **Patch External Source**. On the next screen
assign a name to your Patch Server. In the **SERVER** field enter the URL as
shown::

   communitypatch.com/jamf/v1

In the **PORT** field enter ``443`` (can also be left blank).

Ensure the **Use SSL** box is checked.

.. image:: _static/jamf_setup_02.png
   :align: center

After saving your settings, a **Test** button will be available on the Patch
Server's page. Click it to verify Jamf Pro can connect to CommunityPatch.com and
data is being received.

.. image:: _static/jamf_setup_03.png
   :align: center

CommunityPatch.com will now be displayed on the **Patch Management** settings
page.

.. image:: _static/jamf_setup_04.png
   :align: center

You will now be able to choose software titles to subscribe to from the
**Computers > Patch Management > Software Titles** list.

.. image:: _static/jamf_setup_05.png
   :align: center
