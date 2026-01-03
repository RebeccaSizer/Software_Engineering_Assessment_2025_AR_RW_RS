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


# ----------------------------------------------------------------------------------------------
# Fake classes and functions to be help monkeypatch simulate functions from clinvar_functions.py
# ----------------------------------------------------------------------------------------------
def make_fake_clinvar_gz_bytes():
    """
    This function creates a fake clinvar gz file which contains fake information that the clinvar_vs_download() function
    would pull into the clinvar.db database. Each row is slightly nuanced to test the full functionality of
    clinvar_vs_download().

    Each row (including the headers) is a list. These rows are converted into bytes and then stored into a gzipped file
    so the file can be decompressed and parsed in accordance with clinvar_vs_download()'s functionality.
    """
    # The values in this list reflect the keys that would be referred to in the real ClinVar zip file, which store the
    # information that would be parsed into clinvar.db.
    header = [
        "ChromosomeAccession",
        "Name",
        "ClinicalSignificance",
        "PhenotypeList",
        "ReviewStatus",
    ]
    # Each row represents a different variant summary record in clinvar_db_summary.txt.gz. Most importantly, the HGVS
    # transcript nomenclature (Name), variant classification (ClinicalSignificance), associated conditions
    # (PhenotypeList) and ReviewStatus are different between each row, to test how they are parsed into clinvar.db.
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

    # A text buffer is created to act as a file in which to store information in CSV format.
    buf = io.StringIO()
    # A CSV writer is prepared to separate each row by a new line and each value in a list (row) by the tab delimiter
    # so that information can be read as a string and easily converted into bytes.
    writer = csv.writer(buf, delimiter="\t", lineterminator="\n")
    # The header list are written into the CSV file first.
    writer.writerow(header)
    # The lists in rows are written into the CSV file next.
    writer.writerows(rows)
    # The characters from 'header' and 'rows' are encoded by utf-8 into bytes.
    raw = buf.getvalue().encode("utf-8")
    # After conversion, the information can be compressed into a gzipped file.
    return gzip.compress(raw)


class FakeResponse:
    """
    This class simulates a fake response object to the requests.get python module. In effect, it is meant to simulate
    the download of the variant summary records from ClinVar.
    """
    def __init__(self, content_bytes):
        """
        This function simulates fake content and a fake header. clinvar_vs_download() pareses information from both of
        these objects when pulling information into clinvar.db.

        :param content_bytes: The content of the response is represented as bytes, not a string.
        """
        # Fake content.
        self._content = content_bytes
        # Fake HTTP headers that would typically accompany a real response. In this pretend instance, the headers are
        # blank.
        self.headers = {}

    def raise_for_status(self):
        """
        This function enables monkeypatch to pretend that everything is fine from the blank response that is has
        'received'.

        :return: None: A successful but blank response.
        """
        # Pretend everything is fine
        return None

    def iter_content(self, chunk_size=65536):
        """
        This function simulates a real download stream. It iterates over the content of the response by a designated
        chunk size. The chunk size used here is the default size and is typical for medium bandwidth.

        :param chunk_size: The size of data downloaded from the response over each iteration.

        :return: Fake data converted into chunks of 65536 bytes.
        """
        # From the start to the end of the content, split the data up into chunks of 65536 bytes and iterate through
        # each chunk.
        for i in range(0, len(self._content), chunk_size):
            # Yield the data to 'self'.
            yield self._content[i : i + chunk_size]


class FakeHeadResponse:
    """
    Fake response for requests.head. clinvar_vs_download() stores the date that the variant summary records were last
    modified and stores the information in a table, in clinvar.db. The date is extracted from the 'Last-Modified'
    headers object in the response.
    """
    def __init__(self):
        """
        This function simulates a fake date in a fake 'Last-Modified' header object.
        """
        self.headers = {"Last-Modified": "Sun, 16 Nov 2025 22:54:32 GMT"}

