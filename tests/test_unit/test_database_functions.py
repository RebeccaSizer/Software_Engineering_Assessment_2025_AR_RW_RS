"""
Unit tests for database_functions (tools/modules/database_functions.py).

This module contains pytest-based tests that verify correct behaviour
and error handling for functions in database_functions. Some external
dependencies such as databases, files, and network requests are mocked
using pytest fixtures (e.g. monkeypatch) to ensure deterministic and
isolated testing.

Some tests were initially generated with assistance from ChatGPT and
subsequently refined by the developer.
"""

import os
import sqlite3
import pytest
from pathlib import Path
from flask import Flask, get_flashed_messages
from unittest.mock import patch, MagicMock
import tools.modules.database_functions as db_mod
from tools.modules.database_functions import patient_variant_table
from tools.modules.database_functions import variant_annotations_table
from tools.modules.database_functions import validate_database
from tools.modules.database_functions import query_db

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


@pytest.mark.parametrize(
    "exception_to_raise,expected_start",
    [
        (sqlite3.OperationalError("Operational fail"),
         "❌ patient_variant_table SQLite3 Error:"),
        (sqlite3.DatabaseError("Database fail"),
         "❌ patient_variant_table SQLite3 Error:"),
        (sqlite3.ProgrammingError("Programming fail"),
         "❌ patient_variant_table SQLite3 Error:"),
        (Exception("Generic fail"),
         "❌ patient_variant_table Error occurred while preparing"),
    ]
)
def test_patient_variant_table_exceptions(exception_to_raise, expected_start, tmp_path):
    """
    Test patient_variant_table handling of SQLite-related exceptions.

    This test forces database execution failures by raising a supplied
    exception when cursor.execute() is called. It verifies that:
    - the function returns the string 'error'
    - a flash message is emitted
    - at least one flash message begins with the expected prefix
    """

    # Name of the test database (without .db extension)
    db_name = "test_db"

    # Patch all external dependencies used by patient_variant_table
    # to isolate exception-handling behaviour.
    with patch("os.listdir", return_value=["fake.vcf"]), \
         patch("tools.modules.database_functions.sqlite3.connect") as mock_connect, \
         patch("tools.modules.database_functions.flash") as mock_flash, \
         patch("tools.modules.database_functions.logger") as mock_logger, \
         patch(
             "tools.modules.database_functions.sqlite_error",
             return_value="something wrong with the database",
         ), \
         patch(
             "tools.modules.database_functions.variant_parser",
             return_value=["variant1"],
         ), \
         patch(
             "tools.modules.database_functions.fetch_vv",
             return_value=("NC_000000.1:g.1A>T", "", "", "", ""),
         ):

        # Create mocked database connection and cursor objects
        fake_cursor = MagicMock()
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        mock_connect.return_value = fake_conn

        # Force cursor.execute() to raise the supplied exception
        # to trigger the database exception-handling path
        fake_cursor.execute.side_effect = exception_to_raise

        # Call the function under test
        result = patient_variant_table(str(tmp_path), db_name)

        # Verify that the function signals failure
        assert result == "error"

        # Ensure at least one user-facing flash message was triggered
        assert mock_flash.call_count > 0

        # Extract all flashed messages
        flash_messages = [call[0][0] for call in mock_flash.call_args_list]

        # Confirm that at least one flash message begins with the expected text
        assert any(msg.startswith(expected_start) for msg in flash_messages)

