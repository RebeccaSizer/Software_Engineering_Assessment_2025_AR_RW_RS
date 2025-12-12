import os
import sys
import io
import csv
import json
import errno
import sqlite3
from openpyxl import Workbook


from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    session
)

# Add the project root to sys.path so Python can find 'tools'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.utils.logger import logger
from tools.modules.vv_functions import get_mane_nc
from tools.utils.error_handlers import request_status_codes, connection_error, sqlite_error
from tools.modules.database_functions import (
    patient_variant_table,
    variant_annotations_table,
    validate_database,
    query_db
)

# ---------------------------------------------------------------
# Flask setup
# ---------------------------------------------------------------

#Initialise the app using the .html files in the templates folder.
app = Flask(__name__, template_folder='templates')
app.secret_key = 'supersecretkey'

# Get the filepath to the base directory.
base_dir = f'{os.path.dirname(os.path.abspath(__file__))}/../'
# Assign the filepath to the 'databases' folder to the 'db_upload_folder' key in the flask app.config dictionary.
app.config['db_upload_folder'] = f'{base_dir}databases'
# Make the 'databases' folder if it does not already exist.
os.makedirs(app.config['db_upload_folder'], exist_ok=True)
# Assign the filepath to the 'temp' folder to the 'variant_files_upload_folder' key in the flask app.config dictionary.
app.config['variant_files_upload_folder'] = os.path.join(base_dir, 'temp')
# Make the 'temp' folder if it does not already exist.
os.makedirs(app.config['variant_files_upload_folder'], exist_ok=True)