# ---------------------------------
# Pytests for clinvar_functions.py
# ---------------------------------
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
    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath.
    # <tmp>/app/clinvar/clinvar.db
    app_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'app_dir' filepath.
    app_dir.mkdir(parents=True)
    # Create a filepath to the clinvar.db file in the fake filepath.
    db_path = app_dir / "clinvar.db"

    # Create a fake connection to an SQL database with minimal conformity with the expected schema.
    conn = sqlite3.connect(db_path)
    # Execute SQLite3 commands in Python.
    cur = conn.cursor()
    # Simulate the creation of the clinvar table with the same headers as the real clinvar table.
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
    # Insert a single test record in the clinvar table.
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
    # Commit the insertion.
    conn.commit()
    # Close the connection.
    conn.close()

    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # The SQLite3 connect module is assigned to a variable.
    _real_connect = sqlite3.connect
    # Monkeypatch simulates the connection to the fake clinvar.db database from this test script, whenever the real
    # functions in clinvar_functions.py attempts to create a real sqlite3 connection.
    monkeypatch.setattr(
        mod.sqlite3,
        "connect",
        lambda path, *a, **kw: _real_connect(str(db_path))
    )

    # A set of variables required by the clinvar_annotations() function. These values conform with the fake entry
    # inserted into the clinvar table earlier.
    nc_variant = "NC_000011.10:g.2164285C>T"
    nm_variant = "NM_000360.4:c.1442G>A"

    # The output from clinvar_annotations() function is assigned to the 'result' variable.
    result = clinvar_annotations(nc_variant, nm_variant)

    # Test that clinvar_annotations returned a Python dictionary-type response.
    assert isinstance(result, dict)
    # Test that the classification, conditions and review status are as expected.
    assert result["classification"] == "Pathogenic"
    assert result["conditions"] == "Condition1; Condition2"
    assert "single submitter" in result["reviewstatus"]
    # Create an if statement that checks that the correct star value was returned, based on the review status
    # parameterised by the pytest fixture.
    if Review_Status in result["reviewstatus"]:
        assert result["stars"] == expected_stars

def test_clinvar_annotations_not_found(tmp_path, monkeypatch):
    """
    Unit test for clinvar_annotations when no record is found:
    should return a 'not found' string.
    """
    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath.
    # <tmp>/app/clinvar/clinvar.db
    app_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'app_dir' filepath.
    app_dir.mkdir(parents=True)
    # Create a filepath to the clinvar.db file in the fake filepath.
    db_path = app_dir / "clinvar.db"

    # Create a fake connection to an SQL database with minimal conformity with the expected schema.
    conn = sqlite3.connect(db_path)
    # Execute SQLite3 commands in Python.
    cur = conn.cursor()
    # Simulate the creation of the clinvar table with the same headers as the real clinvar table.
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
    # Commit the insertion.
    conn.commit()
    # Close the connection.
    conn.close()

    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # The SQLite3 connect module is assigned to a variable.
    _real_connect = sqlite3.connect
    # Monkeypatch simulates the connection to the fake clinvar.db database from this test script, whenever the real
    # functions in clinvar_functions.py attempts to create a real sqlite3 connection.
    monkeypatch.setattr(
        mod.sqlite3,
        "connect",
        lambda path, *a, **kw: _real_connect(str(db_path))
    )

    # A set of variables required by the clinvar_annotations() function. These values do not conform with anything in
    # the clinvar table earlier because nothing was inserted into the table.
    nc_variant = "NC_000011.10:g.2164285C>T"
    nm_variant = "NM_000360.4:c.1442G>A"

    # The output from clinvar_annotations() function is assigned to the 'result' variable.
    result = clinvar_annotations(nc_variant, nm_variant)

    # Test that the response is a string datatype, suggesting that an error message was returned.
    assert isinstance(result, str)
    # Test that the expected error message was returned for when the query variant summary record cannot be found.
    assert f"Could not find {nc_variant} variant summary record in clinvar.db" in result