def test_patient_variant_table_fetch_vv_exception(
    app, temp_variants_dir, db_name, db_path, monkeypatch
):
    """
    Test patient_variant_table behaviour when fetch_vv raises an exception.

    This test simulates a failure in the VariantValidator query step by
    forcing fetch_vv to raise a generic Exception. It verifies that:
    - the exception is handled internally
    - a user-facing flash message is generated
    - the function does not crash and returns None or 'error'
    """

    # Create a dummy VCF file to ensure the variant directory is not empty
    vcf_file = temp_variants_dir / "PatientException.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch variant_parser to return a single fake variant
    # so that patient_variant_table proceeds to the fetch_vv step
    monkeypatch.setattr(db_mod, "variant_parser", lambda path: ["variantX"])

    # Patch fetch_vv to raise a generic Exception to simulate API failure
    def raise_exception(v):
        raise Exception("VV fail")

    monkeypatch.setattr(db_mod, "fetch_vv", raise_exception)

    # Ensure a clean test state by removing any existing database file
    if os.path.exists(db_path):
        os.remove(db_path)

    # Run the function inside a Flask request context to capture flash messages
    with app.test_request_context("/"):
        result = db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Verify that the expected error message was flashed to the user
    assert (
        "❌ patient_variant_table Error: Could not retrieve a response from VariantValidator"
        in messages[0]
    )

    # Confirm the function exits gracefully without crashing
    # (depending on execution path, it may return None or 'error')
    assert result in (None, "error")



def test_patient_variant_table_fetch_vv_none_response(
    app, temp_variants_dir, db_name, db_path, monkeypatch
):
    """
    Test patient_variant_table behaviour when fetch_vv returns None.

    This test simulates a scenario where VariantValidator does not return
    a response (i.e. fetch_vv returns None). It verifies that:
    - the missing response is handled gracefully
    - an appropriate warning flash message is shown to the user
    - the function exits safely without crashing
    """

    # Create a dummy VCF file so the variants directory is not empty
    vcf_file = temp_variants_dir / "PatientNone.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch variant_parser to return a single fake variant
    # so that the function proceeds to the fetch_vv step
    monkeypatch.setattr(db_mod, "variant_parser", lambda path: ["variantY"])

    # Patch fetch_vv to return None, simulating no API response
    monkeypatch.setattr(db_mod, "fetch_vv", lambda v: None)

    # Ensure a clean test state by removing any pre-existing database file
    if os.path.exists(db_path):
        os.remove(db_path)

    # Execute the function inside a Flask request context to capture flashes
    with app.test_request_context("/"):
        result = db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Confirm a user-facing warning message was flashed
    assert any(
        "⚠ No response was received from VariantValidator" in m
        for m in messages
    )

    # Confirm the function exits gracefully without raising exceptions
    assert result in (None, "error")


def test_patient_variant_table_fetch_vv_string_response(
    app, temp_variants_dir, db_name, db_path, monkeypatch
):
    """
    Test patient_variant_table behaviour when fetch_vv returns a string.

    This test simulates a VariantValidator response where fetch_vv returns
    a string instead of the expected tuple. This typically represents an
    error message generated by fetch_vv itself.

    The test verifies that:
    - the string response is surfaced to the user via flash messaging
    - the function exits gracefully without raising an exception
    """

    # Create a dummy VCF file so the variants directory is not empty
    vcf_file = temp_variants_dir / "PatientString.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch variant_parser to return a single fake variant
    # so that the function proceeds to calling fetch_vv
    monkeypatch.setattr(db_mod, "variant_parser", lambda path: ["variantZ"])

    # Patch fetch_vv to return an error string instead of a tuple
    monkeypatch.setattr(db_mod, "fetch_vv", lambda v: "error string")

    # Ensure a clean test state by removing any existing database file
    if os.path.exists(db_path):
        os.remove(db_path)

    # Execute the function inside a Flask request context to capture flash messages
    with app.test_request_context("/"):
        result = db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Confirm the error string returned by fetch_vv is shown to the user
    assert any("error string" in m for m in messages)

    # Confirm the function exits safely without crashing
    assert result in (None, "error")