# ---------------------------------------------------------------
# Route: Homepage - create, upload or select a database
# ---------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def choose_create_or_add():
    """
    This function facilitates the use of the Variant Query Database homepage. Users are able to Upload variants from
    variant files with .VCF or .CSV extensions to a new or existing database. They are also able to redirect to the
    query page, where databases can be queried, after they are selected or uploaded on the homepage.
    """

    # The function uploads variants from every variant file in the 'temp' folder. If the User uploaded any variant files
    # without adding them to a database, the variant files will still be in the 'temp' folder the next time the app is
    # used. This will cause the database functions in this script to run slower. If the uploaded files are not
    # variant files, the functions will raise an exception. Therefore, the contents of the 'temp' folder are purged
    # from the folder before the homepage is loaded.
    for variant_file in os.listdir(app.config['variant_files_upload_folder']):
        os.remove(os.path.join(app.config['variant_files_upload_folder'], variant_file))
        # Log which files were deleted from the 'temp' folder.
        logger.info(f"{variant_file} removed from 'temp' folder.")

    # Create an empty list to iterate through the databases.
    databases = []

    # Add the names of the databases in the 'databases' folder to the databases list.
    for f in os.listdir(app.config['db_upload_folder']):
        if f.endswith(".db"):
            databases.append(f)

    # Sort them into alphabetical order to make them easily viewable for the User.
    databases.sort()

    # If no databases are in the 'databases' folder, log that there are not databases in the folder.
    if len(databases) == 0:
        logger.info(f"There are no databases in the 'databases' folder.")
    # Log which databases were found in the 'databases' folder.
    else:
        logger.info(f"Databases in the 'databases' folder: {', '.join(databases)}")

    # Perform the following processes if the User's request uses the HTTP 'POST' method.
    if request.method == "POST":
        # Each operation (create or add to database, select a database to query, upload a database to query) has been
        # assigned a form-type ID in the homepage.html file. This retrieves the form-type ID used by the User.
        form_type = request.form.get("form_type")

        # The 'add_variant' form-type corresponds with creating or adding to a database.
        if form_type == "add_variant":
            # Log that the User wants to create or add to a database.
            logger.info(f'Form-type: add_variant. User is trying to create or add to a database.')

            # The variant files uploaded by the User are added to a list called 'variant_files' in the backend.
            # This command pulls the variant files into the variable, 'files'.
            files = request.files.getlist("variant_files")
            # The databases in the 'databases' folder appear in a dropdown menu, for the User to select. This command
            # pulls the selected database into the variable, 'database_name'.
            database_name = os.path.splitext(request.form["db_file"])[0]

            # The html provides many prompts preventing the User from not uploading a file before creating/adding to
            # the database. However, if somehow nothing has been assigned to the 'files' variable...
            if not files or files[0].filename == '':
                # A warning appears at the top of the homepage.
                flash("⚠ A variant file was not uploaded")
                # The warning is also logged.
                logger.warning("No variant files were uploaded.")
                # Render the output into the homepage.
                return render_template("homepage.html", databases=databases)

            # Save the selected files to the 'temp' folder.
            for file in files:
                # If the file does not have a .CSV or.VCF extension, they cannot be uploaded.
                if not file.filename.endswith('.vcf') and not file.filename.endswith('.csv'):
                    # Log that the file could not be uploaded.
                    logger.warning(f"{file.filename} not uploaded because it is not a .VCF or .CSV file.")
                    flash("❌ Invalid file type. Please upload .VCF or .CSV files only.")
                    # Render this output into the homepage.
                    return render_template("homepage.html", databases=databases)

                # Test if the file can be saved to the 'temp' folder.
                try:
                    # Create a filepath to the uploaded file, in the 'temp' folder.
                    variant_file_path = os.path.join(app.config['variant_files_upload_folder'], file.filename)
                    # Save the file using the aforementioned filepath.
                    file.save(variant_file_path)
                    # Log the name of the file that was saved to the 'temp' folder.
                    logger.info(f"{file.filename} uploaded to 'temp' folder.")

                # Raise an exception if the User lack permission to save the file.
                except PermissionError as e:
                    # Log the error, explaining the User's lack of permission, using the exception output.
                    logger.error(
                        f"Failed to save {file.filename} to {app.config['variant_files_upload_folder']} because the "
                        f"User lacks permissions: {str(e)}")
                    # Notify the User that the file couldn't be saved to the 'temp' folder because they lack permission.
                    flash(f'❌ Failed to save {file.filename}. Permission denied.')
                    # Render this output into the homepage.
                    return render_template("homepage.html", databases=databases)

                # Raise an exception if there is an error with the system, preventing the file from being saved.
                except OSError as e:
                    # from ChatGPT.
                    if e.errno == errno.ENOSPC:
                        # Log the error, explaining there isn't enough disk space, using the exception output.
                        logger.error(
                            f"Failed to save {file.filename} to {app.config['variant_files_upload_folder']} because "
                            f"there is not enough disk space: {str(e)}")
                        # Notify the User that the file couldn't be saved to the 'temp' folder because there is not
                        # enough disk.
                        flash(f'❌ Failed to save {file.filename}. Not enough disk space.')
                        # Render this output into the homepage.
                        return render_template("homepage.html", databases=databases)

                    else:
                        # Log that there was an error with the operating system, using the exception output.
                        logger.error(
                            f"Failed to save {file.filename} to {app.config['variant_files_upload_folder']} because "
                            f"there is an issue with the operating system: {str(e)}")
                        # Notify the User that the file couldn't be saved to the 'temp' folder.
                        flash(
                            f'❌ Failed to save {file.filename}. There is an issue with the operating system: '
                            f'{str(e)}')
                        # Render this output into the homepage.
                        return render_template("homepage.html", databases=databases)

                # Raise an exception if the file cannot be saved.
                except Exception as e:
                    # Log the error, describing the reason why the test failed, using the exception output.
                    logger.error(
                        f"Failed to save {file.filename} to {app.config['variant_files_upload_folder']}: {str(e)}")
                    # Notify the User that the file couldn't be saved to the 'temp' folder.
                    flash(f'❌ Failed to save {file.filename}: {str(e)}')
                    # Render this output into the homepage.
                    return render_template("homepage.html", databases=databases)

            # Execute the imported database_functions, using the absolute path to the 'temp' folder and the database
            # created/selected by the User. These functions parse the files and populate the database with the relevant
            # information.
            # Log the start of when the variant files are being loaded into the User-specified database.
            logger.info(f"Starting to load variant files from 'temp' folder, into {database_name} database.")
            patient_variant_table(app.config['variant_files_upload_folder'], database_name)
            variant_annotations_table(app.config['variant_files_upload_folder'], database_name)
            # Log when the variant files have been loaded into the database.
            logger.info(f"Successfully loaded variant files into {database_name} database.")

            # Delete the files from the 'temp' folder otherwise every file in the 'temp' folder will be processed after
            # the User adds another file to the database.
            for file in files:
                variant_file_path = os.path.join(app.config['variant_files_upload_folder'], file.filename)
                os.remove(variant_file_path)
                # Log when the file has been deleted from the 'temp' folder.
                logger.info(f"{file.filename} removed from 'temp' folder.")

            # Notify the User which files have been loaded into the database.
            filenames = [file.filename for file in files]
            flash(f"Added {', '.join(filenames)} to database.")
            # Refresh the homepage so that the newly created/updated database can be queried.
            return redirect(url_for("choose_create_or_add"))

        # The 'open_db' form-type corresponds with querying a database that already exists in the 'database' folder, in
        # the homepage.html.
        elif form_type == "open_db":
            # The 'existing_db' represents the database that the User selected from the dropdown menu on the homepage.
            selected_db = request.form.get("existing_db")
            # Log which database is going to be queried.
            logger.info(f'User is going to query the {selected_db} database.')
            # Redirect the User to the query page where the chosen database can be queried.
            return redirect(url_for("query_page", db_name=selected_db))

        # The 'upload_db' form-type corresponds with uploading a database so that it can be queried, in the
        # homepage.html.
        elif form_type == "upload_db":

            # Log that the User wants to create or add to a database.
            logger.info(f'Form-type: upload_db. User is trying to upload a database to query.')

            # The uploaded file is represented by 'database_file' in the homepage.html, which is assigned to the file
            # 'variable'.
            file = request.files.get("database_file")

            # The html provides many prompts preventing the User from not uploading a database. However, if somehow
            # nothing has been assigned to the 'files' variable...
            if not file or file.filename == "":
                # A warning appears at the top of the homepage, notifying the User.
                flash("⚠ A database file was not uploaded.")
                # The warning is also logged.
                logger.warning('No database files were uploaded.')
                # Render the output into the homepage.
                return render_template("homepage.html", databases=databases)

            # Assign the database's file name to the variable 'filename'.
            filename = file.filename

            # If the filename does not end with the .DB database extension, it will be rejected from being uploaded.
            if not filename.endswith(".db"):
                # Log the rejection.
                logger.warning(f'{filename} does not contain a .db file extension. It is not recognised as a database '
                               f'file.')
                # Notify the User that their attempt to upload a database has been rejected.
                flash('❌ Invalid file type. Please upload a .db file.')
                return render_template("homepage.html", databases=databases)

            # Test that the database can be saved to the 'database' folder, where the database can be queried from.
            try:
                # Create a filepath to the 'database' folder.
                filepath = os.path.join(app.config['db_upload_folder'], filename)
                # Save the uploaded file to the aforementioned filepath.
                file.save(filepath)
                # Log the name of the file that was saved to the 'temp' folder.
                logger.info(f"{file.filename} uploaded to 'database' folder.")

            # Raise an exception if the User lack permission to save the file.
            except PermissionError as e:
                # Log the error, explaining the User's lack of permission, using the exception output.
                logger.error(
                    f"Failed to save {filename} to {app.config['db_upload_folder']} because the User lacks permissions:"
                    f" {str(e)}")
                # Notify the User that the file couldn't be saved to the 'database' folder because they lack permission.
                flash(f'❌ Failed to save {filename} database. Permission denied.')
                # Render this output into the homepage.
                return render_template("homepage.html", databases=databases)

            # Raise an exception if there is an error with the system, preventing the file from being saved.
            except OSError as e:
                # from ChatGPT.
                if e.errno == errno.ENOSPC:
                    # Log the error, explaining there isn't enough disk space, using the exception output.
                    logger.error(
                        f"Failed to save {filename} to {app.config['db_upload_folder']} because there is not enough "
                        f"disk space: {str(e)}")
                    # Notify the User that the file couldn't be saved to the 'database' folder because there is not
                    # enough disk.
                    flash(f'❌ Failed to save {filename}. Not enough disk space.')
                    # Render this output into the homepage.
                    return render_template("homepage.html", databases=databases)

                else:
                    # Log that there was an error with the operating system, using the exception output.
                    logger.error(
                        f"Failed to save {filename} to {app.config['db_upload_folder']} because there is an issue with "
                        f"the operating system: {str(e)}")
                    # Notify the User that the file couldn't be saved to the 'database' folder.
                    flash(
                        f'❌ Failed to save {filename}. There is an issue with the operating system: '
                        f'{str(e)}')
                    # Render this output into the homepage.
                    return render_template("homepage.html", databases=databases)

            # Raise an exception if the file cannot be saved.
            except Exception as e:
                # Log the error, describing the reason why the test failed, using the exception output.
                logger.error(
                    f"Failed to save {filename} to {app.config['db_upload_folder']}: {str(e)}")
                # Notify the User that the file couldn't be saved to the 'database' folder.
                flash(f'❌ Failed to save {filename}: {str(e)}')
                # Render this output into the homepage.
                return render_template("homepage.html", databases=databases)

            # validate_database() function ensures that the database conforms with the expected schema that allows the
            # database file to be queried.
            if not validate_database(filepath):
                # Log that the database contains inappropriate headers.
                logger.warning(f'{filename} does not contain the appropriate headers and cannot be queried.')
                # Notify the User that the database has not passed validation.
                flash(f'❌ Inappropriate headers in {filename} database.')
                # Remove the database file from the 'database' folder.
                os.remove(filepath)
                # Log that the database file was removed.
                logger.info(f"Removed {filename} from 'database' folder.")
            else:
                # Log that the database was successfully uploaded and validated.
                logger.info(f"Successfully uploaded and validated {filename} database.")
                # Notify the User that the database was successfully uploaded and validated.
                flash("✅ Database uploaded and validated successfully.")
                # Redirect the User to the query page where the uploaded database can be queried.
                return redirect(url_for("query_page", db_name=filename))

    # Render the output from this function into the homepage.
    return render_template("homepage.html", databases=databases)