def test_clinvar_annotations_db_error(tmp_path, monkeypatch, caplog):
    """
    Unit test: simulate a DB query error by monkeypatching sqlite3.connect.
    """
    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath
    # to a directory where the fake gzipped variant summary record file from ClinVar can be found:
    # <tmp>/app/clinvar/
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'tmp_clinvar_dir' filepath.
    tmp_clinvar_dir.mkdir(parents=True)

    # Use the make_fake_clinvar_gz_bytes function to create a fake gzipped variant summary record file from ClinVar.
    fake_gz = make_fake_clinvar_gz_bytes()

    # Monkeypatch simulates a fake download of the fake gzipped variant summary record file from ClinVar, using the
    # FakeResponse class. This response is returned whenever the requests.get function is used in clinvar_functions.py.
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    # Monkeypatch also simulates the return of the date the summary records were last modified, using the
    # FakeHeadResponse class.
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    # It is good practice to keep a reference of the original path (from ChatGPT).
    original_abspath = os.path.abspath

    def fake_abspath(path):
        """
        This function creates a fake absolute path to the clinvar_db_summary.txt.gz and clinvar.db files, at the
        end of the tmp_clinvar_dir filepaths. It can also return a fake absolute path to the clinvar directory in which
        they are stored. This is to help monkeypatch and simulate a test environment without interfering with the
        original files.

        :param path: A filepath that is used to return the filepath to either the clivar directory, the
                     clinvar_db_summary.txt.gz or the clinvar.db database file.

        :return: An absolute path to the fake clinvar directory, fake clinvar_db_summary.txt.gz or the fake clinvar.db
                 database file
        """
        # The path is converted into a string.
        path = str(path)
        # If the path ends with "app/clinvar", return a fake absolute path to the clinvar directory using
        # tmp_clinvar_dir.
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # If the path ends with "clinvar_db_summary.txt.gz", return a fake absolute path to the gzipped file using
        # tmp_clinvar_dir.
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        # If the path ends with "clinvar.db", return a fake absolute path to the clinvar.db database file using
        # tmp_clinvar_dir.
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # Otherwise fallback to the original filepath.
        return original_abspath(path)

    # Monkeypatch the return of a fake filepath using the fake_abspath function, whenever os.path is called in
    # clinvar_functions.py
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    class FailingConnection:
        """
        Simulate a failing connection class that ultimately raises an sqlite3.OperationalError exception. This is used
        to test if the sqlite_error error handler works in clinvar_functions.py.
        """
        def cursor(self):
            """
            This function acts as a cursor which raises the sqlite3.OperationalError exception.

            :return:Raise the sqlite3.OperationalError exception with the error message, "boom".
            """
            # Raise the exception.
            raise sqlite3.OperationalError("boom")

    def fake_connect(path):
        """
        This function creates a fake SQLite3 connection so that the sqlite3.OperationalError exception is raised using
        the FailingConnection class.

        :param path: A path to an SQLite3 database file.

        :return: FailingConnection class: The function of this class is to raise a fake sqlite3.OperationalError
                                          exception.
        """
        # Call the FailingConnection class object.
        return FailingConnection()

    # Monkeypatch simulates the fake sqlite3.OperationalError exception using the fake_connect() function, when the
    # sqlite3 module is used in clinvar_functions.py.
    monkeypatch.setattr(mod.sqlite3, "connect", fake_connect)

    # Pytest's caplog fixture captures the log messages set at the 'ERROR' level, in the clinvar_vs_download() function
    # from clinvar_functions.py.
    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    # Test that the logged error message captured by caplog, is as expected.
    assert any(
        f"sqlite3.OperationalError: clinvar.db is not working properly:" in rec.message
        for rec in caplog.records
    )

    def fake_abspath(path):
        """
        This function is used to simply provide a fake filepath to help monkeypatch satisfy the os.path function from
        clinvar_functions.py, so that the flash error message returned to the User can also be tested.
        :param path: Any filepath.
        :return: fake filepath: "/tmp/fake_module.py"
        """
        # Return the fake filepath.
        return "/tmp/fake_module.py"

    # Monkeypatch pretends to return the fake filepath from fake_abspath, to simulate the process leading up to the
    # return of the flash error message.
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    # A set of variables required by the clinvar_annotations() function. These values do not conform with anything in
    # the clinvar table earlier because nothing was inserted into the table.
    result = clinvar_annotations(
        "NC_000011.10:g.2164285C>T", "NM_000360.4:c.1442G>A"
    )
    # Test that the response is a string datatype, suggesting that an error message was returned.
    assert isinstance(result, str)
    # Test that the expected flash error message was returned when an sqlite3.OperationalError exception is raised.
    assert "❌ clinvar.db query error: Something went wrong while accessing the database." in result


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
    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath
    # to a directory where the fake gzipped variant summary record file from ClinVar can be found:
    # <tmp>/app/clinvar/
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'tmp_clinvar_dir' filepath.
    tmp_clinvar_dir.mkdir(parents=True)

    # Use the make_fake_clinvar_gz_bytes function to create a fake gzipped variant summary record file from ClinVar.
    fake_gz = make_fake_clinvar_gz_bytes()

    # Monkeypatch simulates a fake download of the fake gzipped variant summary record file from ClinVar, using the
    # FakeResponse class. This response is returned whenever the requests.get function is used in clinvar_functions.py.
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    # Monkeypatch also simulates the return of the date the summary records were last modified, using the
    # FakeHeadResponse class.
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    # It is good practice to keep a reference of the original path (from ChatGPT).
    original_abspath = os.path.abspath

    def fake_abspath(path):
        """
        This function creates a fake absolute path to the clinvar_db_summary.txt.gz and clinvar.db files, at the
        end of the tmp_clinvar_dir filepaths. It can also return a fake absolute path to the clinvar directory in which
        they are stored. This is to help monkeypatch simulate a test environment without interfering with the
        original files.

        :param path: A filepath that is used to return the filepath to either the clivar directory, the
                     clinvar_db_summary.txt.gz or the clinvar.db database file.

        :return: An absolute path to the fake clinvar directory, fake clinvar_db_summary.txt.gz or the fake clinvar.db
                 database file
        """
        # The path is converted into a string.
        path = str(path)
        # If the path ends with "app/clinvar", return a fake absolute path to the clinvar directory using
        # tmp_clinvar_dir.
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # If the path ends with "clinvar_db_summary.txt.gz", return a fake absolute path to the gzipped file using
        # tmp_clinvar_dir.
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        # If the path ends with "clinvar.db", return a fake absolute path to the clinvar.db database file using
        # tmp_clinvar_dir.
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # Otherwise fallback to the original filepath.
        return original_abspath(path)

    # Monkeypatch the return of a fake filepath using the fake_abspath function, when os.path is called in
    # clinvar_functions.py
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    # Run the clinvar_vs_download() function from clinvar_functions.py.
    mod.clinvar_vs_download()

    # Assign the path to the newly created clinvar.db to 'db_path'.
    db_path = tmp_clinvar_dir / "clinvar.db"

    # Test that the path to 'clinvar.db' exists, proving that it was successfully downloaded.
    assert db_path.exists()

    # Create a connection to clinvar.db database with minimal conformity with the expected schema.
    conn = sqlite3.connect(db_path)
    # Execute SQLite3 commands in Python.
    cur = conn.cursor()
    # Execute the SQLite SELECT command to extract the values from the corresponding headers, in the clinvar table.
    cur.execute("SELECT nc_accession, nm_hgvs, clinical_significance, conditions, stars, review_status FROM clinvar")
    # Return the entries from the above query to the rows variable.
    rows = cur.fetchall()
    # Close the connection to the clinvar.db database.
    conn.close()

    # 6 rows returned from the make_fake_clinvar_gz_bytes() function, however, one should have been ignored because it
    # included an Ensembl transcript number. Therefore, the number of rows returned by the above SQL query should be 5.
    assert len(rows) == 5

    # Parse the values from the first row into the variables: nc_acc, nm_hgvs, classification, conditions, stars and
    # review_status.
    (nc_acc, nm_hgvs, classification, conditions, stars, review_status) = rows[0]
    # Test that the values from in the first row appeared under the appropriate headers, in the clinvar.db.
    assert nc_acc == "NC_000011.10"
    assert nm_hgvs == "NM_000360.4:c.1442G>A"
    assert classification == "Pathogenic"
    # The conditions from the first row returned by make_fake_clinvar_gz_bytes() were "Condition1;Condition2; not
    # specified". clinvar_vs_download should have removed 'not specified' and the ';' after Condition2 when populating
    # clinvar.db with that row.
    assert conditions == "Condition1; Condition2"
    assert stars == "★"
    assert "single submitter" in review_status

    # Collect all of the values under the 'nm_hgvs' header in clinvar.db and assign them to the 'nm_values' variable.
    nm_values = {r[1] for r in rows}
    # Test that normal HGVS transcript nomenclature can be parsed correctly into the appropriate field, in clinvar.db.
    assert "NM_000360.4:c.1442G>A" in nm_values
    # Test that a HGVS transcript nomenclature that included the gene symbol, can be parsed correctly into the
    # appropriate field, in clinvar.db.
    assert "NM_000361.1:c.1A>T" in nm_values
    # Test that none of the rows with an Ensembl transcript numbers were entered into clinvar.db.
    assert all(not v.startswith("ENST") for v in nm_values)

    # A set of variables required by the clinvar_annotations() function. These values conform with one of the rows
    # returned by make_fake_clinvar_gz_bytes(). Therefore a corresponding fake variant summary record should have been
    # found in the clinvar table earlier.
    nc_variant = "NC_000011.10:g.2164285C>T"
    nm_variant = "NM_000360.4:c.1442G>A"

    # Run the clinvar_annotations function, using the previous values.
    result = clinvar_annotations(nc_variant, nm_variant)

    # Test that the appropriate variant summary record in the clinvar.db was returned.
    assert result["classification"] == "Pathogenic"
    assert result["conditions"] == "Condition1; Condition2"
    assert "single submitter" in result["reviewstatus"]
    # Create an if statement that checks that the correct star value entered into the clinvar.db database, based on the
    # review status parameterised by the pytest fixture.
    if Review_Status in result["reviewstatus"]:
        assert result["stars"] == expected_stars

