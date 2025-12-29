# these tests were written by ChatGPT and refined by the developer
# test_db_tools.py
import os
import sqlite3
import pytest
from pathlib import Path
from flask import Flask, get_flashed_messages
from unittest.mock import patch
import tools.modules.database_functions as db_mod

# -------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------


@pytest.fixture
def app():
    """Minimal Flask app for capturing flash messages."""
    app = Flask(__name__)
    app.secret_key = "test-secret"
    return app


@pytest.fixture
def temp_variants_dir(tmp_path):
    """Temporary directory that will act as the 'temp' upload folder."""
    d = tmp_path / "temp"
    d.mkdir()
    return d


@pytest.fixture
def db_name():
    """Database name WITHOUT the .db suffix (functions add .db themselves)."""
    return "test_db"


@pytest.fixture
def db_path(db_name):
    """
    Compute the DB path exactly the same way as in the module under test.
    This mirrors:

        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.path.join(script_dir, '..', '..', 'databases', f'{db_name}.db')
    """
    script_dir = os.path.dirname(os.path.abspath(db_mod.__file__))
    return os.path.abspath(
        os.path.join(script_dir, "..", "..", "databases", f"{db_name}.db")
    )


# -------------------------------------------------------------------------
# Unit tests: validate_database & query_db (no Flask / external services)
# -------------------------------------------------------------------------


def test_validate_database_true(tmp_path):
    """
    Test that `validate_database` returns True when the database schema 
    matches the EXPECTED_SCHEMA.

    This test creates a temporary SQLite database with the correct tables
    and columns for `patient_variant` and `variant_annotations`. After 
    creating the schema, it verifies that `validate_database` returns True.
    
    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary path provided by pytest for creating test files.
    """
    # Create a temporary database file
    db_file = tmp_path / "valid.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Create the patient_variant table with the expected schema
    cur.execute(
        """
        CREATE TABLE patient_variant (
            No INTEGER PRIMARY KEY,
            patient_ID TEXT NOT NULL,
            variant TEXT NOT NULL
        )
        """
    )

    # Create the variant_annotations table with the expected schema
    cur.execute(
        """
        CREATE TABLE variant_annotations (
            No INTEGER PRIMARY KEY,
            variant_NC TEXT NOT NULL,
            variant_NM TEXT NOT NULL,
            variant_NP TEXT NOT NULL,
            gene TEXT NOT NULL,
            HGNC_ID INTEGER NOT NULL,
            Classification TEXT NOT NULL,
            Conditions TEXT NOT NULL,
            Stars TEXT,
            Review_status TEXT NOT NULL
        )
        """
    )

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # Assert that validate_database returns True for the valid schema
    assert db_mod.validate_database(str(db_file)) is True




def test_validate_database_missing_table(tmp_path):
    """
    Test that `validate_database` returns False when the database is missing 
    a required table.

    This test creates a temporary SQLite database containing only the 
    `patient_variant` table, leaving out the `variant_annotations` table.
    It then verifies that `validate_database` correctly returns False.
    
    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary path provided by pytest for creating test files.
    """
    # Create a temporary database file
    db_file = tmp_path / "invalid.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Create only the patient_variant table (variant_annotations is missing)
    cur.execute(
        """
        CREATE TABLE patient_variant (
            No INTEGER PRIMARY KEY,
            patient_ID TEXT NOT NULL,
            variant TEXT NOT NULL
        )
        """
    )

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    # Patch Flask's flash function to avoid requiring Flask context
    with patch("tools.modules.database_functions.flash"):
        # Assert that validate_database returns False for missing table
        assert db_mod.validate_database(str(db_file)) is False


def test_validate_database_missing_column(tmp_path):
    """
    Test that `validate_database` returns False when a required column 
    is missing from a table.

    This test creates a temporary SQLite database with the `patient_variant` 
    table but intentionally omits the 'variant' column. It verifies that 
    `validate_database` detects the schema mismatch and returns False.
    
    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary path provided by pytest for creating test files.
    """
    # Create a temporary database file
    db_file = tmp_path / "invalid_cols.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Create patient_variant table missing the 'variant' column
    cur.execute(
        """
        CREATE TABLE patient_variant (
            No INTEGER PRIMARY KEY,
            patient_ID TEXT NOT NULL
        )
        """
    )

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    # Patch Flask's flash function to avoid requiring a Flask context
    with patch("tools.modules.database_functions.flash"):
        # Assert that validate_database returns False for missing column
        assert db_mod.validate_database(str(db_file)) is False