# ---------------------------------------------------------------
# Route: Query page - patient, variant_NC, or gene searches
# ---------------------------------------------------------------
@app.route("/query/<db_name>", methods=["GET", "POST"])
def query_page(db_name):
    """
    This function facilitates the use of the Variant Query Database query page. Users are able to search their database
    by patient, variant and by gene. They are also able to redirect to the display page where they can view their
    database in its entirety.

    :params: db_name: The name of the database being queried.
               E.g.: sea.db

    :query input: Patient: The name of the patient as it exists in the database.
                           The database's schema names patients after the filename used to upload their respective
                           variant data.

                     E.g.: Variants derived from a file named, 'Patient_X.csv".
                           Patient = Patient_X

    :query output: Table: A table consisting of all the variants successfully uploaded into the database, from the
                          queried patient's variant file. Each variant constitutes a row in the table which comprises
                          of the Patient ID; HGVS genomic description; HGVS transcript description; HGVS protein
                          consequence description; gene symbol; HGNC ID; Classification; Associated conditions; ClinVar
                          star-rating; Clinvar review status.

                    E.g.:  patient_ID	       | variant_NC	                 | variant_NM	            | variant_NP	               | gene  | HGNC_ID | Classification	 | Conditions	                                                                                                        | Stars | Review_status
                          ---------------------|-----------------------------|----------------------- --|-------|----------------------|-------|---------|-------------------|----------------------------------------------------------------------------------------------------------------------|-------|--------------------------------------
                           Patient_X	       | NC_000005.10:g.150056311C>T | NM_001288705.3:c.2350G>A | NP_001275634.1:p.(Val784Met) | CSF1R | 2433    | Likely pathogenic | Hereditary diffuse leukoencephalopathy with spheroids; Brain abnormalities, neurodegeneration, and dysosteosclerosis | ★	    | criteria provided, single submitter

    :query input: Variant: HGVS genomic descriptions, HGVS transcript descriptions and gene symbols followed by a
                           variant in HGVS nomenclature are all accepted queries because the get_mane_nc() function is
                           leveraged to return the HGVS genomic description, relative to the MANE select transcript.
                           This is then searched for in the database to find the variant.

                     E.g.: NC_000005.10:g.150056311C>T
                           NM_001288705.3:c.2350G>A
                           CSF1R:c.301G>A

    :query output: Table: A table consisting of the variant. The variant occupies a single row in the table which
                          comprises of the HGVS genomic description; HGVS transcript description; HGVS protein
                          consequence description; gene symbol; HGNC ID; Classification; Associated conditions; ClinVar
                          star-rating; Clinvar review status; Number of patients in the database with the variant.

                    E.g.:  variant_NC	               | variant_NM	              | variant_NP	                 | gene  | HGNC_ID | Classification	   | Conditions	                                                                                                          | Stars | Review_status                       | Patient_Count
                          -----------------------------|----------------------- --|------------------------------|-------|---------|-------------------|----------------------------------------------------------------------------------------------------------------------|-------|-------------------------------------|----------------
                           NC_000005.10:g.150056311C>T | NM_001288705.3:c.2350G>A | NP_001275634.1:p.(Val784Met) | CSF1R | 2433    | Likely pathogenic | Hereditary diffuse leukoencephalopathy with spheroids; Brain abnormalities, neurodegeneration, and dysosteosclerosis | ★	  | criteria provided, single submitter | 1

    :query input:   Gene: The gene symbol of a gene. Some genes have multiple gene symbols. Each gene is associated with
                          a specific HGNC ID. When searching by the gene symbol, the app actually searches the database
                          by the associated HGNC ID so it can find all the variants in the corresponding gene, regardless
                          of the gene symbol.

                    E.g.: CSF1R

    :query output: Table: A table consisting of all the variants in the database that are associated with the queried
                          gene symbol's HGNC ID . Each variant occupies a row in the table which comprises of the HGVS
                          genomic description; HGVS transcript description; HGVS protein consequence description; gene
                          symbol; HGNC ID; Classification; Associated conditions; ClinVar star-rating; Clinvar review
                          status; Number of patients in the database with the variant.

                    E.g.   variant_NC	               | variant_NM	              | variant_NP	                 | gene  | HGNC_ID | Classification	   | Conditions	                                                                                                          | Stars | Review_status                       | Patient_Count
                          -----------------------------|----------------------- --|------------------------------|-------|---------|-------------------|----------------------------------------------------------------------------------------------------------------------|-------|-------------------------------------|----------------
                           NC_000005.10:g.150056311C>T | NM_001288705.3:c.2350G>A | NP_001275634.1:p.(Val784Met) | CSF1R | 2433    | Likely pathogenic | Hereditary diffuse leukoencephalopathy with spheroids; Brain abnormalities, neurodegeneration, and dysosteosclerosis | ★	  | criteria provided, single submitter | 1
    """

    # log that the query page is being used.
    logger.info('User has accessed the Query page.')

    # Check that there are databases in the 'database' folder, that can be queried.
    try:
        # Add the names of the databases in the 'databases' folder to the databases list.
        databases = [
            f for f in os.listdir(app.config["db_upload_folder"]) if f.endswith(".db")
        ]

        # Sort the list into alphabetical order.
        databases.sort()

    # Raise an Exception if a file that ends in .DB (a database file) cannot be found in the 'databases' folder.
    except FileNotFoundError as e:
        logger.error(f'Failed to find any databases. Redirecting User back to homepage: {e}')
        flash('❌ Failed to find any databases. Please upload a database on the homepage.')
        # Redirect the User back to the homepage.
        return redirect(url_for("choose_create_or_add"))

    # Check that the filepath to the database file that was selected or uploaded on the homepage exists.
    # Assign the filepath to the selected databse to 'db_path' variable.
    db_path = os.path.join(app.config["db_upload_folder"], db_name)
    # If the filepath to the database file does not exist...
    if not os.path.exists(db_path):
        # ...Log a warning that the database does not exist.
        logger.warning(f"{db_name} database could not be found in: {db_path}")
        # Notify the User that the database was not found in the database folder.
        flash(f"⚠ {db_name} database not found. Please select a database to query on the homepage.")
        # Redirect the User back to the homepage.
        return redirect(url_for("choose_create_or_add"))

    # Check that the patient IDs, HGVS genomic descriptions and gene symbols can be parsed from the tables in the
    # database into the dropdown menus on the query page.
    try:
        # Load the selected database using the absolute filepath to the database file.
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            # Retrieve all the patient IDs in the patient_variant table, only once.
            cur.execute(
                "SELECT DISTINCT patient_ID FROM patient_variant ORDER BY patient_ID ASC;"
            )
            # Store the patient IDs into a list assigned to the 'patient_list' variable.
            patient_list = [row[0] for row in cur.fetchall()]
            # Retrieve all the HGVS genomic descriptions in the variant_annotations table, only once.
            cur.execute(
                "SELECT DISTINCT variant_NC FROM variant_annotations ORDER BY variant_NC ASC;"
            )
            # Store the HGVS genomic descriptions into a list assigned to the 'variant_list' variable.
            variant_list = [row[0] for row in cur.fetchall()]
            # Retrieve all of the gene symbols in the variant_annotations table, only once.
            cur.execute("SELECT DISTINCT gene FROM variant_annotations ORDER BY gene ASC;")
            # Store the gene symbols into a list assigned to the 'gene_list' variable.
            gene_list = [row[0] for row in cur.fetchall()]

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately and returns an error message which can be implemented
        # into a flash message, on the query page.
        error_message = sqlite_error(e, db_name)
        flash(f'❌ {db_name} Error: {error_message}')
        return render_template("db_query_page.html", db_name=db_name)

    # Raise an exception if the there was an issue querying clinvar.db.
    except Exception as e:
        # Log the error, describing why clinvar.db could not be queried, using the exception output.
        logger.error(f'Database Error: Failed to prepare {db_name} to be queried: {str(e)}')
        # Return a flash message to the User, notifying them of the error, on the query page.
        flash(f'❌ {db_name} Error: Failed to prepare {db_name} to be queried: {str(e)}')
        return render_template("db_query_page.html", db_name=db_name)

    # Create the data variable to
    data = None
    result_type = None

    # Handle search term from User's query
    if request.method == "POST":
        patient_ID = request.form.get("patient_ID")
        variant_nc = request.form.get("variant_NC")
        gene = request.form.get("gene")

        try:
            # If the User is performing a patient query...
            if patient_ID:
                # Log that they are trying to retrieve the variants for a patient.
                logger.info(f'User querying variants from {patient_ID}...')
                # Assign the queried patient ID and corresponding HGVS genomic descriptions, HGVS transcript
                # descriptions, HGVS protein descriptions of the variants that derive from that patient, the gene
                # symbol, HGNC ID, Classification, Associated conditions, ClinVar star-rating, and ClinVar review
                # status of those variants, to the 'query' string. The patient ID and HGVS genomic descriptions are
                # taken from the patient_variant table. The HGVS genomic descriptions of the variants are mapped to the
                # descriptions in the variant_annotations table, to find the additional information to append to the
                # patient ID and HGVS genomic descriptions in the table that will be returned to the User
                # through the UI.
                query = """
                SELECT
                    pv.patient_ID,
                    v.variant_NC,
                    v.variant_NM,
                    v.variant_NP,
                    v.gene,
                    v.HGNC_ID,
                    v.Classification,
                    v.Conditions,
                    v.Stars,
                    v.Review_status
                FROM patient_variant pv
                JOIN variant_annotations v
                  ON pv.variant = v.variant_NC
                WHERE pv.patient_ID = ?
                """
                # Use the query_db() function from database_functions.py to convert each entry returned by the sqlite3
                # query into dictionary format and assign the output to the 'data' variable.
                data = query_db(db_path, query, (patient_ID,))
                # Label this query by its type so that it is easily identifiable and callable later on.
                result_type = "patient"
                # If the patient query cannot be found in the selected database, the 'data' variable will remain as
                # None. In such a case, log a warning and notify the User that the patient could not be found in the
                # selected database, on the query page.
                if not data:
                    logger.warning(f'{patient_ID} could not be found in {db_name} database.')
                    flash(f'⚠ Patient Query Error: {patient_ID} could not be found in {db_name} database.')
                    return render_template("db_query_page.html", db_name=db_name)


            # If the User is performing a variant query...
            elif variant_nc:
                # Log that they are trying to retrieve the variant information.
                logger.info(f'User querying information about {variant_nc}...')
                # Use the get_mane_nc() function from vv_functions.py to convert ensembl, non-MANE select or gene symbol
                # gene descriptions into the HGVS genomic description. This is used to look up the variant in the
                # selected database.
                variant_search_term = get_mane_nc(variant_nc)
                # Assign the HGVS genomic description, HGVS transcript description, HGVS protein description, gene
                # symbol, HGNC ID, Classification, Associated conditions, ClinVar star-rating, and ClinVar review
                # status, to the 'query' string. The number of patients with the HGVS genomic description from the
                # get_mane_nc() function output, in the patient_variant table, is counted and
                # returned.
                query = """
                SELECT
                    v.variant_NC,
                    v.variant_NM,
                    v.variant_NP,
                    v.gene,
                    v.HGNC_ID,
                    v.Classification,
                    v.Conditions,
                    v.Stars,
                    v.Review_status,
                    COUNT(pv.patient_ID) AS Patient_Count
                FROM variant_annotations v
                LEFT JOIN patient_variant pv
                  ON v.variant_NC = pv.variant
                WHERE v.variant_NC = ?
                GROUP BY
                    v.variant_NC,
                    v.variant_NM,
                    v.variant_NP,
                    v.gene,
                    v.HGNC_ID,
                    v.Classification,
                    v.Conditions,
                    v.Stars,
                    v.Review_status
                """
                # Use the query_db() function from database_functions.py to convert each entry returned by the
                # sqlite3 query into dictionary format and assign the output to the 'data' variable.
                data = query_db(db_path, query, (variant_search_term,))
                # Label this query by its type so that it is easily identifiable and callable later on.
                result_type = "variant_NC"

            # If the User is performing a gene query...
            elif gene:
                # Log that they are trying to retrieve information about variants that derive from the gene that they
                # are querying.
                logger.info(f'User querying information about variants from {gene}...')
                # Look for the gene symbol in the variant_annotations table of the selected database and retrieve the
                # associated HGNC ID.
                # *** CURRENTLY THE HGNC ID IS FOUND IF THE GENE SYMBOL EXISTS IN THE DATABASE.THE GENE SYMBOL SHOULD
                # HAVE BEEN RUN THROUGH VARIANTVALIDATOR (VV) TO FIND THE HGNC ID. THE HGNC ID FROM VV SHOULD HAVE BEEN
                # USED TO FIND THE ROW. THIS CODE WON'T RETURN THE VARIANTS THAT DERIVE FROM A GENE WITH THE SAME HGNC
                # ID BUT WITH DIFFERENT GENE SYMBOL TO THE QUERIED GENE.***
                lookup_query = (
                    "SELECT DISTINCT HGNC_ID FROM variant_annotations WHERE gene = ?"
                )
                # Assign the row with the corresponding HGNC ID to the variable, 'hgnc_row'
                hgnc_row = query_db(db_path, lookup_query, (gene,), one=True)

                # If the gene symbol was found and a corresponding HGNC ID was retrieved...
                if hgnc_row:
                    # Parse the HGNC ID out of the row.
                    hgnc_id = hgnc_row["HGNC_ID"]
                    # Assign the HGVS genomic descriptions, HGVS transcript descriptions and the HGVS protein
                    # descriptions of the variants that derived from the queried gene, the gene symbol, HGNC ID,
                    # Classification, Associated conditions, ClinVar star-rating, and ClinVar review status, to the
                    # 'query' string. The number of patients with the HGVS genomic descriptions of the variants
                    # returned by the query, in the patient_variant table, are also counted and returned.
                    query = """
                    SELECT
                        v.variant_NC,
                        v.variant_NM,
                        v.variant_NP,
                        v.gene,
                        v.HGNC_ID,
                        v.Classification,
                        v.Conditions,
                        v.Stars,
                        v.Review_status,
                        COUNT(pv.patient_ID) AS Patient_Count
                    FROM variant_annotations v
                    LEFT JOIN patient_variant pv
                      ON v.variant_NC = pv.variant
                    WHERE v.HGNC_ID = ?
                    GROUP BY
                        v.variant_NC,
                        v.variant_NM,
                        v.variant_NP,
                        v.gene,
                        v.HGNC_ID,
                        v.Classification,
                        v.Conditions,
                        v.Stars,
                        v.Review_status
                    ORDER BY Patient_Count DESC
                    """
                    # Use the query_db() function from database_functions.py to convert each entry returned by the
                    # sqlite3 query into dictionary format and assign the output to the 'data' variable.
                    data = query_db(db_path, query, (hgnc_id,))
                    # Label this query by its type so that it is easily identifiable and callable later on.
                    result_type = "gene"
                # If the gene symbol could not be found in the database, a warning message is logged and an error
                # message is returned, indicating that the gene symbol could not be found.
                else:
                    logger.warning(f"User's gene query could not be found: {gene}")
                    flash(f"{gene}: ⚠ Gene Query Error: gene symbol could not be found.")
                    return render_template("db_query_page.html", db_name=db_name)

        # Error handler executed when exceptions related to sqlite3 are raised.
        except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
            # sqlite_error function logs the errors appropriately and returns an error message which can be implemented
            # into a flash message, on the query page.
            error_message = sqlite_error(e, db_name)
            flash(f'❌ {db_name} Query Error: {error_message}')
            return render_template("db_query_page.html", db_name=db_name)

        # Raise an exception if the there was an issue querying clinvar.db.
        except Exception as e:
            # Log the error, describing why the selected database could not be queried, using the exception output.
            logger.error(f'Database Query Error: Failed to prepare {db_name} to be queried: {str(e)}')
            # Return a flash message to the User, notifying them of the error, on the query page.
            flash(f'❌ {db_name} Query Error: Failed to prepare {db_name} to be queried: {str(e)}')
            return render_template("db_query_page.html", db_name=db_name)

    # Prepare JSON to export query results into a table that can be viewed by the User through the user interface.
    try:
        export_columns_json = "[]"
        export_rows_json = "[]"
        if data:
            cols = list(data[0].keys())
            rows_for_export = [[row[c] for c in cols] for row in data]
            export_columns_json = json.dumps(cols)
            export_rows_json = json.dumps(rows_for_export)

    # Raise an exception if the 'data' variable remained as None.
    except TypeError as e:
        # Log the TypeError.
        logger.error(f"Query TypeError: 'data' variable remained as None: {e}")
        # Return a flash message to help the User understand why they have not received the expected response, on the
        # query page.
        flash(f'❌ Query Error: An error occurred while processing the query. It is not your fault. '
              f'Please contact your nearest friendly neighbourhood Bioinformatician')
        return render_template("db_query_page.html", db_name=db_name)

    # Raise an exception if the keys in the 'data' are not iterable (specific to 'cols' variable).
    except IndexError as e:
        # Log the IndexError.
        logger.error(f"Query IndexError: 'data' variable is not iterable: {e}")
        # Return a flash message to help the User understand why they have not received the expected response, on the
        # query page.
        flash(f'❌ Query Error: An error occurred while processing the query. It is not your fault. '
              f'Please contact your nearest friendly neighbourhood Bioinformatician')
        return render_template("db_query_page.html", db_name=db_name)

    # Raise an exception if any of the keys in 'data' are missing.
    except KeyError as e:
        # KeyError message contains the missing key (from ChatGPT).
        missing_key = e.args[0]
        # Log the KeyError.
        logger.error(f"Query KeyError: The {missing_key} key is missing from 'data'. "
                     f"Variant info could not be parsed from {db_name}. {e}")
        # Return a flash message to help the User understand why they have not received the expected response, on the
        # query page.
        flash(f'❌ Query Error: An error occurred while processing the query. It is not your fault. '
              f'Please contact your nearest friendly neighbourhood Bioinformatician')
        return render_template("db_query_page.html", db_name=db_name)

    # Raise an exception if an error occurs while extracting information from 'data'.
    except Exception as e:
        # Log the error using the exception output message.
        logger.error(f'Query Error: An error occurred while extracting the information from the {db_name} database: '
                     f'{e}')
        # Log the value assigned to the 'data' variable, to help with debugging.
        logger.debug(f'Query Error: data:\n{json.dumps(data, indent=4)}')
        # Return a flash message to help the User understand why they have not received the expected response, on the
        # query page.
        flash(f'❌ Query Error: An error occurred while processing the query. It is not your fault. '
              f'Please contact your nearest friendly neighbourhood Bioinformatician')
        return render_template("db_display_page.html", db_name=db_name)

    # Render the information extracted from 'data' into a table that is viewable on the query page.
    return render_template(
        "db_query_page.html",
        db_name=db_name,
        databases=databases,
        data=data,
        result_type=result_type,
        patient_list=patient_list,
        variant_list=variant_list,
        gene_list=gene_list,
        export_columns_json=export_columns_json,
        export_rows_json=export_rows_json,
    )