def test_clinvar_vs_download_logs_error_on_http_failure(tmp_path, monkeypatch, caplog):
    """
    Unit-style test: simulate HTTP error (raise_for_status fails) and ensure
    an error is logged. We don't assert on side effects beyond logging.
    """
    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath
    # to a directory where the fake gzipped variant summary record file from ClinVar can be found:
    # <tmp>/app/clinvar/
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'tmp_clinvar_dir' filepath.
    tmp_clinvar_dir.mkdir(parents=True)

    # Use the make_fake_clinvar_gz_bytes function to create a fake gzipped variant summary record file from ClinVar.
    fake_gz = make_fake_clinvar_gz_bytes()

    # Monkeypatch simulates a fake download of the fake gzipped variant summary record file from ClinVar, using the
    # FakeResponse class. This response is returned whenever the requests.get function is used in clinvar_functions.py.
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    # Monkeypatch also simulates the return of the date the summary records were last modified, using the
    # FakeHeadResponse class.
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    # It is good practice to keep a reference of the original path (from ChatGPT).
    original_abspath = os.path.abspath

    def fake_abspath(path):
        """
        This function creates a fake absolute path to the clinvar_db_summary.txt.gz and clinvar.db files, at the
        end of the tmp_clinvar_dir filepaths. It can also return a fake absolute path to the clinvar directory in which
        they are stored. This is to help monkeypatch simulate a test environment without interfering with the
        original files.

        :param path: A filepath that is used to return the filepath to either the clivar directory, the
                     clinvar_db_summary.txt.gz or the clinvar.db database file.

        :return: An absolute path to the fake clinvar directory, fake clinvar_db_summary.txt.gz or the fake clinvar.db
                 database file
        """
        # The path is converted into a string.
        path = str(path)
        # If the path ends with "app/clinvar", return a fake absolute path to the clinvar directory using
        # tmp_clinvar_dir.
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # If the path ends with "clinvar_db_summary.txt.gz", return a fake absolute path to the gzipped file using
        # tmp_clinvar_dir.
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        # If the path ends with "clinvar.db", return a fake absolute path to the clinvar.db database file using
        # tmp_clinvar_dir.
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # Otherwise fallback to the original filepath.
        return original_abspath(path)

    # Monkeypatch the return of a fake filepath using the fake_abspath function, when os.path is called in
    # clinvar_functions.py
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    # List the response status code of the HTTPErrors that are handled in error_handlers.py.
    status_codes = [400, 404, 408, 429, 500, 503, 504]
    # Iterate over each status code.
    for code in status_codes:

        class FakeErrorResponse:
            """
            This class assigns each status code to the variable 'status_code'. This is to return a fake response status
            code.
            """
            status_code = code

        class FakeResponse:
            """
            Fake response class that raises a HTTPError from the FakeErrorResponse status code.
            """
            def raise_for_status(self):
                """
                This function raises a HTTPError with the FakeErrorResponse status code, and the error message,
                "Simulated HTTP failure"

                :return: err: The HTTPError with corresponding status code.
                """
                # Raise the requests.HTTPError exception.
                err = requests.HTTPError("Simulated HTTP failure")
                # Assign the status code from FakeErrorResponse to the requests.HTTPError exception.
                err.response = FakeErrorResponse()
                # Return the error.
                raise err

        # Monkeypatch simulates error handling of the HTTPError raised when the requests.get function is used in
        # clinvar_vs_download, in clinvar_functions.py, using the FakeResponse class.
        monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse())
        # Monkeypatch also simulates the return of the date the summary records were last modified, using the
        # FakeHeadResponse class.
        monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

        # Pytest's caplog fixture captures the log messages set at the 'ERROR' level, in the clinvar_vs_download()
        # function from clinvar_functions.py.
        with caplog.at_level("ERROR"):
            mod.clinvar_vs_download()

        # Test that the logged error message captured by caplog, is as expected.
        assert any(f"HTTPError {code}" in rec.message for rec in caplog.records)

