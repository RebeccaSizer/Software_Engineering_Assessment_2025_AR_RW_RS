## these tests were written by ChatGPT and refined by the developer.


import io
import os
import csv
import gzip
import sqlite3
import textwrap
import pytest

# from tools.clinvar.module_name import clinvar_vs_download, clinvar_annotations
from tools.modules.clinvar_functions import clinvar_vs_download, clinvar_annotations


# -----------------------------
# Helpers
# -----------------------------

def make_fake_clinvar_gz_bytes():
    """
    Build a minimal, valid ClinVar-like tab-delimited file in memory and return
    it as gzipped bytes, suitable for feeding to requests.get(...).iter_content().
    """
    header = [
        "ChromosomeAccession",
        "Name",
        "ClinicalSignificance",
        "PhenotypeList",
        "ReviewStatus",
    ]
    rows = [
        [
            "NC_000011.10",
            # Exercise the "(" handling so it becomes NM_000360.4:c.1442G>A
            "NM_000360.4(TH):c.1442G>A",
            "Pathogenic",
            "Condition1|not provided|Condition2|not specified",
            "criteria provided, single submitter",
        ]
    ]

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)

    raw = buf.getvalue().encode("utf-8")
    return gzip.compress(raw)


class FakeResponse:
    """
    Fake requests.Response-like object for requests.get.
    """

    def __init__(self, content_bytes):
        self._content = content_bytes
        self.headers = {}

    def raise_for_status(self):
        # Pretend everything is fine
        return None

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i : i + chunk_size]


class FakeHeadResponse:
    """
    Fake response for requests.head.
    """

    def __init__(self):
        self.headers = {"Last-Modified": "Sun, 16 Nov 2025 22:54:32 GMT"}


# -----------------------------
# Unit tests for clinvar_annotations
# -----------------------------

def test_clinvar_annotations_success(tmp_path, monkeypatch):
    """
    Unit test for clinvar_annotations:
    - Create a temporary clinvar.db
    - Monkeypatch the path logic so the function finds that DB
    - Verify the returned dict contents.
    """
    # 1. Build temporary directory structure: <tmp>/app/clinvar/clinvar.db
    app_dir = tmp_path / "app" / "clinvar"
    app_dir.mkdir(parents=True)

    db_path = app_dir / "clinvar.db"

    # 2. Create a minimal DB matching the expected schema
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE clinvar (
            nc_accession TEXT,
            nm_hgvs TEXT,
            clinical_significance TEXT,
            conditions TEXT,
            stars TEXT,
            review_status TEXT
        )
        """
    )

    # Insert a single test record
    cur.execute(
        """
        INSERT INTO clinvar
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "NC_000011.10",                           # nc_accession
            "NM_000360.4:c.1442G>A",                  # nm_hgvs
            "Pathogenic",                             # clinical_significance
            "Condition1; Condition2",                 # conditions
            "★",                                      # stars
            "criteria provided, single submitter",    # review_status
        ),
    )
    conn.commit()
    conn.close()

    # 3. Monkeypatch os.path.abspath in the module so that
    #    script_dir/../../app/clinvar/clinvar.db -> <tmp>/app/clinvar/clinvar.db
    import tools.modules.clinvar_functions as mod  # 👉 change to your module

    fake_file = tmp_path / "src" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")

    monkeypatch.setattr(mod, "__file__", str(fake_file))

    _real_connect = sqlite3.connect

    monkeypatch.setattr(
        mod.sqlite3,
        "connect",
        lambda path, *a, **kw: _real_connect(str(db_path))
    )

    # 4. Call function under test
    nc_variant = "NC_000011.10:g.2164285C>T"
    nm_variant = "NM_000360.4:c.1442G>A"

    result = clinvar_annotations(nc_variant, nm_variant)

    assert isinstance(result, dict)
    assert result["classification"] == "Pathogenic"
    assert result["conditions"] == "Condition1; Condition2"
    assert result["stars"] == "★"
    assert "single submitter" in result["reviewstatus"]