# ---------------------------------------------------------------
# Route: DISPLAY ALL - one big table (patients × variants)
# ---------------------------------------------------------------
@app.route("/display/<db_name>", methods=["GET", "POST"])
def display_database(db_name):
    """
    This function combines the patient_variant and variant_annotations tables from the database selected by the User
    to display a single table containing the patient IDs, the HGVS genomic, transcript and protein consequence
    descriptions, gene symbols, HGNC IDs, ClinVar variant classifications, associated conditions, ClinVar star-ratings,
    and ClinVar Review statuses. The table is displayed on the display webpage.

    Filter options are also available on the display page, which enable the User to select a column in the table
    to filter by, values in the column to filter by and another column to sort by. Each filter and sorting option is
    selected from three dropdown menus.

    :param db_name: The name of the database being queried.
              E.g.: sea.db

    :filter/sort by options:    Filter By: The column which contains the values to filter-into the table, named after
                                           the header of the respective column.
                                     E.g.: Classification

                             Filter Value: All the values under the selected column to filter by. If a column to filter
                                           by has not been selected, the only option in this column will be 'none'.
                                     E.g.: Pathogenic

                                  Sort By: The column with the values that you want to sort by. Values are sorted in
                                           ascending value.
                                     E.g.: patient_ID

    :output: Table: A table consisting of all the variants successfully uploaded into the database, Each variant
                    constitutes a row in the table which comprises of the Patient ID; HGVS genomic description; HGVS
                    transcript description; HGVS protein consequence description; gene symbol; HGNC ID; Classification;
                    Associated conditions; ClinVar star-rating; ClinVar review status.

              E.g.:  patient_ID | variant_NC	| variant_NM   | variant_NP	   | gene   | HGNC_ID | Classification | Conditions	                 | Stars | Review_status
                    ------------|---------------|--------------|---------------|--------|---------|----------------|-----------------------------|-------|-------------------
                     Patient1   | NC_000019.10: | NM_152296.5: | NP_689509.1:  | ATP1A3 | 801     | Pathogenic     | Dystonia 12                 | ★    | criteria provided,
                                | g.41968837C>G | c.2767G>C    | p.(Asp923His) |        |         |                |                             | 	     | single submitter
                    ------------|---------------|--------------|---------------|--------|---------|----------------|-----------------------------|-------|-------------------
                     Patient2	| NC_000019.10:	| NM_152296.5: | NP_689509.1:  | ATP1A3	| 801	  | Pathogenic	   | Developmental and epileptic | 0★	 | no assertion
                                | g.41985036A>C | c.875T>G	   | p.(Leu292Arg) |        |         |                |  encephalopathy 99          |       | criteria provided
    """
    # Log that the display page is being used.
    logger.info('User has accessed the Query page.')

    # Check that the filepath to the database file that was selected or uploaded on the homepage exists.
    # Assign the filepath to the selected databse to 'db_path' variable.
    db_path = os.path.join(app.config["db_upload_folder"], db_name)
    # If the filepath to the database file does not exist...
    if not os.path.exists(db_path):
        # ...Log a warning that the database does not exist.
        logger.warning(f"{db_name} database could not be found in: {db_path}")
        # Notify the User that the database was not found in the database folder.
        flash(f"⚠ {db_name} database not found. Please select a database to query on the homepage.")
        # Redirect the User back to the homepage.
        return redirect(url_for("choose_create_or_add"))

    # A list of the column headers that are shown to the User.
    all_columns = [
        "patient_ID",
        "variant_NC",
        "variant_NM",
        "variant_NP",
        "gene",
        "HGNC_ID",
        "Classification",
        "Conditions",
        "Stars",
        "Review_status",
    ]

    # Check that the filter queries work.
    try:
        # Retrieve the filter-in column, filter-in value and column to sort by, that the User selected on the display page.
        filter_column = request.form.get("filter_column") or ""
        filter_value = request.form.get("filter_value") or ""
        sort_column = request.form.get("sort_column") or ""

        # Assign the HGVS genomic descriptions, HGVS transcript descriptions and the HGVS protein descriptions of the
        # variants in the database, the gene symbol, HGNC ID, Classification, Associated conditions, ClinVar star-rating,
        # and ClinVar review status, to the 'base_query' string.
        base_query = """
        SELECT
            pv.patient_ID,
            v.variant_NC,
            v.variant_NM,
            v.variant_NP,
            v.gene,
            v.HGNC_ID,
            v.Classification,
            v.Conditions,
            v.Stars,
            v.Review_status
        FROM patient_variant pv
        JOIN variant_annotations v
          ON pv.variant = v.variant_NC
        """

        # Create an empty list to store the column header that the User wants to filter by.
        where_clauses = []
        # Create an empty list to store the value that the User wants to filter by.
        params = []

        # If a column and value was chosen by the User...
        if filter_column and filter_value:
            # Add the column to the 'where_clauses' list with additional sqlite3 syntax so that it is easily integrated
            # within the sqlite query code.
            where_clauses.append(f"{filter_column} = ?")
            # Add the value to the 'params' list.
            params.append(filter_value)
            # Log which column and value the user wants to filter by.
            logger.info(f"User wants to filter by '{filter_column}': '{filter_value}'.")


        # Assign the original query to a new query where the filters and sort by values can be applied.
        query = base_query
        # Apply the filter column to the sqlite3 query with additional syntax to make it logical in the code.
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        # If the User selected a column to sort by apply it to the sqlite3 query with additional syntax to make it logical
        # in the code.
        if sort_column:
            query += f" ORDER BY {sort_column}"
            # Log which column the User wants to sort by.
            logger.info(f"User wants to sort by '{sort_column}'.")

        # Convert each entry returned from the sqlite3 query into a dictionary using the query_db() function from the
        # database_functions.py script and assign it to the 'data' variable.
        data = query_db(db_path, query, tuple(params))

        # Build a dictionary of filter values that the User can view in the dropdown menu, after selecting a column to
        # filter by.
        filter_values = {}
        # Connect to the User-selected database using the absolute path to it.
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            # Iterate through each column header in the 'all_columns' list.
            for col in all_columns:
                # Retrieve each distinct value under each column header.
                cur.execute(
                    f"""
                    SELECT DISTINCT {col}
                    FROM patient_variant pv
                    JOIN variant_annotations v
                      ON pv.variant = v.variant_NC
                    WHERE {col} IS NOT NULL
                    ORDER BY {col}
                    """
                )
                # Assign the filter value to the 'val' variable.
                vals = [r[0] for r in cur.fetchall()]
                # Add the filter value to a keyword in the 'filter_values' dictionary, named after the corresponding column
                # header.
                filter_values[col] = vals

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately and returns an error message which can be implemented
        # into a flash message, on the display page.
        error_message = sqlite_error(e, db_name)
        flash(f'❌ {db_name} Filter Error: {error_message}')
        return render_template("db_display_page.html", db_name=db_name)

    # Raise an exception if there was an issue filtering the selected database.
    except Exception as e:
        # Log the error, describing why the selected database could not be filtered, using the exception output.
        logger.error(f'Database Filter Error: Failed to prepare {db_name} to be filtered: {str(e)}')
        # Return a flash message to the User, notifying them of the error, on the display page.
        flash(f'❌ {db_name} Filter Error: Failed to prepare {db_name} to be filtered: {str(e)}')
        return render_template("db_display_page.html", db_name=db_name)

    # 'filter_values' dictionary converted into a JSON.
    filter_values_json = json.dumps(filter_values)

    # Prepare JSON to export query results into a table that can be viewed by the User through the user interface.
    try:
        export_columns_json = "[]"
        export_rows_json = "[]"
        if data:
            cols = all_columns[:]  # fixed order
            rows_for_export = [[row[c] for c in cols] for row in data]
            export_columns_json = json.dumps(cols)
            export_rows_json = json.dumps(rows_for_export)

    # Raise an exception if the 'data' variable is None.
    except TypeError as e:
        # Log the TypeError.
        logger.error(f"Filter TypeError: No data was returned to the 'data' variable: {e}")
        # Return a flash message to help the User understand why they have not received the expected response, on the
        # display page.
        flash(f'❌ Filter Error: An error occurred while processing the query. It is not your fault. '
              f'Please contact your nearest friendly neighbourhood Bioinformatician')
        return render_template("db_display_page.html", db_name=db_name)

    # Raise an exception if the keys in the 'data' are not iterable (specific to 'cols' variable).
    except IndexError as e:
        # Log the IndexError.
        logger.error(f"Filter IndexError: 'data' variable is not iterable: {e}")
        # Return a flash message to help the User understand why they have not received the expected response, on the
        # display page.
        flash(f'❌ Filter Error: An error occurred while processing the query. It is not your fault. '
              f'Please contact your nearest friendly neighbourhood Bioinformatician')
        return render_template("db_display_page.html", db_name=db_name)

    # Raise an exception if any of the keys in 'data' are missing.
    except KeyError as e:
        # KeyError message contains the missing key (from ChatGPT).
        missing_key = e.args[0]
        # Log the KeyError.
        logger.error(f"Filter KeyError: The {missing_key} key is missing from 'data'. "
                     f"Variant info could not be parsed from {db_name}. {e}")
        # Return a flash message to help the User understand why they have not received the expected response, on the
        # display page.
        flash(f'❌ Filter Error: An error occurred while processing the query. It is not your fault. '
              f'Please contact your nearest friendly neighbourhood Bioinformatician')
        return render_template("db_display_page.html", db_name=db_name)

    # Raise an exception if an error occurs while extracting information from 'data'.
    except Exception as e:
        # Log the error using the exception output message.
        logger.error(f'Filter Error: An error occurred while extracting the information from the {db_name} database: '
                     f'{e}')
        # Log the value assigned to the 'data' variable, to help with debugging.
        logger.debug(f'Filter Error: data:\n{json.dumps(data, indent=4)}')
        # Return a flash message to help the User understand why they have not received the expected response, on the
        # display page.
        flash(f'❌ Filter Error: An error occurred while processing the query. It is not your fault.'
              f'Please contact your nearest friendly neighbourhood Bioinformatician')
        return render_template("db_display_page.html", db_name=db_name)

    # Render the information extracted from 'data' into a table that is viewable on the query page.
    return render_template(
        "db_display_page.html",
        db_name=db_name,
        data=data,
        all_columns=all_columns,
        filter_values=filter_values,
        selected_filter_column=filter_column,
        selected_filter_value=filter_value,
        selected_sort_column=sort_column,
        filter_values_json=filter_values_json,
        export_columns_json=export_columns_json,
        export_rows_json=export_rows_json,
    )