def test_bad_gzip_file(tmp_path, monkeypatch, caplog):
    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath
    # to a directory where the fake gzipped variant summary record file from ClinVar can be found:
    # <tmp>/app/clinvar/
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'tmp_clinvar_dir' filepath.
    tmp_clinvar_dir.mkdir(parents=True)

    # Use the make_fake_clinvar_gz_bytes function to create a fake gzipped variant summary record file from ClinVar.
    fake_gz = make_fake_clinvar_gz_bytes()

    # Monkeypatch simulates a fake download of the fake gzipped variant summary record file from ClinVar, using the
    # FakeResponse class. This response is returned whenever the requests.get function is used in clinvar_functions.py.
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    # Monkeypatch also simulates the return of the date the summary records were last modified, using the
    # FakeHeadResponse class.
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    # It is good practice to keep a reference of the original path (from ChatGPT).
    original_abspath = os.path.abspath

    def fake_abspath(path):
        """
        This function creates a fake absolute path to the clinvar_db_summary.txt.gz and clinvar.db files, at the
        end of the tmp_clinvar_dir filepaths. It can also return a fake absolute path to the clinvar directory in which
        they are stored. This is to help monkeypatch and simulate a test environment without interfering with the
        original files.

        :param path: A filepath that is used to return the filepath to either the clivar directory, the
                     clinvar_db_summary.txt.gz or the clinvar.db database file.

        :return: An absolute path to the fake clinvar directory, fake clinvar_db_summary.txt.gz or the fake clinvar.db
                 database file
        """
        # The path is converted into a string.
        path = str(path)
        # If the path ends with "app/clinvar", return a fake absolute path to the clinvar directory using
        # tmp_clinvar_dir.
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # If the path ends with "clinvar_db_summary.txt.gz", return a fake absolute path to the gzipped file using
        # tmp_clinvar_dir.
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        # If the path ends with "clinvar.db", return a fake absolute path to the clinvar.db database file using
        # tmp_clinvar_dir.
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # Otherwise fallback to the original filepath.
        return original_abspath(path)

    # Monkeypatch the return of a fake filepath using the fake_abspath function, whenever os.path is called in
    # clinvar_functions.py
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)
    # Monkeypatch raises the gzip.BadGzipFile exception with the error message, "corrupt" when the
    # clinvar_db_summary.txt.gz file is being read during the clinvar_vs_downloaded() function from clinvar_functions.py.
    # This should raise the corresponding error handler and generate the corresponding log message.
    monkeypatch.setattr(
        mod.gzip,
        "open",
        lambda *a, **k: (_ for _ in ()).throw(gzip.BadGzipFile("corrupt")),
    )

    # Pytest's caplog fixture captures the log messages set at the 'ERROR' level, in the clinvar_vs_download()
    # function from clinvar_functions.py.
    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    # Test that the logged error message captured by caplog, is as expected.
    assert any(
        f"clinvar_db_summary.txt.gz is corrupted" in rec.message
        for rec in caplog.records
    )

