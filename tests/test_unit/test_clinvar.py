## these tests were written by ChatGPT and refined by the developer.


import io
import os
import csv
import gzip
import errno
import pytest
import sqlite3
import requests

import tools.modules.clinvar_functions as mod
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
        ["NC_000011.10",
         "NM_000360.4:c.1442G>A",
         "Pathogenic",
         "Condition1;Condition2; not specified",
         "single submitter"
         ],
        ["NC_000011.10",
         "NM_000361.1(GENE):c.1A>T",
         "Likely Benign",
         " ;Condition2",
         "practice guideline"
         ],
        ["NC_000017.11",
         "NM_001377265.1:c.2078C>T",
         "Benign",
         "Autosomal recessive DOPA responsive dystonia|Inborn genetic diseases",
         "criteria provided, multiple submitters, no conflicts"
         ],
        ["NC_000011.10",
         "ENST000003:c.1A>T",
         "Benign",
         "IgnoreMe",
         "single submitter"
         ],
        ["NC_000012.12:g.40295535A>T",
         "NM_198578.4:c.2987A>T",
         "Uncertain significance",
         " Not provided;Autosomal dominant Parkinson disease 8| Inborn genetic diseases; ",
         "reviewed by expert panel"
         ],
        ["NC_000019.10:g.41981742C>T",
         "NM_152296.5:c.1282G>A",
         "Likely pathogenic",
         "| not specified",
         "no assertion criteria provided"
         ],
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
@pytest.mark.parametrize(
    "Review_Status,expected_stars",
    [
        ("practice guideline", "★★★★"),
        ("reviewed by expert panel", "★★★"),
        ("criteria provided, multiple submitters", "★★"),
        ("criteria provided, single submitter", "★"),
        ("no assertion criteria provided", "0★"),
    ],
)
def test_clinvar_annotations_success(tmp_path, monkeypatch, Review_Status, expected_stars):
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
    assert "single submitter" in result["reviewstatus"]
    if Review_Status in result["reviewstatus"]:
        assert result["stars"] == expected_stars

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
    assert f"Could not find {nc_variant} variant summary record in clinvar.db" in result


def test_clinvar_annotations_db_error(tmp_path, monkeypatch, caplog):
    """
    Unit test: simulate a DB query error by monkeypatching sqlite3.connect.
    """
    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "clinvar_functions.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))

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
        # Only redirect the *directory* app/clinvar
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # Redirect files inside clinvar
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    class FailingConnection:
        def cursor(self):
            raise sqlite3.OperationalError("boom")

    def fake_connect(path):
        return FailingConnection()

    monkeypatch.setattr(mod.sqlite3, "connect", fake_connect)

    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    assert any(
        f"sqlite3.OperationalError" in rec.message
        for rec in caplog.records
    )

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
@pytest.mark.parametrize(
    "Review_Status,expected_stars",
    [
        ("practice guideline", "★★★★"),
        ("reviewed by expert panel", "★★★"),
        ("criteria provided, multiple submitters", "★★"),
        ("criteria provided, single submitter", "★"),
        ("no assertion criteria provided", "0★"),
    ],
)
def test_clinvar_download_and_annotation_integration(tmp_path, monkeypatch, Review_Status, expected_stars):
    """
    Full integration test:
    - Fake HTTP requests to provide a small gzipped ClinVar-like file.
    - Monkeypatch path logic so files go under tmp_path.
    - Run clinvar_vs_download() to generate clinvar.db.
    - Use clinvar_annotations() to look up a variant and check the result.
    - Check that the appropriate stars will be returned.
    """

    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "clinvar_functions.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))


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
        # Only redirect the *directory* app/clinvar
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # Redirect files inside clinvar
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    # 3. Run the download function (writes gz + db)
    clinvar_vs_download()

    # 4. Verify that the db files exist
    db_path = tmp_clinvar_dir / "clinvar.db"

    assert db_path.exists()

    # 5. Check DB content directly
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT nc_accession, nm_hgvs, clinical_significance, conditions, stars, review_status FROM clinvar")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 5
    (nc_acc, nm_hgvs, classification, conditions, stars, review_status) = rows[0]
    assert nc_acc == "NC_000011.10"
    assert nm_hgvs == "NM_000360.4:c.1442G>A"
    assert classification == "Pathogenic"
    # 'not provided' and 'not specified' should be removed, '|' replaced by '; '
    assert conditions == "Condition1; Condition2"
    assert stars == "★"
    assert "single submitter" in review_status

    nm_values = {r[1] for r in rows}

    assert "NM_000360.4:c.1442G>A" in nm_values
    assert "NM_000361.1:c.1A>T" in nm_values
    assert all(not v.startswith("ENST") for v in nm_values)

    # 6. Now query via clinvar_annotations using the same abspath monkeypatch
    nc_variant = "NC_000011.10:g.2164285C>T"
    nm_variant = "NM_000360.4:c.1442G>A"

    result = clinvar_annotations(nc_variant, nm_variant)

    assert result["classification"] == "Pathogenic"
    assert result["conditions"] == "Condition1; Condition2"
    assert "single submitter" in result["reviewstatus"]
    if Review_Status in result["reviewstatus"]:
        assert result["stars"] == expected_stars