def test_patient_variant_table_sqlite_exception(
    monkeypatch, app, temp_variants_dir, db_name, db_path
):
    """
    Test patient_variant_table handling of SQLite OperationalError exceptions.

    This test simulates a failure during database interaction by forcing
    sqlite3.OperationalError to be raised when a cursor execute call occurs.

    The test verifies that:
    - SQLite-related exceptions are caught by the appropriate except block
    - an error message is flashed to the user
    - the function exits gracefully without crashing
    """

    # Create a dummy VCF file so the variants directory is not empty
    vcf_file = temp_variants_dir / "PatientSQLite.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch variant_parser to return a single fake variant
    # so the function proceeds to database insertion logic
    monkeypatch.setattr(db_mod, "variant_parser", lambda path: ["variantB"])

    # Patch fetch_vv to return a valid-looking tuple
    # ensuring the SQLite failure occurs during DB execution, not earlier
    monkeypatch.setattr(
        db_mod,
        "fetch_vv",
        lambda v: ("NC_000001.1:g.1A>G", "NM", "NP", "GENE", 1234),
    )

    # Fake cursor that raises sqlite3.OperationalError on any execute call
    class FakeCursor:
        def execute(self, *args, **kwargs):
            raise sqlite3.OperationalError("DB fail")

    # Fake SQLite connection returning the failing cursor
    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def close(self):
            pass

    # Patch sqlite3.connect inside database_functions to return the fake connection
    monkeypatch.setattr(db_mod.sqlite3, "connect", lambda path: FakeConn())

    # Run the function inside a Flask request context to capture flash messages
    with app.test_request_context("/"):
        result = db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Confirm that a SQLite-related error message was shown to the user
    assert any("SQLite3 Error" in m for m in messages)

    # Confirm the function exits safely without raising an exception
    assert result in (None, "error")


def test_patient_variant_table_generic_exception_on_insert(tmp_path):
    """
    Test patient_variant_table handling of a generic Exception during INSERT.

    This test simulates a non-SQLite-specific exception occurring when attempting
    to insert variant data into the database.

    The test verifies that:
    - generic Exceptions raised during INSERT are caught
    - an appropriate error message is flashed to the user
    - the function returns 'error' when no rows are successfully added
    """

    # Create a temporary directory to act as the variants directory
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()

    # Create a dummy VCF file so the directory is not empty
    vcf_file = temp_dir / "Patient2.vcf"
    vcf_file.write_text("## dummy content\n")

    # Define database name and expected database path
    db_name = "test_db_generic"
    db_path = tmp_path / f"{db_name}.db"

    # Patch internal dependencies to fully control execution flow
    with patch("tools.modules.database_functions.os.listdir", return_value=[str(vcf_file)]), \
         patch("tools.modules.database_functions.variant_parser", return_value=["var1"]), \
         patch("tools.modules.database_functions.fetch_vv", return_value=("NC_000001.1:g.123A>G",)), \
         patch("tools.modules.database_functions.sqlite3.connect") as mock_connect, \
         patch("tools.modules.database_functions.flash") as mock_flash, \
         patch("tools.modules.database_functions.logger") as mock_logger:

        # Create a fake SQLite connection and cursor
        fake_cursor = MagicMock()
        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor
        mock_connect.return_value = fake_conn

        # Side effect function to control cursor.execute behaviour
        # - Raise a generic Exception on INSERT
        # - Simulate an empty table when SELECT COUNT is executed
        def execute_side_effect(*args, **kwargs):
            if "INSERT" in args[0]:
                raise Exception("generic insert fail")
            elif "SELECT COUNT" in args[0]:
                fake_cursor.fetchone.return_value = [0]
                return
            return None

        # Apply the side effect to cursor.execute
        fake_cursor.execute.side_effect = execute_side_effect

        # Run the function under test
        result = db_mod.patient_variant_table(str(temp_dir), db_name)

        # Function should return 'error' since no records were added
        assert result == "error"

        # Verify that a user-facing flash message was generated
        # describing the failed insert attempt
        flash_messages = [call[0][0] for call in mock_flash.call_args_list]
        assert any(
            "Could not add Patient2 and NC_000001.1:g.123A>G" in msg
            for msg in flash_messages
        )