def test_bad_csv(tmp_path, monkeypatch, caplog):
    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath
    # to a directory where the fake gzipped variant summary record file from ClinVar can be found:
    # <tmp>/app/clinvar/
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'tmp_clinvar_dir' filepath.
    tmp_clinvar_dir.mkdir(parents=True)

    # Use the make_fake_clinvar_gz_bytes function to create a fake gzipped variant summary record file from ClinVar.
    fake_gz = make_fake_clinvar_gz_bytes()

    # Monkeypatch simulates a fake download of the fake gzipped variant summary record file from ClinVar, using the
    # FakeResponse class. This response is returned whenever the requests.get function is used in clinvar_functions.py.
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    # Monkeypatch also simulates the return of the date the summary records were last modified, using the
    # FakeHeadResponse class.
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    # It is good practice to keep a reference of the original path (from ChatGPT).
    original_abspath = os.path.abspath

    def fake_abspath(path):
        """
        This function creates a fake absolute path to the clinvar_db_summary.txt.gz and clinvar.db files, at the
        end of the tmp_clinvar_dir filepaths. It can also return a fake absolute path to the clinvar directory in which
        they are stored. This is to help monkeypatch and simulate a test environment without interfering with the
        original files.

        :param path: A filepath that is used to return the filepath to either the clivar directory, the
                     clinvar_db_summary.txt.gz or the clinvar.db database file.

        :return: An absolute path to the fake clinvar directory, fake clinvar_db_summary.txt.gz or the fake clinvar.db
                 database file
        """
        # The path is converted into a string.
        path = str(path)
        # If the path ends with "app/clinvar", return a fake absolute path to the clinvar directory using
        # tmp_clinvar_dir.
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # If the path ends with "clinvar_db_summary.txt.gz", return a fake absolute path to the gzipped file using
        # tmp_clinvar_dir.
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        # If the path ends with "clinvar.db", return a fake absolute path to the clinvar.db database file using
        # tmp_clinvar_dir.
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # Otherwise fallback to the original filepath.
        return original_abspath(path)

    # Monkeypatch the return of a fake filepath using the fake_abspath function, whenever os.path is called in
    # clinvar_functions.py
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    class BadCSV:
        """
        This class raises a csv.Error with the error message, "bad csv". This is raised in response to a fake but
        irregular CSV file compressed in the clinvar_db_summary.txt.gz file.
        """
        def __iter__(self):
            """
            This function raises the csv.Error with the error message, "bad csv".
            """
            # Raise the csv.Error and error message.
            raise csv.Error("bad csv")

    # Monkeypatch raises the csv.Error exception when the CSV content from the clinvar_db_summary.txt.gz file is being
    # read during the clinvar_vs_downloaded() function from clinvar_functions.py. This should raise the corresponding
    # error handler and generate the corresponding log message.
    monkeypatch.setattr(mod.csv, "DictReader", lambda *a, **k: BadCSV())

    # Pytest's caplog fixture captures the log messages set at the 'ERROR' level, in the clinvar_vs_download()
    # function from clinvar_functions.py.
    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    # Test that the logged error message captured by caplog, is as expected.
    assert any(
        f"The .CSV file compressed in clinvar_db_summary.txt.gz is malformed" in rec.message
        for rec in caplog.records
    )