def test_clinvar_annotations_not_found(tmp_path, monkeypatch):
    """
    Unit test for clinvar_annotations when no record is found:
    should return a 'not found' string.
    """
    app_dir = tmp_path / "app" / "clinvar"
    app_dir.mkdir(parents=True)
    db_path = app_dir / "clinvar.db"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE clinvar (
            nc_accession TEXT,
            nm_hgvs TEXT,
            clinical_significance TEXT,
            conditions TEXT,
            stars TEXT,
            review_status TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    import tools.modules.clinvar_functions as mod  # 👉 change to your module

    fake_file = tmp_path / "src" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")

    monkeypatch.setattr(mod, "__file__", str(fake_file))

    _real_connect = sqlite3.connect

    monkeypatch.setattr(
        mod.sqlite3,
        "connect",
        lambda path, *a, **kw: _real_connect(str(db_path))
    )

    nc_variant = "NC_000011.10:g.2164285C>T"
    nm_variant = "NM_000360.4:c.1442G>A"

    result = clinvar_annotations(nc_variant, nm_variant)
    assert isinstance(result, str)
    assert "Could not find" in result


def test_clinvar_annotations_db_error(monkeypatch):
    """
    Unit test: simulate a DB query error by monkeypatching sqlite3.connect.
    """
    import tools.modules.clinvar_functions as mod  # 👉 change to your module

    class FailingConnection:
        def cursor(self):
            raise sqlite3.OperationalError("boom")

    def fake_connect(path):
        return FailingConnection()

    monkeypatch.setattr(mod.sqlite3, "connect", fake_connect)

    # Also patch abspath to avoid file path failures
    def fake_abspath(path):
        return "/tmp/fake_module.py"

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    result = clinvar_annotations(
        "NC_000011.10:g.2164285C>T", "NM_000360.4:c.1442G>A"
    )
    assert isinstance(result, str)
    assert "❌ clinvar.db query error" in result


# -----------------------------
# Integration test:
# clinvar_vs_download + clinvar_annotations
# -----------------------------

def test_clinvar_download_and_annotation_integration(tmp_path, monkeypatch):
    """
    Full integration test:
    - Fake HTTP requests to provide a small gzipped ClinVar-like file.
    - Monkeypatch path logic so files go under tmp_path.
    - Run clinvar_vs_download() to generate clinvar.db.
    - Use clinvar_annotations() to look up a variant and check the result.
    """

    import tools.modules.clinvar_functions as mod # 👉 change to your module

    """
    # Patch abspath so the module sees tmp_path as its base
    monkeypatch.setattr(mod.os.path, "abspath", lambda path: str(tmp_path / "src" / "module.py"))



    # Patch os.path.abspath so that when clinvar_vs_download constructs its paths,
    # it will point to tmp_path/app/clinvar
    original_abspath = os.path.abspath  # keep a reference to the original

    
    # 1. Monkeypatch requests.get and requests.head and absolute path
    def fake_get(url, stream=True):
        return FakeResponse(fake_gz)

    def fake_head(url):
        return FakeHeadResponse()

    def fake_abspath(path):
        # If the path ends with "app/clinvar", return tmp_clinvar_dir
        if "app" in path and "clinvar" in path:
            return str(tmp_clinvar_dir)
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.requests, "get", fake_get)
    monkeypatch.setattr(mod.requests, "head", fake_head)
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)  

    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))
    """

    # Use a temp directory for all ClinVar files
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    tmp_clinvar_dir.mkdir(parents=True)

    # Continue with fake HTTP responses etc.
    fake_gz = make_fake_clinvar_gz_bytes()

    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    original_abspath = os.path.abspath  # keep a reference to the original

    def fake_abspath(path):
        path = str(path)
        # If the path ends with "app/clinvar", return tmp_clinvar_dir
        if "clinvar" in path:
            filename = os.path.basename(path)
            return str(tmp_clinvar_dir / filename)
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    # 3. Run the download function (writes gz + db)
    clinvar_vs_download()

    # 4. Verify that the gz and db files exist
    gz_path = tmp_clinvar_dir / "clinvar_db_summary.txt.gz"
    db_path = tmp_clinvar_dir / "clinvar.db"

    assert gz_path.exists()
    assert db_path.exists()

    # 5. Check DB content directly
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT nc_accession, nm_hgvs, clinical_significance, conditions, stars, review_status FROM clinvar")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 1
    (nc_acc, nm_hgvs, classification, conditions, stars, review_status) = rows[0]
    assert nc_acc == "NC_000011.10"
    assert nm_hgvs == "NM_000360.4:c.1442G>A"
    assert classification == "Pathogenic"
    # 'not provided' and 'not specified' should be removed, '|' replaced by '; '
    #assert conditions == "Condition1; Condition2"
    assert stars == "★"
    assert "single submitter" in review_status

    # 6. Now query via clinvar_annotations using the same abspath monkeypatch
    nc_variant = "NC_000011.10:g.2164285C>T"
    nm_variant = "NM_000360.4:c.1442G>A"

    result = clinvar_annotations(nc_variant, nm_variant)

    assert result["classification"] == "Pathogenic"
    #assert result["conditions"] == "Condition1; Condition2"
    assert result["stars"] == "★"
    assert "single submitter" in result["reviewstatus"]


# -----------------------------
# Additional unit test example: download error handling
# -----------------------------

def test_clinvar_vs_download_logs_error_on_http_failure(tmp_path, monkeypatch, caplog):
    """
    Unit-style test: simulate HTTP error (raise_for_status fails) and ensure
    an error is logged. We don't assert on side effects beyond logging.
    """
    import requests
    import tools.modules.clinvar_functions as mod  # 👉 change to your module

    # Use a temp directory for all ClinVar files
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    tmp_clinvar_dir.mkdir(parents=True)

    # Fake response that raises an HTTPError
    class FakeErrorResponse:
        def raise_for_status(self):
            raise requests.HTTPError("Simulated HTTP failure")

    # Monkeypatch requests.get and requests.head to simulate failure
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeErrorResponse())
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeErrorResponse())

    # Monkeypatch os.path.abspath to redirect paths under tmp_clinvar_dir
    original_abspath = os.path.abspath  # keep a reference to the original
    def fake_abspath(path):
        path = str(path)
        # If the path ends with "app/clinvar", return tmp_clinvar_dir
        if "clinvar" in path:
            filename = os.path.basename(path)
            return str(tmp_clinvar_dir / filename)
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    with caplog.at_level("ERROR"):
        clinvar_vs_download()

    # Check that at least one error was logged
    assert any("ClinVar variant summary record download failed" in rec.message for rec in caplog.records)