@pytest.mark.parametrize("exception_type, expected_flash", [
    (sqlite3.OperationalError, "❌ patient_variant_table: SQLite3 Error"),
    (Exception, "❌ patient_variant_table Error")
])
def test_patient_variant_table_db_check_exceptions(app, tmp_path, monkeypatch, exception_type, expected_flash):
    """
    Test patient_variant_table behavior when the final database check fails.

    This test targets the *final try/except block* in patient_variant_table,
    where the function queries the database to check whether any rows were
    successfully inserted (typically via a SELECT COUNT query).

    The test verifies that:
    - exceptions raised during the database validation step are caught
    - an appropriate flash message is generated
    - the function returns 'error' when the database check fails
    """

    db_name = "test_db_check_exception"

    # Create a dummy VCF file so os.listdir finds at least one input file
    vcf_file = tmp_path / "Patient1.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch os.listdir to simulate presence of the VCF file
    monkeypatch.setattr("os.listdir", lambda path: [vcf_file.name])

    # Patch variant_parser to return a single valid variant
    monkeypatch.setattr(
        "tools.modules.database_functions.variant_parser",
        lambda path: ["c.123A>G"]
    )

    # Patch fetch_vv to return a valid VariantValidator-style response tuple
    monkeypatch.setattr(
        "tools.modules.database_functions.fetch_vv",
        lambda variant: ("NC_000001.11:g.123A>G", "NM_0001", "NP_0001", "GENE1", 1234)
    )

    # Fake cursor that raises an exception when the final SELECT COUNT query is executed
    class FakeCursor:
        def execute(self, *args, **kwargs):
            # Simulate failure during database row-count validation
            if "SELECT COUNT" in args[0]:
                raise exception_type("Simulated exception for testing")
            return None

        # Return zero rows if fetchone is called (defensive fallback)
        def fetchone(self):
            return [0]

    # Fake database connection returning the fake cursor
    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            return None

        def close(self):
            return None

    # Patch sqlite3.connect to use the fake connection
    monkeypatch.setattr(
        "tools.modules.database_functions.sqlite3.connect",
        lambda db_path: FakeConnection()
    )

    # Run the function within a Flask request context to capture flash messages
    with app.test_request_context("/"):
        result = patient_variant_table(str(tmp_path), db_name)

        # Function should return 'error' due to the simulated database exception
        assert result == "error"

        # Verify that a flash message containing the expected text was emitted
        flashes = get_flashed_messages()
        assert any(expected_flash in msg for msg in flashes)


def test_variant_annotations_table_db_creation_exceptions(app, tmp_path, monkeypatch):
    """
    Test variant_annotations_table handling of database creation/setup failures.

    This test ensures that variant_annotations_table:
    - gracefully handles SQLite3-specific exceptions raised during database setup
    - gracefully handles generic Exceptions raised during database setup
    - flashes appropriate error messages for each failure type
    - returns 'error' instead of raising UnboundLocalError or crashing

    The test explicitly covers failures occurring *after* sqlite3.connect
    but *before* any successful cursor operations.
    """

    db_name = "test_db_exception"

    # Create a dummy VCF file so os.listdir detects input data
    vcf_file = tmp_path / "Patient1.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch os.listdir to simulate presence of a VCF file
    monkeypatch.setattr(os, "listdir", lambda path: [vcf_file.name])

    # Patch dependent functions to isolate database setup logic
    monkeypatch.setattr(db_mod, "variant_parser", lambda path: ["c.123A>G"])
    monkeypatch.setattr(
        db_mod,
        "fetch_vv",
        lambda variant: ("NC_000001.11:g.123A>G", "NM_0001", "NP_0001", "GENE1", 1234)
    )
    monkeypatch.setattr(
        db_mod,
        "clinvar_annotations",
        lambda nc, nm: {
            "classification": "Pathogenic",
            "conditions": "TestCond",
            "stars": "★",
            "reviewstatus": "reviewed",
        },
    )

    # ------------------------------------------------------------------
    # CASE 1: SQLite3 OperationalError raised during cursor creation
    # ------------------------------------------------------------------
    class FakeConn:
        """Simulate a SQLite connection that fails with an OperationalError."""
        def cursor(self):
            raise sqlite3.OperationalError("Forced SQLite error")

        def close(self):
            return None

    # Patch sqlite3.connect to return the failing SQLite connection
    monkeypatch.setattr(db_mod.sqlite3, "connect", lambda db_path: FakeConn())

    with app.test_request_context("/"):
        result = db_mod.variant_annotations_table(str(tmp_path), db_name)
        flashes = get_flashed_messages()

        # Expect a SQLite-specific flash message and 'error' return value
        assert any("SQLite3 Error" in msg for msg in flashes)
        assert result == "error"

    # ------------------------------------------------------------------
    # CASE 2: Generic Exception raised during cursor creation
    # ------------------------------------------------------------------
    class GenericFailConn:
        """Simulate a database connection that raises a generic exception."""
        def cursor(self):
            raise Exception("Forced generic error")

        def close(self):
            return None

    # Patch sqlite3.connect to return the generic failing connection
    monkeypatch.setattr(db_mod.sqlite3, "connect", lambda db_path: GenericFailConn())

    with app.test_request_context("/"):
        result = db_mod.variant_annotations_table(str(tmp_path), db_name)
        flashes = get_flashed_messages()

        # Expect a generic preparation error flash message and 'error' return value
        assert any("Error occurred while preparing" in msg for msg in flashes)
        assert result == "error"

