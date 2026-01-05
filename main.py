"""
SEA - Variant Database Query tool entry point.

This script is responsible for:
    - Initialising the Flask app.
    - Launching the app in a web browser.
    - Checking if a copy of clinvar.db exists in the app/clinver subirectory.
    - Logging the start of the application.

No patient or variant-level data is processed here.
Some of the code used in this script derives from ChatGPT.
"""

import os
import sys
import webbrowser
from app.app import app
from threading import Timer
from tools.utils.logger import logger
from tools.modules.clinvar_functions import clinvar_vs_download

# A simple banner to appear in the terminal stdout.
print("\n\n *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-**-*-*-*-*-*-*-*-*-*-*-*\n",
      "|                                                      |\n",
      "*   Welcome to SEA: the Variant Database Query Tool!   *\n",
      "|                                                      |\n",
      "*-*-*-*-*-*-*-*-*-*-**-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*\n\n")

# Log when the app was started.
logger.info("Application started")

# Create a filepath to the ClinVar database
base_dir = os.path.dirname(os.path.abspath(__file__))
clinvar_db_path = os.path.join(base_dir, "app", "clinvar", "clinvar.db")

def clinvar_db_check(path):
    """
    This function checks if a clinvar.db exists in the app/clinvar subdirectory.
    :param path: The path to clinvar.db.
    """
    # Download the ClinVar database if the filepath above does not exist
    if not os.path.exists(path):
        logger.debug(
            "ClinVar DB missing → Starting Download.\n\tPlease wait ~6 minutes for download to complete...")
        clinvar_vs_download()
        logger.info("ClinVar database successfully downloaded.")
    else:
        logger.info("ClinVar database available. No download needed.")


def open_browser():
    '''
    Function that launches the flask app automatically at startup on port 5000, unless port forwarding is required.
    '''
    try:
        # Open the http://127.0.0.1:5000 webpage in a local browser.
        webbrowser.open("http://127.0.0.1:5000")
        # Log the address where the flask app was launched.
        logger.info("Launching flask app @ http://127.0.0.1:5000")

    # If an error occurs while launching the flask app in a web browser, log the error.
    except Exception as e:
        logger.warning(f"Could not launch flask app @ http://127.0.0.1:5000 in web browser. {e}")

def run_app():
    """
    This function first runs the clinvar_db_check function to check if a clinvar database already exists before
    launching the app.
    :return:
    """
    # Run the clinvar_db_check
    clinvar_db_check(clinvar_db_path)
    # Timer module initiates the open_browser function above after 1 second, launching the flask app. App runs in debug
    # mode when debug=True
    Timer(1, open_browser).start()
    app.run(debug=True)

# Initialise this script from the commandline.
if __name__ == "__main__":
    try:
        run_app()
    # Raise a RuntimeError exception if an error occurs while checking for a local copy of the ClinVar database and log
    # the error.
    except RuntimeError as e:
        logger.critical(f"ClinVar database download check failed. Application cannot be started. {e}")
    # If an error occurs while launching the flask app, log the error and exit the program cleanly.
    except Exception as e:
        logger.critical(f"Fatal error occurred during application startup: {e}")
        sys.exit(0)