def test_query_db_returns_all_rows(tmp_path):
    """
    Test that `query_db` returns all rows as a list of sqlite3.Row objects 
    when `one=False` (the default).

    This test creates a temporary SQLite database with a table `t` containing 
    two rows. It queries all rows using `query_db` and verifies that the 
    results match the inserted data.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary path provided by pytest for creating test files.
    """
    # Create a temporary database file
    db_file = tmp_path / "q.db"
    conn = sqlite3.connect(db_file)

    # Create table 't' with id and name columns
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")

    # Insert two rows into the table
    conn.execute("INSERT INTO t (name) VALUES (?)", ("Alice",))
    conn.execute("INSERT INTO t (name) VALUES (?)", ("Bob",))

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    # Query all rows using query_db
    rows = db_mod.query_db(str(db_file), "SELECT * FROM t ORDER BY id")

    # Assert that two rows are returned
    assert len(rows) == 2

    # Assert that the row contents match the inserted data
    assert rows[0]["name"] == "Alice"
    assert rows[1]["name"] == "Bob"

def test_query_db_returns_one_row(tmp_path):
    """
    Test that `query_db` returns a single sqlite3.Row when `one=True`.

    This test creates a temporary SQLite database with a table `t` containing 
    one row. It verifies that `query_db` returns the row when queried with 
    `one=True`, and returns None when no matching rows exist.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary path provided by pytest for creating test files.
    """
    # Create a temporary database file
    db_file = tmp_path / "q_one.db"
    conn = sqlite3.connect(db_file)

    # Create table 't' with id and name columns
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")

    # Insert a single row into the table
    conn.execute("INSERT INTO t (name) VALUES (?)", ("Alice",))

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    # Query the row using query_db with one=True
    row = db_mod.query_db(str(db_file), "SELECT * FROM t", one=True)

    # Assert that a row is returned and has the correct data
    assert row is not None
    assert row["name"] == "Alice"

    # Query a non-existent row; one=True should return None
    row = db_mod.query_db(str(db_file), "SELECT * FROM t WHERE name='Bob'", one=True)
    assert row is None


# -------------------------------------------------------------------------
# Unit-ish tests for patient_variant_table: behaviour with empty folder
# -------------------------------------------------------------------------


def test_patient_variant_table_no_files_logs_warning(app, temp_variants_dir, db_name, db_path, caplog):
    """
    Test that `patient_variant_table` logs a warning when no VCF/CSV files 
    are detected in the variants directory.

    This test removes the database if it exists, then calls 
    `patient_variant_table` in a Flask test request context. It verifies 
    that a warning message is logged when no files are present.

    Parameters
    ----------
    app : Flask
        Flask application fixture for creating a test request context.
    temp_variants_dir : pathlib.Path
        Temporary directory used for storing variant files (empty in this test).
    db_name : str
        Name of the database file to be created.
    db_path : pathlib.Path
        Path to the database file.
    caplog : pytest.CaptureFixture
        Pytest fixture for capturing log messages.
    """
    # Remove the database file if it already exists
    if os.path.exists(db_path):
        os.remove(db_path)

    # Run patient_variant_table inside a Flask test request context
    with app.test_request_context("/"):
        # Capture log messages at WARNING level
        with caplog.at_level("WARNING"):
            db_mod.patient_variant_table(str(temp_variants_dir), db_name)

    # Assert that the expected warning was logged
    assert any(
        "No VCF/CSV files detected" in record.message 
        for record in caplog.records
    )

# -------------------------------------------------------------------------
# Unit-ish tests for patient_variant_table: happy path with mocks
# -------------------------------------------------------------------------


