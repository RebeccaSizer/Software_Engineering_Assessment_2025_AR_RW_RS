# these tests were written by ChatGPT and refined by the developer
# test_db_tools.py
import os
import sqlite3
from pathlib import Path

import pytest
from flask import Flask, get_flashed_messages


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
    """validate_database returns True when schema matches EXPECTED_SCHEMA."""
    db_file = tmp_path / "valid.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Create correct patient_variant table
    cur.execute(
        """
        CREATE TABLE patient_variant (
            No INTEGER PRIMARY KEY,
            patient_ID TEXT NOT NULL,
            variant TEXT NOT NULL
        )
        """
    )

    # Create correct variant_annotations table
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

    conn.commit()
    conn.close()

    assert db_mod.validate_database(str(db_file)) is True


def test_validate_database_missing_table(tmp_path):
    """validate_database returns False if a required table is missing."""
    db_file = tmp_path / "invalid.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Only create one of the required tables
    cur.execute(
        """
        CREATE TABLE patient_variant (
            No INTEGER PRIMARY KEY,
            patient_ID TEXT NOT NULL,
            variant TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()

    assert db_mod.validate_database(str(db_file)) is False


def test_validate_database_missing_column(tmp_path):
    """validate_database returns False if a required column is missing."""
    db_file = tmp_path / "invalid_cols.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Missing HGNC_ID column, for example
    cur.execute(
        """
        CREATE TABLE patient_variant (
            No INTEGER PRIMARY KEY,
            patient_ID TEXT NOT NULL
            -- variant column missing on purpose
        )
        """
    )

    conn.commit()
    conn.close()

    assert db_mod.validate_database(str(db_file)) is False


def test_query_db_returns_all_rows(tmp_path):
    """query_db returns a list of sqlite3.Row when one=False (default)."""
    db_file = tmp_path / "q.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO t (name) VALUES (?)", ("Alice",))
    conn.execute("INSERT INTO t (name) VALUES (?)", ("Bob",))
    conn.commit()
    conn.close()

    rows = db_mod.query_db(str(db_file), "SELECT * FROM t ORDER BY id")
    assert len(rows) == 2
    assert rows[0]["name"] == "Alice"
    assert rows[1]["name"] == "Bob"


def test_query_db_returns_one_row(tmp_path):
    """query_db returns a single sqlite3.Row when one=True."""
    db_file = tmp_path / "q_one.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO t (name) VALUES (?)", ("Alice",))
    conn.commit()
    conn.close()

    row = db_mod.query_db(str(db_file), "SELECT * FROM t", one=True)
    assert row is not None
    assert row["name"] == "Alice"

    # If no rows and one=True, it should return None
    row = db_mod.query_db(str(db_file), "SELECT * FROM t WHERE name='Bob'", one=True)
    assert row is None


# -------------------------------------------------------------------------
# Unit-ish tests for patient_variant_table: behaviour with empty folder
# -------------------------------------------------------------------------


def test_patient_variant_table_no_files_creates_table_and_flashes(app, temp_variants_dir, db_name, db_path):
    """
    When no .vcf/.csv files are present:
    - A warning flash is issued.
    - The DB and patient_variant table are created.
    """
    if os.path.exists(db_path):
        os.remove(db_path)

    with app.test_request_context("/"):
        db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Check flash message contains the expected warning (typo preserved)
    assert any("No varaint files have been uploaded" in m for m in messages)

    # Check DB exists and has patient_variant table
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='patient_variant';"
    )
    assert cur.fetchone() is not None
    conn.close()


# -------------------------------------------------------------------------
# Unit-ish tests for patient_variant_table: happy path with mocks
# -------------------------------------------------------------------------


def test_patient_variant_table_inserts_variants(
    app, temp_variants_dir, db_name, db_path, monkeypatch
):
    """
    With one VCF file and mocked variant_parser + fetch_vv, the function
    should insert (patient_ID, variant) rows into patient_variant.
    """
    # Create a dummy VCF file
    vcf_file = temp_variants_dir / "Patient1.vcf"
    vcf_file.write_text("## dummy content\n")

    # Mock variant_parser(path) -> list of raw variants
    def fake_variant_parser(path):
        assert str(vcf_file) == path
        return ["varA", "varB"]

    monkeypatch.setattr(db_mod, "variant_parser", fake_variant_parser)

    # Mock fetch_vv(variant) -> tuple where [0] is NC_ string
    def fake_fetch_vv(variant):
        if variant == "varA":
            return ("NC_000001.1:g.1A>G", "NM_dummy", "NP_dummy", "GENE1", 1111)
        elif variant == "varB":
            return ("NC_000002.1:g.2C>T", "NM_dummy2", "NP_dummy2", "GENE2", 2222)
        else:
            raise AssertionError("Unexpected variant")

    monkeypatch.setattr(db_mod, "fetch_vv", fake_fetch_vv)

    # Avoid slowing tests with real sleep
    monkeypatch.setattr(db_mod.time, "sleep", lambda *_: None)

    if os.path.exists(db_path):
        os.remove(db_path)

    with app.test_request_context("/"):
        db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Should not have error flashes about VariantValidator
    assert not any("VariantValidator" in m for m in messages)

    # Check DB content
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


def test_variant_annotations_table_no_files_flashes_and_returns(
    app, temp_variants_dir, db_name, db_path
):
    """
    If no variant files exist, variant_annotations_table should:
    - flash a warning
    - return early (DB may not be created)
    """
    if os.path.exists(db_path):
        os.remove(db_path)

    with app.test_request_context("/"):
        db_mod.variant_annotations_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    assert any("No data files have been uploaded" in m for m in messages)

    # It returns immediately, so DB might not exist yet
    # We just assert that it *didn't* crash. Existence is optional here.


def test_variant_annotations_table_inserts_annotations(
    app, temp_variants_dir, db_name, db_path, monkeypatch
):
    """
    With one VCF file and mocks for variant_parser, fetch_vv, clinvar_annotations,
    variant_annotations_table should populate the variant_annotations table.
    """
    # Create a dummy VCF file
    vcf_file = temp_variants_dir / "PatientX.vcf"
    vcf_file.write_text("## dummy content\n")

    # Mock variant_parser to return a single variant per file
    def fake_variant_parser(path):
        assert str(vcf_file) == path
        return ["c.123A>G"]

    monkeypatch.setattr(db_mod, "variant_parser", fake_variant_parser)

    # Mock fetch_vv returning the 5-tuple
    def fake_fetch_vv(variant):
        assert variant == "c.123A>G"
        return (
            "NC_000003.1:g.123A>G",
            "NM_000003.1:c.123A>G",
            "NP_000003.1:p.(Lys41Arg)",
            "GENE3",
            3333,
        )

    monkeypatch.setattr(db_mod, "fetch_vv", fake_fetch_vv)
    monkeypatch.setattr(db_mod.time, "sleep", lambda *_: None)

    # Mock clinvar_annotations to return a dict with annotations
    def fake_clinvar_annotations(nc_variant, nm_variant):
        assert nc_variant == "NC_000003.1:g.123A>G"
        assert nm_variant == "NM_000003.1:c.123A>G"
        return {
            "classification": "Pathogenic",
            "conditions": "Some condition",
            "stars": "★★",
            "reviewstatus": "criteria provided, multiple submitters, no conflicts",
        }

    monkeypatch.setattr(db_mod, "clinvar_annotations", fake_clinvar_annotations)

    if os.path.exists(db_path):
        os.remove(db_path)

    with app.test_request_context("/"):
        db_mod.variant_annotations_table(str(temp_variants_dir), db_name)
        messages = get_flashed_messages()

    # Expect a success flash at the end
    assert any(f"{db_name}.db created/updated successfully" in m for m in messages)

    # Check DB contents
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM variant_annotations")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 1
    row = rows[0]
    assert row["variant_NC"] == "NC_000003.1:g.123A>G"
    assert row["variant_NM"] == "NM_000003.1:c.123A>G"
    assert row["variant_NP"] == "NP_000003.1:p.(Lys41Arg)"
    assert row["gene"] == "GENE3"
    assert row["HGNC_ID"] == 3333
    assert row["Classification"] == "Pathogenic"
    assert row["Conditions"] == "Some condition"
    assert row["Stars"] == "★★"
    assert (
        row["Review_status"]
        == "criteria provided, multiple submitters, no conflicts"
    )


# -------------------------------------------------------------------------
# Integration-ish tests: everything together + validate_database/query_db
# -------------------------------------------------------------------------


def test_full_flow_creates_valid_schema_and_query(
    app, temp_variants_dir, db_name, db_path, monkeypatch
):
    """
    Integration test:
    - Run patient_variant_table and variant_annotations_table on the same db_name
    - Use validate_database to confirm schema
    - Use query_db to read back rows
    """
    # Dummy VCF
    vcf_file = temp_variants_dir / "PatientY.vcf"
    vcf_file.write_text("## dummy content\n")

    # Shared mock variant list
    def fake_variant_parser(path):
        return ["c.999G>T"]

    monkeypatch.setattr(db_mod, "variant_parser", fake_variant_parser)

    def fake_fetch_vv(variant):
        return (
            "NC_000010.1:g.999G>T",
            "NM_000010.1:c.999G>T",
            "NP_000010.1:p.(Gly333Val)",
            "GENE10",
            1010,
        )

    monkeypatch.setattr(db_mod, "fetch_vv", fake_fetch_vv)
    monkeypatch.setattr(db_mod.time, "sleep", lambda *_: None)

    def fake_clinvar_annotations(nc, nm):
        return {
            "classification": "Benign",
            "conditions": "Unknown",
            "stars": "★",
            "reviewstatus": "criteria provided, single submitter",
        }

    monkeypatch.setattr(db_mod, "clinvar_annotations", fake_clinvar_annotations)

    if os.path.exists(db_path):
        os.remove(db_path)

    with app.test_request_context("/"):
        db_mod.patient_variant_table(str(temp_variants_dir), db_name)
        db_mod.variant_annotations_table(str(temp_variants_dir), db_name)

    # Integration: validate schema
    assert db_mod.validate_database(db_path) is True

    # Integration: query DB via query_db
    rows_pv = db_mod.query_db(
        db_path,
        "SELECT patient_ID, variant FROM patient_variant",
    )
    assert len(rows_pv) == 1
    assert rows_pv[0]["patient_ID"] == "PatientY"
    assert rows_pv[0]["variant"] == "NC_000010.1:g.999G>T"

    rows_va = db_mod.query_db(
        db_path,
        "SELECT variant_NC, classification FROM variant_annotations",
    )
    assert len(rows_va) == 1
    assert rows_va[0]["variant_NC"] == "NC_000010.1:g.999G>T"
    assert rows_va[0]["classification"] == "Benign"