# ---------------------------------------------------------------
# JSON API for dropdowns on query page (still available if needed)
# ---------------------------------------------------------------
@app.route("/api/dropdown/<db_name>")
def dropdown_data(db_name):
    """
    This function generates the values that the User can see in the patient, variant and gene query dropdown menus, on
    the query page. It does so by reading the database selected by the User on the homepage and extracting the unique
    values under the 'patient_ID' header in the patient_variant table; the variant_NC header in the variant_annotations
    table; and the gene header also in the variant_annotations table. It then returns a dictionary with all of these
    distinct values stored in their respective lists, in JSON format.

    :param: db_name: The name of the database selected by the User on the homepage.
               E.g.: 'sea.db'

    :output: Dictionary in JSON format with the following structure:
                    {"patients": patient_list, "variants": variant_list, "genes": gene_list}

               E.g.: {
                            "patients": [Patient1, Patient2, Patient3],
                            "variants": [NC_000019.10:g.41968837C>G,
                                         NC_000019.10:g.41985036A>C,
                                         NC_000017.11:g.44349216A>G],
                               "genes": [ATP1A3, GRN]
                     }
    """
    # Log that the dropdown menus are being generated for the query page.
    logger.debug('Generating dropdown menus for the query page...')

    # Check that the filepath to the database file that was selected or uploaded on the homepage exists.
    # Assign the filepath to the selected databse to 'db_path' variable.
    db_path = os.path.join(app.config["db_upload_folder"], db_name)
    # If the filepath to the database file does not exist...
    if not os.path.exists(db_path):
        # ...Log a warning that the database does not exist.
        logger.warning(f"{db_name} database could not be found in: {db_path}")
        # Notify the User that the database was not found in the database folder.
        flash(f"⚠ {db_name} database not found. Please select a database to query on the homepage.")
        # Redirect the User back to the homepage.
        return redirect(url_for("choose_create_or_add"))

    # Check that the information from the sqlite3 database can be accessed.
    try:
        # Connect to the database specified by the User using the absolute filepath.
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            # Extract the patient IDs (only once) from the patient_variant table and arrange them in ascending order.
            cur.execute(
                "SELECT DISTINCT patient_ID FROM patient_variant ORDER BY patient_ID ASC;"
            )
            # Store the patient IDs in a list and assign the list to the 'patient_list' variable.
            patient_list = [row[0] for row in cur.fetchall()]
            # Extract the HGVS genomic descriptions (only once) from the variant_annotations table and arrange them in
            # ascending order.
            cur.execute(
                "SELECT DISTINCT variant_NC FROM variant_annotations ORDER BY variant_NC ASC;"
            )
            # Store the HGVS genomic descriptions in a list and assign the list to the 'variant_list' variable.
            variant_list = [row[0] for row in cur.fetchall()]
            # Extract the gene symbols (only once) from the variant_annotations table and arrange them in ascending
            # order.
            cur.execute("SELECT DISTINCT gene FROM variant_annotations ORDER BY gene ASC;")
            # Store the gene symbols in a list and assign the list to the 'gene_list' variable.
            gene_list = [row[0] for row in cur.fetchall()]

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately and returns an error message which can be implemented
        # into a flash message, on the query page.
        error_message = sqlite_error(e, db_name)
        flash(f'❌ Dropdown Menu Error: {error_message}. Dropdown menus do not work.')
        return render_template("db_query_page.html", db_name=db_name)

    # Raise an exception if there was an error while trying to generate the dropdown menus.
    except Exception as e:
        # Log the error, describing why the selected database could not be filtered, using the exception output.
        logger.error(f'Dropdown Menu Error: Could not access {db_name} to generate dropdown menus: {str(e)}')
        # Return a flash message to the User, notifying them of the error, on the display page.
        flash(f'❌ Dropdown Menu Error: Dropdown menus do not work.')
        return render_template("db_query_page.html", db_name=db_name)

    # Return a JSON dictionary with a list of the Patient IDs, HGVS genomic descriptions and gene symbols.
    return jsonify(
        {"patients": patient_list, "variants": variant_list, "genes": gene_list}
    )