@pytest.mark.parametrize(
    "fetch_vv_side_effect, expected_fragment",
    [
        (Exception("fetch_vv failed"), "❌ Could not retrieve a response from VariantValidator"),
        (lambda v: None, "⚠ No response from VariantValidator"),
        (lambda v: "Invalid string response", "Invalid string response"),
    ],
)
def test_variant_annotations_table_fetch_vv_exceptions(app, tmp_path, fetch_vv_side_effect, expected_fragment):
    """
    Test variant_annotations_table handling of exceptions raised by fetch_vv.

    This test ensures that:
    - fetch_vv exceptions are caught gracefully
    - appropriate flash messages are displayed to the user
    - the function returns 'error' when a fetch_vv exception occurs

    Parameters
    ----------
    app : Flask application fixture
        Provides the Flask test request context for flash messages.
    tmp_path : pathlib.Path
        Temporary directory fixture to simulate file input.
    fetch_vv_side_effect : Exception or callable
        Side effect to simulate fetch_vv raising an exception.
    expected_fragment : str
        Expected substring in the flashed error message.
    """

    db_name = "test_db_fetch_vv"

    # Create a dummy VCF file in the temporary directory
    vcf_file = tmp_path / "Patient1.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch dependencies to isolate fetch_vv exception handling
    with patch("os.listdir", return_value=[vcf_file.name]), \
         patch("tools.modules.database_functions.variant_parser", return_value=["c.123A>G"]), \
         patch("tools.modules.database_functions.fetch_vv", side_effect=fetch_vv_side_effect), \
         patch("tools.modules.database_functions.clinvar_annotations", return_value={"classification": "Pathogenic"}), \
         patch("tools.modules.database_functions.sqlite3.connect") as mock_connect:

        # Simulate a database cursor and connection
        class FakeCursor:
            def execute(self, *args, **kwargs):
                return None
            def fetchone(self):
                return [0]

        class FakeConn:
            def cursor(self):
                return FakeCursor()
            def commit(self):
                return None
            def close(self):
                return None

        mock_connect.return_value = FakeConn()

        # Run the function inside a Flask test request context
        with app.test_request_context("/"):
            result = db_mod.variant_annotations_table(str(tmp_path), db_name)
            flashes = get_flashed_messages()

            # Assert that the expected error message fragment was flashed
            assert any(expected_fragment in msg for msg in flashes), f"Flashes: {flashes}"

            # Function should return 'error' due to fetch_vv exception
            assert result == "error"