def test_patient_variant_table_inserts_variants(app, temp_variants_dir, db_name, db_path, monkeypatch):
    """
    Test that `patient_variant_table` inserts (patient_ID, variant) rows 
    into the patient_variant table when a VCF file is present.

    This test creates a dummy VCF file and uses monkeypatching to mock 
    `variant_parser` and `fetch_vv` functions to return controlled outputs. 
    It also mocks `time.sleep` to speed up the test. After running 
    `patient_variant_table`, it verifies that no error flashes were triggered 
    and that the database contains the expected rows.

    Parameters
    ----------
    app : Flask
        Flask application fixture for creating a test request context.
    temp_variants_dir : pathlib.Path
        Temporary directory used for storing variant files.
    db_name : str
        Name of the database file to be created.
    db_path : pathlib.Path
        Path to the database file.
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture for mocking functions.
    """
    # Create a dummy VCF file in the temporary variants directory
    vcf_file = temp_variants_dir / "Patient1.vcf"
    vcf_file.write_text("## dummy content\n")

    # Mock variant_parser(path) to return a list of variants
    def fake_variant_parser(path):
        assert str(vcf_file) == path
        return ["varA", "varB"]

    monkeypatch.setattr(db_mod, "variant_parser", fake_variant_parser)

    # Mock fetch_vv(variant) to return expected variant details
    def fake_fetch_vv(variant):
        if variant == "varA":
            return ("NC_000001.1:g.1A>G", "NM_dummy", "NP_dummy", "GENE1", 1111)
        elif variant == "varB":
            return ("NC_000002.1:g.2C>T", "NM_dummy2", "NP_dummy2", "GENE2", 2222)
        else:
            raise AssertionError("Unexpected variant")

    monkeypatch.setattr(db_mod, "fetch_vv", fake_fetch_vv)

    # Mock time.sleep to avoid slowing down the test
    monkeypatch.setattr(db_mod.time, "sleep", lambda *_: None)

    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    # Run patient_variant_table inside a Flask test request context
    with app.test_request_context("/"):
        db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Ensure no error flashes about VariantValidator occurred
    assert not any("VariantValidator" in m for m in messages)

    # Verify the patient_variant table contains the expected rows
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT patient_ID, variant FROM patient_variant ORDER BY No;")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0] == ("Patient1", "NC_000001.1:g.1A>G")
    assert rows[1] == ("Patient1", "NC_000002.1:g.2C>T")

# -------------------------------------------------------------------------
# Unit-ish tests for variant_annotations_table
# -------------------------------------------------------------------------


def test_variant_annotations_table_no_files_flashes_and_returns(app, temp_variants_dir, db_name, db_path):
    """
    Test that `variant_annotations_table` flashes a warning and returns 
    early when no variant files are present.

    This test ensures that if the variants directory is empty, the function:
    - flashes a warning message to the user, and
    - returns without raising an exception (the database may not be created).

    Parameters
    ----------
    app : Flask
        Flask application fixture for creating a test request context.
    temp_variants_dir : pathlib.Path
        Temporary directory used for storing variant files (empty for this test).
    db_name : str
        Name of the database file.
    db_path : pathlib.Path
        Path to the database file.
    """
    # Remove the database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    # Run variant_annotations_table inside a Flask test request context
    with app.test_request_context("/"):
        db_mod.variant_annotations_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Assert that the expected warning message was flashed
    assert any("No data files have been uploaded" in m for m in messages)

    # Database existence is optional since the function returns early
    # The test ensures no exceptions are raised


def test_variant_annotations_table_inserts_annotations(
    app, temp_variants_dir, db_name, db_path, monkeypatch
):
    """
    Test that `variant_annotations_table` inserts annotation data into 
    the `variant_annotations` table when a VCF file is present.

    This test:
    - Creates a dummy VCF file.
    - Mocks `variant_parser`, `fetch_vv`, and `clinvar_annotations` to 
      return controlled outputs.
    - Mocks `time.sleep` to avoid delays.
    - Prepares a database with the required tables.
    - Runs `variant_annotations_table` inside a Flask test request context.
    - Checks that the table contains the expected rows and that a success 
      flash message is emitted.

    Parameters
    ----------
    app : Flask
        Flask application fixture for creating a test request context.
    temp_variants_dir : pathlib.Path
        Temporary directory used for storing variant files.
    db_name : str
        Name of the database file.
    db_path : pathlib.Path
        Path to the database file.
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture for mocking functions.
    """
    # Create a dummy VCF file
    vcf_file = temp_variants_dir / "PatientX.vcf"
    vcf_file.write_text("## dummy content\n")

    # Mock variant_parser to return a single variant
    monkeypatch.setattr(db_mod, "variant_parser", lambda path: ["c.123A>G"])

    # Mock fetch_vv to return controlled variant details
    monkeypatch.setattr(
        db_mod,
        "fetch_vv",
        lambda v: (
            "NC_000003.1:g.123A>G",
            "NM_000003.1:c.123A>G",
            "NP_000003.1:p.(Lys41Arg)",
            "GENE3",
            3333,
        ),
    )

    # Mock clinvar_annotations to return controlled annotation data
    monkeypatch.setattr(
        db_mod,
        "clinvar_annotations",
        lambda nc, nm: {
            "classification": "Pathogenic",
            "conditions": "Some condition",
            "stars": "★★",
            "reviewstatus": "criteria provided, multiple submitters, no conflicts",
        },
    )

    # Mock time.sleep to speed up test execution
    monkeypatch.setattr(db_mod.time, "sleep", lambda *_: None)

    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    # Create database with required tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # patient_variant table (required for function checks)
    cursor.execute(
        """
        CREATE TABLE patient_variant (
            No INTEGER PRIMARY KEY,
            patient_ID TEXT,
            variant TEXT
        )
        """
    )

    # variant_annotations table
    cursor.execute(
        """
        CREATE TABLE variant_annotations (
            No INTEGER PRIMARY KEY,
            variant_NC TEXT NOT NULL,
            variant_NM TEXT NOT NULL,
            variant_NP TEXT NOT NULL,
            gene TEXT NOT NULL,
            HGNC_ID INTEGER NOT NULL,
            Classification TEXT NOT NULL,
            Conditions TEXT NOT NULL,
            Stars TEXT,
            Review_status TEXT NOT NULL,
            UNIQUE(variant_NC, variant_NM, variant_NP)
        )
        """
    )
    conn.commit()
    conn.close()

    # Run variant_annotations_table inside a Flask test request context
    with app.test_request_context("/"):
        db_mod.variant_annotations_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Assert that a success flash message was emitted
    assert any("successfully" in m.lower() for m in messages)

    # Verify that the variant_annotations table contains the expected row
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check row count
    cur.execute("SELECT COUNT(*) FROM variant_annotations")
    rows_count = cur.fetchone()[0]
    assert rows_count > 0  # table is not empty

    # Check that the variant_NC value matches the mocked data
    cur.execute("SELECT variant_NC FROM variant_annotations")
    variant_nc = cur.fetchone()[0]
    assert variant_nc == "NC_000003.1:g.123A>G"

    conn.close()


