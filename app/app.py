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
            logger.info(f"Starting to load variant files in 'temp' folder, into {database_name} database.")
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
    """Main query interface for a specific database."""
    # Get list of uploaded databases
    databases = [
        f for f in os.listdir(app.config["db_upload_folder"]) if f.endswith(".db")
    ]
    databases.sort()

    db_path = os.path.join(app.config["db_upload_folder"], db_name)
    if not os.path.exists(db_path):
        flash("Database not found.")
        return redirect(url_for("homepage.html"))

    data = None
    result_type = None

    # Load dropdown values (from annotations / patients)
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT patient_ID FROM patient_variant ORDER BY patient_ID ASC;"
        )
        patient_list = [row[0] for row in cur.fetchall()]

        cur.execute(
            "SELECT DISTINCT variant_NC FROM variant_annotations ORDER BY variant_NC ASC;"
        )
        variant_list = [row[0] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT gene FROM variant_annotations ORDER BY gene ASC;")
        gene_list = [row[0] for row in cur.fetchall()]

    # Handle search submission
    if request.method == "POST":
        patient_ID = request.form.get("patient_ID")
        variant_nc = request.form.get("variant_NC")
        variant_search_term = get_mane_nc(variant_nc)
        gene = request.form.get("gene")

        if patient_ID:
            # Join on pv.variant = v.variant_NC, but show only variant_NC
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
            data = query_db(db_path, query, (patient_ID,))
            result_type = "patient"

        elif variant_nc:
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
            data = query_db(db_path, query, (variant_search_term,))
            result_type = "variant_NC"

        elif gene:
            lookup_query = (
                "SELECT DISTINCT HGNC_ID FROM variant_annotations WHERE gene = ?"
            )
            hgnc_row = query_db(db_path, lookup_query, (gene,), one=True)

            if hgnc_row:
                hgnc_id = hgnc_row["HGNC_ID"]
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
                data = query_db(db_path, query, (hgnc_id,))
                result_type = "gene"
            else:
                flash(f"No HGNC_ID found for gene '{gene}'.")
                data = None

    # Prepare export JSON for query results
    export_columns_json = "[]"
    export_rows_json = "[]"
    if data:
        cols = list(data[0].keys())
        rows_for_export = [[row[c] for c in cols] for row in data]
        export_columns_json = json.dumps(cols)
        export_rows_json = json.dumps(rows_for_export)

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
    Display one giant joined table:
    patient_ID + all variant annotation fields,
    with optional sort & filter, plus export.
    """
    db_path = os.path.join(app.config["db_upload_folder"], db_name)
    if not os.path.exists(db_path):
        flash("Database not found.")
        return redirect(url_for("homepage.html"))

    # Columns we show (no duplicate 'variant', we show variant_NC)
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

    # Read filter / sort from form
    filter_column = request.form.get("filter_column") or ""
    filter_value = request.form.get("filter_value") or ""
    sort_column = request.form.get("sort_column") or ""

    # Build base query (join patient_variant + variant_annotations)
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

    where_clauses = []
    params = []

    # Apply filter if provided
    if filter_column and filter_value:
        where_clauses.append(f"{filter_column} = ?")
        params.append(filter_value)

    query = base_query
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # Apply sort if provided
    if sort_column:
        query += f" ORDER BY {sort_column}"

    # Get data for table
    data = query_db(db_path, query, tuple(params))

    # Build filter value lists for each column
    filter_values = {}
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        for col in all_columns:
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
            vals = [r[0] for r in cur.fetchall()]
            filter_values[col] = vals

    # JSON for JS dynamic dropdown
    filter_values_json = json.dumps(filter_values)

    # Prepare export JSON
    export_columns_json = "[]"
    export_rows_json = "[]"
    if data:
        cols = all_columns[:]  # fixed order
        rows_for_export = [[row[c] for c in cols] for row in data]
        export_columns_json = json.dumps(cols)
        export_rows_json = json.dumps(rows_for_export)

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
    """Return JSON lists of patients, variants, and genes for the current database."""
    db_path = os.path.join(app.config["db_upload_folder"], db_name)
    if not os.path.exists(db_path):
        return jsonify({"error": "Database not found"}), 404

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT patient_ID FROM patient_variant ORDER BY patient_ID ASC;"
        )
        patient_list = [row[0] for row in cur.fetchall()]

        cur.execute(
            "SELECT DISTINCT variant_NC FROM variant_annotations ORDER BY variant_NC ASC;"
        )
        variant_list = [row[0] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT gene FROM variant_annotations ORDER BY gene ASC;")
        gene_list = [row[0] for row in cur.fetchall()]

    return jsonify(
        {"patients": patient_list, "variants": variant_list, "genes": gene_list}
    )


# ---------------------------------------------------------------
# Route: Switch database dropdown
# ---------------------------------------------------------------
@app.route("/switch_db", methods=["POST"])
def switch_db():
    """Redirect to a different /query/<db_name> when user selects another database."""
    db_name = request.form.get("db_name")
    if db_name:
        return redirect(url_for("query_page", db_name=db_name))
    flash("No database selected.")
    return redirect(url_for("homepage.html"))


# ---------------------------------------------------------------
# EXPORT: CSV of current results
# ---------------------------------------------------------------
@app.route("/export_csv", methods=["POST"])
def export_csv():
    columns = json.loads(request.form["columns"])
    rows = json.loads(request.form["rows"])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for r in rows:
        writer.writerow(r)

    mem = io.BytesIO()
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