@pytest.mark.parametrize("clinvar_side_effect, expected_flash", [
    (Exception("clinvar failed"), "❌ Unable to query clinvar.db"),
    (lambda nc, nm: None, "❌ Variant summary record could not be found in clinvar.db"),
    (lambda nc, nm: "Invalid string response", "Variant not added to"),
])
def test_variant_annotations_table_clinvar_exceptions(app, tmp_path, clinvar_side_effect, expected_flash):
    """
    Test variant_annotations_table handling of exceptions or bad responses
    from clinvar_annotations.

    This test ensures that:
    - Exceptions raised by clinvar_annotations are caught gracefully.
    - Appropriate flash messages are displayed to the user.
    - The function returns 'error' when a clinvar_annotations exception occurs.

    Parameters
    ----------
    app : Flask application fixture
        Provides a Flask test request context for flash messages.
    tmp_path : pathlib.Path
        Temporary directory fixture to simulate file input.
    clinvar_side_effect : Exception or callable
        Side effect to simulate clinvar_annotations raising an exception.
    expected_flash : str
        Expected substring in the flashed error message.
    """

    db_name = "test_db_clinvar"

    # Create a dummy VCF file in the temporary directory
    vcf_file = tmp_path / "Patient1.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch dependencies to isolate clinvar_annotations exception handling
    with patch("os.listdir", return_value=[vcf_file.name]), \
         patch("tools.modules.database_functions.variant_parser", return_value=["c.123A>G"]), \
         patch("tools.modules.database_functions.fetch_vv", 
               return_value=("NC_000001.11:g.123A>G", "NM_0001", "NP_0001", "GENE1", 1234)), \
         patch("tools.modules.database_functions.clinvar_annotations", side_effect=clinvar_side_effect), \
         patch("tools.modules.database_functions.sqlite3.connect") as mock_connect:

        # Provide a fake connection and cursor to prevent actual DB errors
        class FakeCursor:
            def execute(self, *args, **kwargs):
                return None

            def fetchone(self):
                return [0]

        class FakeConn:
            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

            def close(self):
                return None

        mock_connect.return_value = FakeConn()

        # Run the function inside a Flask test request context
        with app.test_request_context("/"):
            result = db_mod.variant_annotations_table(str(tmp_path), db_name)
            flashes = get_flashed_messages()

            # Assert that the expected error message fragment was flashed
            assert any(expected_flash in msg for msg in flashes)

            # Function should return 'error' due to clinvar_annotations exception
            assert result == "error"

@pytest.mark.parametrize(
    "clinvar_side_effect, expected_fragment",
    [
        (Exception("clinvar_annotations failed"), "❌ Unable to query clinvar.db"),
        (lambda nc, nm: {}, "❌ Variant summary record could not be found in clinvar.db"),
        (lambda nc, nm: "Invalid string response", "Invalid string response"),
    ]
)

def test_variant_annotations_table_clinvar_exceptions(app, tmp_path, clinvar_side_effect, expected_fragment):
    """
    Test exception handling in variant_annotations_table around clinvar_annotations().

    Covers the following scenarios:
    - clinvar_annotations raises an exception
    - clinvar_annotations returns an empty dictionary
    - clinvar_annotations returns an invalid string response
    - clinvar_annotations returns a successful dictionary

    This ensures that the function:
    - Flashes an appropriate message for any bad response or exception
    - Returns 'error' when clinvar_annotations fails
    - Handles DB interactions safely using a fake connection
    """

    db_name = "test_db_clinvar"

    # Create a dummy VCF file in the temporary directory
    vcf_file = tmp_path / "Patient1.vcf"
    vcf_file.write_text("## dummy content\n")

    # Patch dependencies to isolate clinvar_annotations behavior
    with patch("os.listdir", return_value=[vcf_file.name]), \
         patch("tools.modules.database_functions.variant_parser", return_value=["c.123A>G"]), \
         patch(
             "tools.modules.database_functions.fetch_vv",
             return_value=("NC_000001.11:g.123A>G", "NM_0001", "NP_0001", "GENE1", 1234)
         ), \
         patch(
             "tools.modules.database_functions.clinvar_annotations",
             side_effect=clinvar_side_effect
         ), \
         patch("tools.modules.database_functions.sqlite3.connect") as mock_connect:

        # Fake DB cursor to avoid real database writes
        class FakeCursor:
            def execute(self, *args, **kwargs):
                return None

            def fetchone(self):
                return [0]

        # Fake DB connection
        class FakeConn:
            def cursor(self):
                return FakeCursor()

            def commit(self):
                return None

            def close(self):
                return None

        mock_connect.return_value = FakeConn()

        # Run inside a Flask test request context to allow flashing
        with app.test_request_context("/"):
            result = db_mod.variant_annotations_table(str(tmp_path), db_name)
            flashes = get_flashed_messages()

            # Ensure at least one flash message contains the expected fragment
            assert any(expected_fragment in msg for msg in flashes), f"Flashes: {flashes}"

            # The function should return 'error' due to clinvar_annotations failure
            assert result == "error"


