Managing Patch Definitions
==========================

Manage your patch definition files for your patch server.

Populate the S3 Bucket in AWS Console
-------------------------------------

To make patch titles available on your Patch Server, upload the JSON file of the full patch definition into the root of the S3 bucket created for the application.

.. note::

    **The JSON filename must match the software title ID of the patch.**

Examples taken from Jamf's official patch server would be saved to the S3 bucket as::

    AdobeAcrobatProDC.json
    Composer.json
    GoogleChrome.json
    JavaSEDevelopmentKit8.json
    macOS.json
    MicrosoftWord2016.json

To update your patch definitions, replace the existing file in S3 with the new, updated file.
