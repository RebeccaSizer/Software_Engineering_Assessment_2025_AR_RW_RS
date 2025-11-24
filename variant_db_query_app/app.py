import os
import sys
import io
import csv
import json
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

from tools.modules.database_functions import patient_variant_table, variant_annotations_table, validate_database, query_db
#from tools.modules.clinvar_functions import clinvar_vs_download

# ---------------------------------------------------------------
# Flask setup
# ---------------------------------------------------------------
app = Flask(__name__, template_folder='templates')
app.secret_key = 'supersecretkey'
#clinvar_vs_download()

# Get the filepath to the base directory.
base_dir = f'{os.path.dirname(os.path.abspath(__file__))}/../'
app.config['db_upload_folder'] = f'{base_dir}databases'
os.makedirs(app.config['db_upload_folder'], exist_ok=True)
app.config['variant_files_upload_folder'] = f'{base_dir}temp'
os.makedirs(app.config['variant_files_upload_folder'], exist_ok=True)


# ---------------------------------------------------------------
# Route: Home page - create, upload or select a database
# ---------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def choose_create_or_add():

    databases = []

    for f in os.listdir(app.config['db_upload_folder']):
        if f.endswith(".db"):
            databases.append(f)

    databases.sort()

    # Creating or adding to a database
    if request.method == 'POST':
        file = request.files.get('vcf')
        database_name = os.path.splitext(request.form["db_file"])[0]

        if not file:
            flash("No file uploaded")
            return render_template("Home_Template_Flask.html", databases=databases)

        if not file.filename.endswith('.vcf'):
            flash("❌ Invalid file type. Please upload a VCF file.")
            return render_template("Home_Template_Flask.html", databases=databases)

        # Save the file inside the uploads folder
        variant_file_path = os.path.join(app.config['variant_files_upload_folder'], file.filename)
        file.save(variant_file_path)

        # Get the absolute path for use in your scripts
        patient_variant_table(app.config['variant_files_upload_folder'], database_name)
        variant_annotations_table(app.config['variant_files_upload_folder'], database_name)
        os.remove(variant_file_path)

        flash(f"{file.filename} added to database.")
        return render_template("Home_Template_Flask.html", databases=databases)

    # Selecting existing database
    if request.form.get("existing_db"):
        selected_db = request.form.get("existing_db")
        return redirect(url_for("query_page", db_name=selected_db))

    # Uploading new database
    if request.method == "POST" and "database_file" in request.files:

        file = request.files.get("database_file")

        if not file or file.filename == "":
            flash("No file selected.")
            return render_template("Home_Template_Flask.html", databases=databases)

        filename = file.filename

        if not filename.endswith(".db"):
            flash("❌ Invalid file type. Please upload a .db file.")
            return render_template("Home_Template_Flask.html", databases=databases)

        filepath = os.path.join(app.config['db_upload_folder'], filename)
        file.save(filepath)

        if not validate_database(filepath):
            flash("❌ Inappropriate headers in database.")
            os.remove(filepath)
        else:
            flash("✅ Database uploaded and validated successfully.")
            return redirect(url_for("query_page", db_name=filename))

    return render_template("Home_Template_Flask.html", databases=databases)

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
        return redirect(url_for("upload_db"))

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
            data = query_db(db_path, query, (variant_nc,))
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
        "Database_Query_Flask.html",
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
    db_path = os.path.join(app.config["UPLOAD_FOLDER"], db_name)
    if not os.path.exists(db_path):
        flash("Database not found.")
        return redirect(url_for("upload_db"))

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
        "Display_All_Flask.html",
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
    db_path = os.path.join(app.config["UPLOAD_FOLDER"], db_name)
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
    return redirect(url_for("upload_db"))


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
    app.run(host='127.0.0.1', port=5000)