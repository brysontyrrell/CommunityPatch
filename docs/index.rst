.. StupidSimplePatchServer documentation master file, created by
   sphinx-quickstart on Thu Jan 25 17:27:37 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Stupid Simple Patch Server
==========================

The Supid Simple Patch Server (SSPS) is a serverless application to provide a patch server for Jamf Pro administrators.

With the SSPS you can host your own software title patch definitions for custom patch policies. The SSPS also allows you to :doc:`subscribe to other administrators' patch definitions </managing/subscriptions>` and automate the management of your patch definitions using it's :doc:`REST API </documentation/rest_api>`.

.. toctree::
   :maxdepth: 1
   :caption: Deploy and Setup

   setup/deploy_on_aws
   setup/jamf_pro_setup

.. toctree::
   :maxdepth: 1
   :caption: Managing Your Patch Server

   managing/manage_definitions
   managing/subscriptions

.. toctree::
   :maxdepth: 1
   :caption: API Documentation

   documentation/patch_endpoints
   documentation/rest_api
