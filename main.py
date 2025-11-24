import os
import subprocess
from tools.modules.clinvar_functions import clinvar_vs_download

script_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(script_dir, "app", "clinvar"), exist_ok=True)
clinvar_db_path = os.path.join(script_dir, "app", "clinvar", "clinvar.db")
clinvar_gz_path = os.path.join(script_dir, "app", "clinvar", "clinvar_db_summary.txt.gz")

# Run download only if DB is missing
if not os.path.exists(clinvar_db_path):
    print("ClinVar DB missing → Please wait ~6 minutes for download to complete...")
    clinvar_vs_download()
elif not os.path.exists(clinvar_gz_path):
    print("ClinVar summary file missing → Please wait ~6 minutes for download to complete...")
    clinvar_vs_download()
else:
    print("ClinVar database available. No download needed.")

subprocess.run(["python", "app/app.py"])