def test_no_disk_space(tmp_path, monkeypatch, caplog):
    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath
    # to a directory where the fake gzipped variant summary record file from ClinVar can be found:
    # <tmp>/app/clinvar/
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'tmp_clinvar_dir' filepath.
    tmp_clinvar_dir.mkdir(parents=True)

    # Use the make_fake_clinvar_gz_bytes function to create a fake gzipped variant summary record file from ClinVar.
    fake_gz = make_fake_clinvar_gz_bytes()

    # Monkeypatch simulates a fake download of the fake gzipped variant summary record file from ClinVar, using the
    # FakeResponse class. This response is returned whenever the requests.get function is used in clinvar_functions.py.
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    # Monkeypatch also simulates the return of the date the summary records were last modified, using the
    # FakeHeadResponse class.
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    # It is good practice to keep a reference of the original path (from ChatGPT).
    original_abspath = os.path.abspath

    def fake_abspath(path):
        """
        This function creates a fake absolute path to the clinvar_db_summary.txt.gz and clinvar.db files, at the
        end of the tmp_clinvar_dir filepaths. It can also return a fake absolute path to the clinvar directory in which
        they are stored. This is to help monkeypatch and simulate a test environment without interfering with the
        original files.

        :param path: A filepath that is used to return the filepath to either the clivar directory, the
                     clinvar_db_summary.txt.gz or the clinvar.db database file.

        :return: An absolute path to the fake clinvar directory, fake clinvar_db_summary.txt.gz or the fake clinvar.db
                 database file
        """
        # The path is converted into a string.
        path = str(path)
        # If the path ends with "app/clinvar", return a fake absolute path to the clinvar directory using
        # tmp_clinvar_dir.
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # If the path ends with "clinvar_db_summary.txt.gz", return a fake absolute path to the gzipped file using
        # tmp_clinvar_dir.
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        # If the path ends with "clinvar.db", return a fake absolute path to the clinvar.db database file using
        # tmp_clinvar_dir.
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # Otherwise fallback to the original filepath.
        return original_abspath(path)

    # Monkeypatch the return of a fake filepath using the fake_abspath function, whenever os.path is called in
    # clinvar_functions.py
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)

    def no_space(*a, **k):
        """
        This function raises the ENOSPC exception from the OSError class of exceptins.
        """
        # Raise the ENOSPC exception with the error message, "No space".
        raise OSError(errno.ENOSPC, "No space")

    # Monkeypatch raises the ENOSPC exception when the 'os' Python module attempts to make a file during the
    # clinvar_vs_downloaded() function from clinvar_functions.py. This should raise the corresponding error handler and
    # generate the corresponding log message.
    monkeypatch.setattr(mod.os, "makedirs", no_space)

    # Pytest's caplog fixture captures the log messages set at the 'ERROR' level, in the clinvar_vs_download()
    # function from clinvar_functions.py.
    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    # Test that the logged error message captured by caplog, is as expected.
    assert any(
        f"there is not enough disk space" in rec.message
        for rec in caplog.records
    )

def test_permission_error(tmp_path, monkeypatch, caplog):
    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath
    # to a directory where the fake gzipped variant summary record file from ClinVar can be found:
    # <tmp>/app/clinvar/
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'tmp_clinvar_dir' filepath.
    tmp_clinvar_dir.mkdir(parents=True)

    # Use the make_fake_clinvar_gz_bytes function to create a fake gzipped variant summary record file from ClinVar.
    fake_gz = make_fake_clinvar_gz_bytes()

    # Monkeypatch simulates a fake download of the fake gzipped variant summary record file from ClinVar, using the
    # FakeResponse class. This response is returned whenever the requests.get function is used in clinvar_functions.py.
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    # Monkeypatch also simulates the return of the date the summary records were last modified, using the
    # FakeHeadResponse class.
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    # It is good practice to keep a reference of the original path (from ChatGPT).
    original_abspath = os.path.abspath

    def fake_abspath(path):
        """
        This function creates a fake absolute path to the clinvar_db_summary.txt.gz and clinvar.db files, at the
        end of the tmp_clinvar_dir filepaths. It can also return a fake absolute path to the clinvar directory in which
        they are stored. This is to help monkeypatch and simulate a test environment without interfering with the
        original files.

        :param path: A filepath that is used to return the filepath to either the clivar directory, the
                     clinvar_db_summary.txt.gz or the clinvar.db database file.

        :return: An absolute path to the fake clinvar directory, fake clinvar_db_summary.txt.gz or the fake clinvar.db
                 database file
        """
        # The path is converted into a string.
        path = str(path)
        # If the path ends with "app/clinvar", return a fake absolute path to the clinvar directory using
        # tmp_clinvar_dir.
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # If the path ends with "clinvar_db_summary.txt.gz", return a fake absolute path to the gzipped file using
        # tmp_clinvar_dir.
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        # If the path ends with "clinvar.db", return a fake absolute path to the clinvar.db database file using
        # tmp_clinvar_dir.
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # Otherwise fallback to the original filepath.
        return original_abspath(path)

    # Monkeypatch the return of a fake filepath using the fake_abspath function, whenever os.path is called in
    # clinvar_functions.py
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)
    # Monkeypatch raises the PermissionError exception with the error message "no perms" when the 'os' Python module
    # attempts to make a file during the clinvar_vs_downloaded() function from clinvar_functions.py. This should raise
    # the corresponding error handler and generate the corresponding log message.
    monkeypatch.setattr(
        mod.os,
        "makedirs",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError("no perms")),
    )

    # Pytest's caplog fixture captures the log messages set at the 'ERROR' level, in the clinvar_vs_download()
    # function from clinvar_functions.py.
    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    # Test that the logged error message captured by caplog, is as expected.
    assert any(
        f"the User lacks permissions" in rec.message
        for rec in caplog.records
    )