# -----------------------------
# Additional unit test example: download error handling
# -----------------------------

def test_clinvar_vs_download_logs_error_on_http_failure(tmp_path, monkeypatch, caplog):
    """
    Unit-style test: simulate HTTP error (raise_for_status fails) and ensure
    an error is logged. We don't assert on side effects beyond logging.
    """

    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "clinvar_functions.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))


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
        # Only redirect the *directory* app/clinvar
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # Redirect files inside clinvar
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    status_codes = [400, 404, 408, 429, 500, 503, 504]

    for code in status_codes:

        class FakeErrorResponse:
            status_code = code

        # Fake response that raises an HTTPError
        class FakeResponse:
            def raise_for_status(self):
                err = requests.HTTPError("Simulated HTTP failure")
                err.response = FakeErrorResponse()
                raise err

        # Monkeypatch requests.get and requests.head to simulate failure
        monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse())
        monkeypatch.setattr(mod.requests, "head", lambda url: FakeResponse())

        with caplog.at_level("ERROR"):
            clinvar_vs_download()

        # Check that at least one error was logged
        assert any(f"HTTPError {code}" in rec.message for rec in caplog.records)

def test_bad_gzip_file(tmp_path, monkeypatch, caplog):

    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "clinvar_functions.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))

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
        # Only redirect the *directory* app/clinvar
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # Redirect files inside clinvar
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    monkeypatch.setattr(
        mod.gzip,
        "open",
        lambda *a, **k: (_ for _ in ()).throw(gzip.BadGzipFile("corrupt")),
    )

    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    assert any(
        f"clinvar_db_summary.txt.gz is corrupted" in rec.message
        for rec in caplog.records
    )

def test_bad_csv(tmp_path, monkeypatch, caplog):

    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "clinvar_functions.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))


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
        # Only redirect the *directory* app/clinvar
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # Redirect files inside clinvar
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    class BadCSV:
        def __iter__(self):
            raise csv.Error("bad csv")

    monkeypatch.setattr(mod.csv, "DictReader", lambda *a, **k: BadCSV())

    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    assert any(
        f"The .CSV file compressed in clinvar_db_summary.txt.gz is malformed" in rec.message
        for rec in caplog.records
    )

def test_no_disk_space(tmp_path, monkeypatch, caplog):

    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "clinvar_functions.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))

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
        # Only redirect the *directory* app/clinvar
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # Redirect files inside clinvar
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    def no_space(*a, **k):
        raise OSError(errno.ENOSPC, "No space")

    monkeypatch.setattr(mod.os, "makedirs", no_space)

    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    assert any(
        f"there is not enough disk space" in rec.message
        for rec in caplog.records
    )

def test_permission_error(tmp_path, monkeypatch, caplog):

    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "clinvar_functions.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))

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
        # Only redirect the *directory* app/clinvar
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # Redirect files inside clinvar
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    monkeypatch.setattr(
        mod.os,
        "makedirs",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError("no perms")),
    )

    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    assert any(
        f"the User lacks permissions" in rec.message
        for rec in caplog.records
    )

def test_unexpected_exception(tmp_path, monkeypatch, caplog):

    # 2. Monkeypatch abspath so the app/clinvar dir is under tmp_path
    fake_file = tmp_path / "src" / "clinvar_functions.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy module")
    monkeypatch.setattr(mod, "__file__", str(fake_file))

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
        # Only redirect the *directory* app/clinvar
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # Redirect files inside clinvar
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # otherwise fallback to original
        return original_abspath(path)

    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: 1 / 0)

    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    assert any(
        f"Failed to download variant summary record" in rec.message
        for rec in caplog.records
    )