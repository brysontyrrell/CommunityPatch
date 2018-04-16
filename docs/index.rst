CommunityPatch.com
==================

CommunityPatch.com is a free, open-source patch server for Jamf Pro
administrators to post patch definitions they maintain for the broader Jamf
community to subscribe to.

Manage Titles with the API
--------------------------

If you want to contribute to the patch definitions available on CommunityPatch,
read how to in the API documentation.

.. toctree::
   :maxdepth: 1

   api/create
   api/update

Add CommunityPatch.com to Jamf Pro
----------------------------------

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

   beta.communitypatch.com/jamf/v1

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