# ---------------------------------------------------------------
# Route: Switch database dropdown
# ---------------------------------------------------------------
@app.route("/switch_db", methods=["POST"])
def switch_db():
    """
    This functions redirects the User to a different /query/<db_name> query page when they select another database from
    the 'Select Database:' dropdown menu on the query page.
    """
    # Log that the User has selected a different database to query.
    logger.info('The User has selected a different database to query.')

    # Check that are no issues with switching databases.
    try:
        # Retrieve the name of the database that the User selected from the dropdown menu.
        db_name = request.form.get("db_name")
        if db_name:
            # Log which database the user wants to query.
            logger.info(f'The User has selected the {db_name} database to query. '
                        f'Redirected to http://127.0.0.1:5000/query/{db_name}')
            # Redirect the User to the query page for the database they selected.
            return redirect(url_for("query_page", db_name=db_name))

        # Log a warning if a database cannot be found.
        logger.warning(f"Database could not be found.")
        # Notify the User that the database was not found in the database folder.
        flash(f"⚠ {db_name} database not found. Please select a database to query on the homepage.")
        return redirect(url_for("homepage.html"))

    # Raise an exception if an error arose while selecting a different database to query.
    except Exception as e:
        # Log a warning using the error message from the exception output.
        logger.error(f'Failed to select a different database to query: {e}')
        # Notify the User that the attempt to switch databases failed.
        flash(f'❌ Failed to select a different database to query.')
        # Redirect the User to the homepage so that they can select or upload a database.
        return redirect(url_for("homepage.html"))


