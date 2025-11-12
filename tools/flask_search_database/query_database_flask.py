import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

EXPECTED_SCHEMA = {
    "patient_variant": {'No', 'patient_ID', 'variant'},
    "variant_annotations": {'No', 'variant', 'variant_NM', 'gene', 'HGNC_ID', 'Classification', 'Conditions', 'Stars', 'Review_status'},
}

def validate_database(db_path):
    """Check whether the uploaded database matches expected tables and columns."""
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()

            # Check tables
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cur.fetchall()}

            if not EXPECTED_SCHEMA.keys() <= tables:
                return False

            # Check columns for each table
            for table, expected_cols in EXPECTED_SCHEMA.items():
                cur.execute(f"PRAGMA table_info({table});")
                cols = {row[1] for row in cur.fetchall()}
                if not expected_cols <= cols:
                    return False
        return True
    except Exception:
        return False


def query_db(db_path, query, args=(), one=False):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv


@app.route("/", methods=["GET", "POST"])
def upload_db():
    """Allow user to upload and validate database."""
    if request.method == "POST":
        file = request.files.get("database_file")
        if not file:
            flash("No file selected.")
            return render_template("home_flask.html")

        filename = file.filename
        if not filename.endswith(".db"):
            flash("Please upload a .db SQLite file.")
            return render_template("home_flask.html")

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        if not validate_database(filepath):
            flash("❌ File is not a database in correct form.")
            os.remove(filepath)
            return render_template("home_flask.html")
        else:
            flash("✅ Database validated successfully.")
            return redirect(url_for("query_page", db_name=filename))

    return render_template("home_flask.html")


@app.route("/query/<db_name>", methods=["GET", "POST"])
def query_page(db_name):
    db_path = os.path.join(app.config["UPLOAD_FOLDER"], db_name)
    if not os.path.exists(db_path):
        flash("Database not found.")
        return redirect(url_for("upload_db"))

    data = None
    result_type = None

    if request.method == "POST":
        patient_ID = request.form.get("patient_ID")
        variant = request.form.get("variant")

        if patient_ID:
            query = """
            SELECT pv.variant, v.variant_NM, v.gene, v.HGNC_ID, v.Classification, 
            v.Conditions, v.Stars, v.Review_status
            FROM patient_variant pv
            JOIN variant_annotations v ON pv.variant = v.variant
            WHERE pv.patient_ID = ?
            """
            data = query_db(db_path, query, (patient_ID,))
            result_type = "patient"

        elif variant:
            query = """
            SELECT v.variant, v.variant_NM, v.gene, v.HGNC_ID, v.Classification, 
            v.Conditions, v.Stars, v.Review_status,COUNT(pv.patient_ID) as Patient_Count
            FROM variant_annotations v
            LEFT JOIN patient_variant pv ON v.variant = pv.variant
            WHERE v.variant = ?
            GROUP BY v.variant
            """
            data = query_db(db_path, query, (variant,))
            result_type = "variant"

    return render_template("query_flask.html", db_name=db_name, data=data, result_type=result_type)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004,debug=True)