# -------------------------------------------------------------------------
# Integration-ish tests: everything together + validate_database/query_db
# -------------------------------------------------------------------------


def test_full_flow_creates_valid_schema_and_query(
    app, temp_variants_dir, db_name, db_path, monkeypatch
):
    """
    Integration test for full database workflow:
    - Run `patient_variant_table` and `variant_annotations_table` on the same database.
    - Validate the database schema using `validate_database`.
    - Query back the inserted rows using `query_db` to confirm correctness.

    Parameters
    ----------
    app : Flask
        Flask application fixture for creating a test request context.
    temp_variants_dir : pathlib.Path
        Temporary directory used for storing variant files.
    db_name : str
        Name of the database file.
    db_path : pathlib.Path
        Path to the database file.
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture for mocking functions.
    """
    # Create a dummy VCF file
    vcf_file = temp_variants_dir / "PatientY.vcf"
    vcf_file.write_text("## dummy content\n")

    # Mock variant_parser to return a controlled list of variants
    def fake_variant_parser(path):
        return ["c.999G>T"]

    monkeypatch.setattr(db_mod, "variant_parser", fake_variant_parser)

    # Mock fetch_vv to return controlled variant details
    def fake_fetch_vv(variant):
        return (
            "NC_000010.1:g.999G>T",
            "NM_000010.1:c.999G>T",
            "NP_000010.1:p.(Gly333Val)",
            "GENE10",
            1010,
        )

    monkeypatch.setattr(db_mod, "fetch_vv", fake_fetch_vv)

    # Mock clinvar_annotations to return controlled annotation data
    def fake_clinvar_annotations(nc, nm):
        return {
            "classification": "Benign",
            "conditions": "Unknown",
            "stars": "★",
            "reviewstatus": "criteria provided, single submitter",
        }

    monkeypatch.setattr(db_mod, "clinvar_annotations", fake_clinvar_annotations)

    # Mock time.sleep to avoid slowing down the test
    monkeypatch.setattr(db_mod.time, "sleep", lambda *_: None)

    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    # Run both table functions inside a Flask test request context
    with app.test_request_context("/"):
        db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        db_mod.variant_annotations_table(str(temp_variants_dir), db_name)

    # Integration: validate database schema
    assert db_mod.validate_database(db_path) is True

    # Integration: query patient_variant table
    rows_pv = db_mod.query_db(
        db_path,
        "SELECT patient_ID, variant FROM patient_variant",
    )
    assert len(rows_pv) == 1
    assert rows_pv[0]["patient_ID"] == "PatientY"
    assert rows_pv[0]["variant"] == "NC_000010.1:g.999G>T"

    # Integration: query variant_annotations table
    rows_va = db_mod.query_db(
        db_path,
        "SELECT variant_NC, classification FROM variant_annotations",
    )
    assert len(rows_va) == 1
    assert rows_va[0]["variant_NC"] == "NC_000010.1:g.999G>T"
    assert rows_va[0]["classification"] == "Benign"