# ---------------------------------------------------------------
# EXPORT: CSV of current results
# ---------------------------------------------------------------
@app.route("/export_csv", methods=["POST"])
def export_csv():
    columns = json.loads(request.form["columns"])
    rows = json.loads(request.form["rows"])

        # Fix for Excel auto-formatting - this should stop excel converting numbers or genes
        # to dates 
    def excel_safe(value):
        if value is None:
            return ""
        value = str(value)

        # Prefix values Excel may auto-format
        if value.startswith(("=", "+", "-", "@", "*")):
            return "'" + value

        return value

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([excel_safe(v) for v in row])

    mem = io.BytesIO()
    # this should ensure that characters are properly coded so 
    # * is interpreted as * in the csv rather than being converted to letters
    mem.write("\ufeff".encode("utf-8"))  # UTF-8 BOM
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)

    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name="export.csv",
    )


# ---------------------------------------------------------------
# EXPORT: Excel of current results
# ---------------------------------------------------------------
@app.route("/export_excel", methods=["POST"])
def export_excel():
    columns = json.loads(request.form["columns"])
    rows = json.loads(request.form["rows"])

    wb = Workbook()
    ws = wb.active
    ws.append(columns)

    for r in rows:
        ws.append(r)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return send_file(
        stream,
        as_attachment=True,
        download_name="export.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)