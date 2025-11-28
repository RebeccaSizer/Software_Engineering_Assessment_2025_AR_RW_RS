import os
import subprocess
import webbrowser
from threading import Timer
from app.app import app
from tools.utils.logger import logger
from tools.modules.clinvar_functions import clinvar_vs_download

# A simple banner to appear in the terminal stdout.
print("\n\n *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*\n",
      "|                                                 |\n",
      "*   Welcome to the Variant Database Query Tool!   *\n",
      "|                                                 |\n",
      "*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*\n\n")

#Log when the app was started.
logger.info("Application started")

# Create a filepath to the ClinVar database
base_dir = os.path.dirname(os.path.abspath(__file__))
clinvar_db_path = os.path.join(base_dir, "app", "clinvar", "clinvar.db")

# Download the ClinVar database if the filepath above does not exist
if not os.path.exists(clinvar_db_path):
    logger.debug("ClinVar DB missing → Please wait ~6 minutes for download to complete...")
    clinvar_vs_download()
    logger.info("ClinVar database downloaded.")
else:
    logger.info("ClinVar database available. No download needed.")

logger.info("Launching flask app @ http://127.0.0.1:5000")


def open_browser():
    '''
    Function that launches the flask app automatically at startup on port 5000.
    '''
    webbrowser.open("http://127.0.0.1:5000")

# Timer module initiates the open_browser function above after 1 second, launchning the flask app. App runs in debug
# mode when debug=True
if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True)