def test_unexpected_exception(tmp_path, monkeypatch, caplog):
    # Create a fake filepath to a fake Python script.
    fake_file = tmp_path / "src" / "module.py"
    # Simulate the creation of the directories leading to the fake Python script.
    fake_file.parent.mkdir(parents=True)
    # Insert random text inside of the fake Python file.
    fake_file.write_text("# dummy module")
    # Monkeypatch simulates the use of the fake Python file by redirecting functions from clinvar_functions.py (mod) to
    # the fake file.
    monkeypatch.setattr(mod, "__file__", str(fake_file))

    # Build temporary directory structure from within the fake pytest fixture, tmp_path, that simulates a real filepath
    # to a directory where the fake gzipped variant summary record file from ClinVar can be found:
    # <tmp>/app/clinvar/
    tmp_clinvar_dir = tmp_path / "app" / "clinvar"
    # Create the directories in the fake 'tmp_clinvar_dir' filepath.
    tmp_clinvar_dir.mkdir(parents=True)

    # Use the make_fake_clinvar_gz_bytes function to create a fake gzipped variant summary record file from ClinVar.
    fake_gz = make_fake_clinvar_gz_bytes()

    # Monkeypatch simulates a fake download of the fake gzipped variant summary record file from ClinVar, using the
    # FakeResponse class. This response is returned whenever the requests.get function is used in clinvar_functions.py.
    monkeypatch.setattr(mod.requests, "get", lambda url, stream=True: FakeResponse(fake_gz))
    # Monkeypatch also simulates the return of the date the summary records were last modified, using the
    # FakeHeadResponse class.
    monkeypatch.setattr(mod.requests, "head", lambda url: FakeHeadResponse())

    # It is good practice to keep a reference of the original path (from ChatGPT).
    original_abspath = os.path.abspath

    def fake_abspath(path):
        """
        This function creates a fake absolute path to the clinvar_db_summary.txt.gz and clinvar.db files, at the
        end of the tmp_clinvar_dir filepaths. It can also return a fake absolute path to the clinvar directory in which
        they are stored. This is to help monkeypatch and simulate a test environment without interfering with the
        original files.

        :param path: A filepath that is used to return the filepath to either the clivar directory, the
                     clinvar_db_summary.txt.gz or the clinvar.db database file.

        :return: An absolute path to the fake clinvar directory, fake clinvar_db_summary.txt.gz or the fake clinvar.db
                 database file
        """
        # The path is converted into a string.
        path = str(path)
        # If the path ends with "app/clinvar", return a fake absolute path to the clinvar directory using
        # tmp_clinvar_dir.
        if path.endswith(os.path.join("app", "clinvar")):
            return str(tmp_clinvar_dir)
        # If the path ends with "clinvar_db_summary.txt.gz", return a fake absolute path to the gzipped file using
        # tmp_clinvar_dir.
        if "clinvar_db_summary.txt.gz" in path:
            return str(tmp_clinvar_dir / "clinvar_db_summary.txt.gz")
        # If the path ends with "clinvar.db", return a fake absolute path to the clinvar.db database file using
        # tmp_clinvar_dir.
        if path.endswith("clinvar.db"):
            return str(tmp_clinvar_dir / "clinvar.db")
        # Otherwise fallback to the original filepath.
        return original_abspath(path)

    # Monkeypatch the return of a fake filepath using the fake_abspath function, whenever os.path is called in
    # clinvar_functions.py
    monkeypatch.setattr(mod.os.path, "abspath", fake_abspath)
    # Monkeypatch simulates infinity is returned when the requests.get function in clinvar_vs_downloaded() from
    # clinvar_functions.py is activated, raising the generic Exceptions error handler.
    monkeypatch.setattr(mod.requests, "get", lambda *a, **k: 1 / 0)

    # Pytest's caplog fixture captures the log messages set at the 'ERROR' level, in the clinvar_vs_download()
    # function from clinvar_functions.py.
    with caplog.at_level("ERROR"):
        mod.clinvar_vs_download()

    # Test that the logged error message captured by caplog, is as expected.
    assert any(
        f"Failed to download variant summary record" in rec.message
        for rec in caplog.records
    )