def test_variant_annotations_table_sqlite_exception(app, tmp_path):
    """
    Test variant_annotations_table handling of a SQLite3 OperationalError.

    This ensures that:
    - The function flashes an appropriate message when a DB operation fails.
    - The function safely returns 'error' without raising an unhandled exception.
    """

    db_name = "test_db_exception"

    # Create a dummy VCF file in the temporary directory
    vcf_file = tmp_path / "Patient1.vcf"
    vcf_file.write_text("## dummy content\n")

    # Fake cursor that raises OperationalError when executing SQL commands
    class FakeCursor:
        def execute(self, *args, **kwargs):
            raise sqlite3.OperationalError("Forced SQLite error")

        def fetchone(self):
            return [0]

    # Fake connection to provide a cursor and no-op commit/close
    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            return None

        def close(self):
            return None

    # Patch dependencies to isolate SQLite exception
    with patch("os.listdir", return_value=[vcf_file.name]), \
         patch("tools.modules.database_functions.variant_parser", return_value=["c.123A>G"]), \
         patch(
             "tools.modules.database_functions.fetch_vv",
             return_value=("NC_000001.11:g.123A>G", "NM_0001", "NP_0001", "GENE1", 1234)
         ), \
         patch(
             "tools.modules.database_functions.clinvar_annotations",
             return_value={
                 "classification": "Pathogenic",
                 "conditions": "TestCond",
                 "stars": "★",
                 "reviewstatus": "reviewed"
             }
         ), \
         patch("tools.modules.database_functions.sqlite3.connect", return_value=FakeConnection()):

        # Run the function inside a Flask test request context
        with app.test_request_context("/"):
            result = db_mod.variant_annotations_table(str(tmp_path), db_name)
            flashes = get_flashed_messages()

            # Ensure the flash message contains the SQLite error
            assert any("SQLite3 Error" in msg for msg in flashes)

            # The function should safely return 'error'
            assert result == "error"

@pytest.fixture
def app():
    app = Flask(__name__)
    app.secret_key = "test_secret"
    return app

def create_db(path, tables):
    """
    Helper function to create a test SQLite database with specified tables and columns.

    Args:
        path (str or pathlib.Path): Path where the SQLite database will be created.
        tables (dict): Dictionary where keys are table names and values are lists of column names.

    Example:
        tables = {
            "patients": ["id", "name", "age"],
            "variants": ["chrom", "pos", "ref", "alt"]
        }
        create_db("test.db", tables)
    """
    # Connect to the SQLite database (creates file if it doesn't exist)
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    # Iterate over each table and create it with the specified columns
    for table, columns in tables.items():
        # Build SQL column definitions as "col_name TEXT"
        cols_sql = ", ".join(f"{col} TEXT" for col in columns)
        # Execute SQL CREATE TABLE statement
        cur.execute(f"CREATE TABLE {table} ({cols_sql})")

    # Commit changes and close the connection
    conn.commit()
    conn.close()

