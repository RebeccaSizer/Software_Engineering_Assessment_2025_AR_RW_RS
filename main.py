import os
import webbrowser
from threading import Timer
from tools.modules.clinvar_functions import clinvar_vs_download
from app.app import app

# Create a filepath to the ClinVar database
base_dir = os.path.dirname(os.path.abspath(__file__))
clinvar_db_path = os.path.join(base_dir, "app", "clinvar", "clinvar.db")

# Download the ClinVar database if the filepath above does not exist
if not os.path.exists(clinvar_db_path):
    print("ClinVar DB missing → Please wait ~6 minutes for download to complete...")
    clinvar_vs_download()
else:
    print("ClinVar database available. No download needed.")


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True)