import os
import io
import csv
import json
import sqlite3


from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
)
from openpyxl import Workbook
from tools.modules.database_functions import patient_variant_table, variant_annotations_table, validate_database
from tools.modules.clinvar_functions import clinvar_vs_download

# ---------------------------------------------------------------
# Flask setup
# ---------------------------------------------------------------
app = Flask(__name__, template_folder='templates')
app.secret_key = 'supersecretkey'
clinvar_vs_download()

# Get the filepath to the base directory.
base_dir = f'{os.path.dirname(os.path.abspath(__file__))}/../'
app.config['db_upload_folder'] = f'{base_dir}databases'
os.makedirs(app.config['db_upload_folder'], exist_ok=True)
app.config['variant_files_upload_folder'] = f'{base_dir}data'
os.makedirs(app.config['variant_files_upload_folder'], exist_ok=True)


# ===============================================================
# PAGE 1 — CHOOSE NEW DB or EXISTING DB
# ===============================================================
@app.route("/", methods=["GET", "POST"])
def choose_create_or_add():

    databases = []

    for f in os.listdir(app.config['db_upload_folder']):
        if f.endswith(".db"):
            databases += f

    databases.sort()

    if request.method == "POST":

        mode = request.form.get("mode")

        if mode == "new":
            return redirect(url_for("create_new_database"))

        elif mode == "existing":
            return redirect(url_for("add_to_existing_database"))

        flash("Please select an option:")

    return render_template("home_chatgpt.html", databases=databases)


# ===============================================================
# CREATE A NEW DATABASE
# ===============================================================
@app.route("/new", methods=["GET", "POST"])
def create_new_database():

    print("Request method:", request.method)

    if request.method == 'POST':
        file = request.files.get('vcf')

        if not file:
            flash("No file uploaded")
            return render_template("upload_new_chatgpt.html"), 400

        if not file.filename.endswith('.vcf'):
            flash("Invalid file type. Please upload a VCF file.")
            return render_template("upload_new_chatgpt.html"), 400

        # Save the file inside the uploads folder
        variant_file_path = os.path.join(app.config['variant_files_upload_folder'], file.filename)
        print("Saving file to:", variant_file_path)
        file.save(variant_file_path)

        # Get the absolute path for use in your scripts
        patient_variant_table(app.config['variant_files_upload_folder'])
        variant_annotations_table(app.config['variant_files_upload_folder'])

        flash(f"New database successfully created:\n{app.config['db_upload_folder']}")


        return redirect(url_for("query_page", db_name='sea.db'))

    # GET request: show the upload form
    return render_template('upload_new_chatgpt.html')


# ===============================================================
# ADD TO EXISTING DATABASE
# ===============================================================
@app.route("/existing", methods=["GET", "POST"])
def add_to_existing_database():

    if request.method == "POST" and "database_file" in request.files:

        file = request.files["database_file"]

        if not file.filename.endswith(".db"):
            flash("Please upload a .db file.")
            return render_template("upload_existing_chatgpt.html", databases=file.filename)

        database_path = os.path.join(app.config["db_upload_folder"], file.filename)
        file.save(database_path)

        if not validate_database(database_path):
            flash("❌ Inappropriate headers in database.")
            os.remove(database_path)
            return render_template("upload_existing_chatgpt.html")

        else:
            request.session["selected_db"] = file.filename
            flash("✅ Database uploaded and validated successfully.")
            return redirect(url_for("query_page", db_name=file.filename))


    # Step 2: Upload VCF to append data
    if request.method == "POST" and "vcf" in request.files:

        db_name = request.form.get("db_name")

        vcf_file = request.files["vcf"]
        if not vcf_file.filename.endswith(".vcf"):
            flash("Invalid VCF file.")
            return render_template("upload_existing_chatgpt.html", db_name=db_name)

        vcf_path = os.path.join(app.config["UPLOAD_FOLDER"], vcf_file.filename)
        vcf_file.save(vcf_path)

        folder_path = os.path.dirname(vcf_path)

        # Run your table builders again (append mode)
        patient_variant_table(folder_path)
        variant_annotations_table(folder_path)

        flash("Database updated successfully.")
        return redirect(url_for("query_page", db_name=db_name))

    return render_template("upload_existing_chatgpt.html")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)