def test_validate_database_success(app, tmp_path):
    """
    Test that `validate_database` returns True for a correctly structured database.

    This test creates a temporary SQLite database with the expected tables and columns,
    then checks that `validate_database` recognizes it as valid.

    Args:
        app: Flask app fixture, used to provide a test request context for flashing messages.
        tmp_path: pytest temporary path fixture for creating temporary files/databases.
    """
    # Path to the temporary test database
    db_path = tmp_path / "valid.db"

    # Define the tables and columns expected in a valid database
    tables = {
        "patient_variant": {"No", "patient_ID", "variant"},
        "variant_annotations": {
            "No", "variant_NC", "variant_NM", "variant_NP", "gene", "HGNC_ID",
            "Classification", "Conditions", "Stars", "Review_status"
        }
    }

    # Create the database with the expected structure
    create_db(db_path, tables)

    # Run the validation inside a Flask test request context to allow flash messages
    with app.test_request_context("/"):
        result = validate_database(str(db_path))
        # Assert that the validation reports the database as valid
        assert result is True
        # Assert that no flash messages were triggered
        assert get_flashed_messages() == []

def test_validate_database_missing_headers(app, tmp_path):
    """
    Test that `validate_database` returns False and flashes a warning
    when a required column is missing from the database tables.

    This test creates a temporary SQLite database with one missing column
    in the `patient_variant` table and verifies that the validation
    fails appropriately.

    Args:
        app: Flask app fixture, used to provide a test request context for flashing messages.
        tmp_path: pytest temporary path fixture for creating temporary files/databases.
    """
    # Path to the temporary test database
    db_path = tmp_path / "missing_headers.db"

    # Define tables, omitting one required column ("variant") in patient_variant
    tables = {
        "patient_variant": {"No", "patient_ID"},  
        "variant_annotations": {
            "No", "variant_NC", "variant_NM", "variant_NP", "gene", "HGNC_ID",
            "Classification", "Conditions", "Stars", "Review_status"
        }
    }

    # Create the database with the missing column
    create_db(db_path, tables)

    # Run the validation inside a Flask test request context to allow flash messages
    with app.test_request_context("/"):
        result = validate_database(str(db_path))
        flashes = get_flashed_messages()

        # Assert that the validation correctly identifies the database as invalid
        assert result is False

        # Assert that a flash message contains the expected warning about missing headers
        assert any("⚠ Inappropriate headers" in msg for msg in flashes)

def test_validate_database_sqlite_exceptions(app, tmp_path):
    """
    Test that `validate_database` handles SQLite exceptions gracefully.

    This test simulates an OperationalError when connecting to the database
    and verifies that `validate_database` returns False and flashes an
    appropriate error message.

    Args:
        app: Flask app fixture, used to provide a test request context for flashing messages.
        tmp_path: pytest temporary path fixture for database paths.
    """
    # Path to the temporary test database
    db_path = tmp_path / "error.db"

    # Patch sqlite3.connect to raise an OperationalError
    with patch(
        "tools.modules.database_functions.sqlite3.connect",
        side_effect=sqlite3.OperationalError("Forced SQLite error")
    ):
        # Run the validation inside a Flask test request context to allow flashing
        with app.test_request_context("/"):
            result = validate_database(str(db_path))
            flashes = get_flashed_messages()

            # Assert that the function correctly returns False on DB connection error
            assert result is False

            # Assert that a flash message indicates the SQLite3 error
            assert any("SQLite3 Error" in msg for msg in flashes)

def test_validate_database_generic_exception(app, tmp_path):
    """
    Test that `validate_database` handles generic exceptions gracefully.

    This test simulates a generic Exception when connecting to the database
    and verifies that `validate_database` returns False and flashes an
    appropriate error message.

    Args:
        app: Flask app fixture, used to provide a test request context for flashing messages.
        tmp_path: pytest temporary path fixture for database paths.
    """
    # Path to the temporary test database
    db_path = tmp_path / "error.db"

    # Patch sqlite3.connect to raise a generic Exception
    with patch(
        "tools.modules.database_functions.sqlite3.connect",
        side_effect=Exception("Forced generic error")
    ):
        # Run the validation inside a Flask test request context to allow flashing
        with app.test_request_context("/"):
            result = validate_database(str(db_path))
            flashes = get_flashed_messages()

            # Assert that the function correctly returns False on generic exception
            assert result is False

            # Assert that a flash message indicates a generic database validation error
            assert any("Database Validation Error" in msg for msg in flashes)