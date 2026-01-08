"""
Unit tests for app (app/app.py).

This module contains pytest-based tests that verify correct behaviour
and error handling for functions in app. Some external
dependencies such as databases, files, and network requests are mocked
using pytest fixtures (e.g. monkeypatch) to ensure deterministic and
isolated testing.

Some tests were initially generated with assistance from ChatGPT and
subsequently refined by the developer.
"""

import csv
import json
import errno
import pytest
import sqlite3
import werkzeug
from io import BytesIO
from flask import flash
from app.app import app
from tools.utils.logger import logger
from tools.modules.database_functions import (
    patient_variant_table,
    variant_annotations_table,
    validate_database,
    query_db
)

# ----------------------------------------------------------------
# Pytest fixtures
# ----------------------------------------------------------------
@pytest.fixture
def flask_app():
    """
    This function prepares a fake environment to run our flask app for monkeypatch pytesting.
    Flask_app makes the app callable in subsequent pytests where monkeypatch is used to emulate the app.
    """

    # This dictionary like object changes the flask app configuration.
    app.config.update({
        # The flask app is switch to 'test mode'.
        "TESTING": True,
        # Access to apps typically use a token which represents the User's identification and their activity.
        # This is disabled so that a fake environment can be created to execute pytests.
        "WTF_CSRF_ENABLED": False
    })

    # The app is returned.
    return app

@pytest.fixture
def client(flask_app):
    """
    This function prepares a fake flask app test client for monkeypatch pytesting. This allows GET and POST requests to
    be pytested.

    :params: flask_app: The output from the flask_app pytest fixture. This is essentially a testable version of our
                        flask app.

    :output: flask_app.test_client(): A fake flask app test client.
    """
    # Return the fake flask app test client.
    return flask_app.test_client()

# ----------------------------------------------------------------
# Exceptions for testing app.py:
#   - PermissionError
#   - ENOSPC
#   - OSError
#   - General exception
#   - SQLite3.DatabaseError
#   - SQLite3.OperationalError
#   - json.JSONDecodeError
#   - csv.Error
# ----------------------------------------------------------------
def raise_permission(*args, **kwargs):
    """
    Function raises the PermissionError exception. This error occurs when the User does not have permission to use a
    file.
    """
    # Raise the exception with the error message, "no permission".
    raise PermissionError("no permission")

def raise_enospc(*args, **kwargs):
    """
    Function raises the OSError exception: ENOSPC. This error occurs when there is no more disk space to store a file.
    """
    # Raise the exception with the error message, "No space".
    raise OSError(errno.ENOSPC, "No space")

def raise_oserror(*args, **kwargs):
    """
    Function raises OSError exceptions. This error occurs when there is an issue with the Operating System.
    """
    # Raise the exception with the error message, "IO error".
    raise OSError(errno.EIO, "IO error")

def raise_generic(*args, **kwargs):
    """
    Function raises all exceptions that were not captured by previous error handlers.
    """
    # Raise th exception with the error message, "unexpected".
    raise Exception("unexpected")

def raise_sqlite_de(*args, **kwargs):
    """
    Function raises the sqlite3.DatabaseError exception. It occurs when databases cannot be processed.
    """
    # Raise the exception with the error message, "bad db".
    raise sqlite3.DatabaseError("bad db")

def raise_sqlite_oe(*args, **kwargs):
    """
    Function raises the sqlite3.OperationalError exception. It occurs when SQLite3 is not functioning correctly.
    """
    # Raise the exception with the error message, "cannot open".
    raise sqlite3.OperationalError("cannot open")

def raise_json_error(*args, **kwargs):
    """
    Function raises the json.JSONDecodeError exception. It occurs when the python module 'json' cannot use its 'load(s)'
    function to parse the content from a json into a python dictionary.
    """
    # Raise the exception with the error message, "bad json".
    raise json.JSONDecodeError("bad json", "", 0)

def raise_csv_error(*args, **kwargs):
    """
    Function raises the csv.Error exception. It occurs when the python module 'csv' cannot write content into CSV
    format.
    """
    # Raise the exception with the error message, "write failed".
    raise csv.Error("write failed")

# ----------------------------------------------------------------
# Test Homepage-GET: files removed from temp folder.
# ----------------------------------------------------------------
def test_homepage_cleans_temp_folder(client, monkeypatch):
    """
    This function tests if the route to the homepage in app.py adequately removes .VCF and .CSV file from the 'temp'
    folder, as soon as the flask app has been initialised.
    Monkeypatch creates a fake path to two fake files: one VCF and one CSV.

    :param: client: A fake test client generated by the 'client' pytest fixture.
            monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be
                         altered without changing the original attributes and variables being used.

    :test outcomes: Test that a response was received successfully (status code 200).
                    Test that if files were removed from the 'temp' folder.
    """

    # Create an empty list to store the paths to the removed files.
    removed = []

    # Monkeypatch simulates a VCF and CSV file in the temp folder using os.listdir in app.py. lambda converts the values
    # in the list into filenames.
    monkeypatch.setattr("app.app.os.listdir", lambda path: ["a.vcf", "b.csv"])
    # Monkeypatch repurposes os.remove in app.py to add the paths of the files that were removed, to the 'removed' list
    # variable.
    monkeypatch.setattr("app.app.os.remove", lambda path: removed.append(path))

    # The homepage in app.py is specified in the route by a '/'. This is submitted by the test client to 'get' a
    # response from app.py during which os.remove is used.
    response = client.get("/")

    # A status code of 200 indicates that the simulated response was received successfully.
    assert response.status_code == 200
    # The length of the 'removed' list is checked to ensure that both files were removed.
    assert len(removed) == 2

# ----------------------------------------------------------------
# Test Homepage-POST: No files uploaded to temp folder.
# ----------------------------------------------------------------
def test_add_variant_no_files(client):
    """
    This function tests if the route to the homepage in app.py reports that the 'temp' folder is empty.
    The 'form_type' and 'db_file' are required to test the "Create or Add to a Database" part of the app.

    :param: client: A fake test client generated by the 'client' pytest fixture.

    :test outcomes: Test that a response was received successfully (status code 200).
                    Test that "A variant file was not uploaded" is returned.
    """
    # Simulate a POST request from the "Create or Add to a Database" section on the homepage by selecting the
    # 'add_variant' form type and assigning a fake database name to 'db_file'.
    response = client.post("/", data={
        #
        "form_type": "add_variant",
        "db_file": "test.db"
    })

    # A status code of 200 indicates that the simulated response was received successfully.
    assert response.status_code == 200
    # Test that app.py returned 'A variant file was not uploaded' when a database was being added to/created while no
    # files has been uploaded.
    assert b"A variant file was not uploaded" in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: Invalid variant file extension.
# ----------------------------------------------------------------
def test_add_variant_invalid_extension(client):
    """
    This function tests if app.py reports that an invalid file type was uploaded, i.e. the file was not a VCF or CSV
    file.
    The 'form_type', 'db_file' and 'variant_files' are required to test this aspect of the "Create or Add to a Database"
    portion of the app.

    :param: client: A fake test client generated by the 'client' pytest fixture.

    :test outcome: Test that "Invalid file type" is returned by the app.
    """

    # Create a dict variable which stores the parameters required to test what happens if an invalid file is uploaded.
    data = {
        # This tests the 'Create or Add to a Database' functionality in app.py.
        "form_type": "add_variant",
        # A fake database name is provided.
        "db_file": "test.db",
        # Simulates the upload of a .txt file, which is not a VCF or CSV file, and should cause the expected message to
        # be returned.
        "variant_files": (BytesIO(b"fake"), "bad.txt")
    }

    # Use request POST to submit the fake file with the wrong extension to app.py.
    response = client.post("/", data=data, content_type="multipart/form-data")

    # Test that "Invalid file type" is returned, as expected.
    assert b"Invalid file type. Please upload .VCF or .CSV files only." in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: Successful upload of variants to a database.
# ----------------------------------------------------------------
def test_add_variant_success(client, monkeypatch):
    """
    This function tests if app.py can successfully upload a variant file and populate a database with the variants from
    the file. This is signified by the return of the message, "Added sample.vcf to database".
    Monkeypatch creates fake parameters to test the patient_variant_table() and variant_annotations_table() database
    functions, as well as os.remove.
    The 'form_type', 'db_file' and 'variant_files' are required to test this aspect of the "Create or Add to a Database"
    portion of the app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response was successfully received (status code 200).
                   Test that "Added sample.vcf to database" is returned by the app.
    """

    # Monkeypatch creates a fake environment to initialise patient_variant_table() and variant_annotations_table().
    monkeypatch.setattr("app.app.patient_variant_table", lambda *args: None)
    monkeypatch.setattr("app.app.variant_annotations_table", lambda *args: None)
    # Monkeypatch also simulates os.remove without deleting any real files.
    monkeypatch.setattr("app.app.os.remove", lambda *args: None)

    # Create a dict variable which stores the parameters required to test what happens if a .VCF file is uploaded.
    data = {
        # This tests the 'Create or Add to a Database' functionality in app.py.
        "form_type": "add_variant",
        # A fake database name is provided.
        "db_file": "test.db",
        # Simulates the upload of a .VCF file, which should be processed without error by the app.
        "variant_files": (BytesIO(b"fake"), "sample.vcf")
    }

    # Use request POST to submit the fake variant file to app.py.
    # follow_redirects=True simulates the full User workflow after form submission.
    response = client.post("/", data=data, content_type="multipart/form-data", follow_redirects=True)

    # A status code of 200 indicates that the simulated response was received successfully.
    assert response.status_code == 200
    # Test that "Added sample.vcf to database" is returned, indicating that the variant file was successfully uploaded
    # to the database.
    assert b"Added sample.vcf to database" in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: Failure to populate a database.
# ----------------------------------------------------------------
def test_add_variant_db_failure(client, monkeypatch):
    """
    This function tests if app.py can handle a failure to populate a database appropriately, without crashing. This is
    signified by the return of the message, ".db was not created/updated" and a status code of 200.
    Monkeypatch creates fake parameters to test the patient_variant_table() and variant_annotations_table() database
    functions.
    The 'form_type', 'db_file' and 'variant_files' are required to test this aspect of the "Create or Add to a Database"
    portion of the app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response was successfully received (status code 200).
                   Test that ".db was not created/updated" is returned by the app.
    """

    # Monkeypatch creates a fake environment to initialise patient_variant_table() and variant_annotations_table().
    monkeypatch.setattr("app.app.patient_variant_table", lambda *args: "error")
    monkeypatch.setattr("app.app.variant_annotations_table", lambda *args: "error")

    # Create a dict variable which stores the parameters required to test what happens if a .VCF file is uploaded.
    data = {
        # This form-type tests the 'Create or Add to a Database' functionality in app.py.
        "form_type": "add_variant",
        # A fake database name is provided.
        "db_file": "test.db",
        # Simulates the upload of a .VCF file, which should be processed without error by the app.
        "variant_files": (BytesIO(b"fake"), "sample.vcf")
    }

    # Use request POST to retrieve submit the fake variant file to app.py, where the database functions do not work.
    # follow_redirects=True simulates the full User workflow after form submission.
    response = client.post(
        "/",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True
    )

    # A status code of 200 indicates that the simulated response was received successfully.
    assert response.status_code == 200
    # Test that ".db was not created/updated" is returned, indicating that the database functions failed but were
    # handled appropriately.
    assert b".db was not created/updated" in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: PermissionError on variant file upload.
# ----------------------------------------------------------------
def test_add_variant_permission_error(monkeypatch, client):
    """
    This function tests if app.py can successfully handle PermissionError exceptions at the point of uploading a variant
    file to a database. Successful error handling is signified by the return of the message, "Failed to save sample.vcf.
    Permission denied." 'sample.vcf' is the name of a fake variant file utilised in this test.
    Monkeypatch creates fake parameters to raise the PermissionError exception.
    The 'form_type', 'db_file' and 'variant_files' are required to test this aspect of the "Create or Add to a Database"
    portion of the app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Failed to save sample.vcf. Permission denied." is returned by the app.
    """
    # Monkeypatch simulates a PermissionError exception raised from saving a variant file.
    monkeypatch.setattr(
        "werkzeug.datastructures.FileStorage.save",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError("no permission"))
    )

    # Create a dict variable which stores the parameters required to test what happens if a .VCF file is uploaded.
    data = {
        # This tests the 'Create or Add to a Database' functionality in app.py.
        "form_type": "add_variant",
        # A fake database name is provided.
        "db_file": "test.db",
        # Simulates the upload of a .VCF file.
        "variant_files": (BytesIO(b"fake"), "sample.vcf")
    }

    # Use request POST to submit the fake variant file to app.py and raise the PermissionError exception.
    response = client.post("/", data=data, content_type="multipart/form-data")

    # Test that "Failed to save sample.vcf. Permission denied." is returned, indicating that the PermissionError
    # exception was handled successfully.
    assert b"Failed to save sample.vcf. Permission denied." in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: ENOSPC exception on variant file upload.
# ----------------------------------------------------------------
def test_add_variant_disk_full(monkeypatch, client):
    """
    This function tests if app.py can successfully handle OSError- ENOSPC exceptions that are raised when there is no
    more diskspace, at the point of uploading a variant file to a database. Successful error handling is signified by
    the return of the message, "Failed to save sample.vcf. There is a problem with your disk space." 'sample.vcf' is the
    name of a fake variant file utilised in this test.
    Monkeypatch creates fake parameters to raise the ENOSPC exception.
    The 'form_type', 'db_file' and 'variant_files' are required to test this aspect of the "Create or Add to a Database"
    portion of the app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Failed to save sample.vcf. There is a problem with your disk space." is returned by the
                   app.
    """
    # Monkeypatch simulates an ENOSPC exception raised from saving a fake variant file.
    monkeypatch.setattr(
        "werkzeug.datastructures.FileStorage.save",
        raise_enospc
    )

    data = {
        # This tests the 'Create or Add to a Database' functionality in app.py.
        "form_type": "add_variant",
        # A fake database name is provided.
        "db_file": "test.db",
        # Simulates the upload of a .VCF file.
        "variant_files": (BytesIO(b"fake"), "sample.vcf")
    }

    # Use request POST to submit the fake variant file to app.py and raise the ENOSPC exception.
    response = client.post("/", data=data, content_type="multipart/form-data")

    # Test that "Failed to save sample.vcf. There is a problem with your disk space." is returned, indicating that the
    # ENOSPC exception was handled successfully.
    assert b"Failed to save sample.vcf. There is a problem with your disk space." in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: OSError exception on variant file upload.
# ----------------------------------------------------------------
def test_add_variant_os_error(monkeypatch, client):
    """
    This function tests if app.py can successfully handle OSError exceptions that are raised when there is a problem
    with the operating system, at the point of uploading a variant file to a database. Successful error handling is
    signified by the return of the message, "Failed to save sample.vcf. There is an issue with the operating system:"
    'sample.vcf' is the name of a fake variant file utilised in this test.
    Monkeypatch creates fake parameters to raise the OSError exception.
    The 'form_type', 'db_file' and 'variant_files' are required to test this aspect of the "Create or Add to a Database"
    portion of the app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Failed to save sample.vcf. There is an issue with the operating system:" is returned by
                   the app.
    """
    # Monkeypatch simulates an OSError exception raised from saving a fake variant file.
    monkeypatch.setattr(
        "werkzeug.datastructures.FileStorage.save",
        raise_oserror
    )

    data = {
        # This tests the 'Create or Add to a Database' functionality in app.py.
        "form_type": "add_variant",
        # A fake database name is provided.
        "db_file": "test.db",
        # Simulates the upload of a .VCF file.
        "variant_files": (BytesIO(b"fake"), "sample.vcf")
    }

    # Use request POST to submit the fake variant file to app.py where the OSError exception is raised.
    response = client.post("/", data=data, content_type="multipart/form-data")

    # Test that "Failed to save sample.vcf. There is an issue with the operating system:" is returned, indicating that
    # OSError exceptions are handled successfully.
    assert b"Failed to save sample.vcf. There is an issue with the operating system:" in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: Invalid database file extension.
# ----------------------------------------------------------------
def test_upload_db_invalid_extension(client):
    """
    This function tests if app.py reports that an invalid database file type was uploaded, i.e. the file does not have a
    .db extension.
    The 'form_type' and 'db_file' are required to test this aspect of the "Upload a Database to Query" portion of the
    app.

    :param: client: A fake test client generated by the 'client' pytest fixture.

    :test outcome: Test that "Invalid file type" is returned by the app.
    """
    # Create a dict variable which stores the parameters required to test what happens if the wrong type of database
    # file is uploaded.
    data = {
        # This form-type tests the 'Upload a Database to Query' functionality in app.py.
        "form_type": "upload_db",
        # A fake database, with a .txt extension, is provided. This should not work as it does not end in .db.
        "database_file": (BytesIO(b"fake"), "notadb.txt")
    }

    # Use request POST to submit a database file with the wrong extension to the app and retrieve the simulated
    # response.
    # follow_redirects=True simulates the full User workflow after form submission.
    response = client.post(
        "/",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True
    )

    # Test that "Invalid file type" is returned, indicating that the database file was not uploaded and the failure was
    # handled appropriately.
    assert b"Invalid file type. Please upload a .db file." in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: Database validation check failure.
# ----------------------------------------------------------------
def test_upload_db_validation_failure(monkeypatch, client):
    """
    This function tests if app.py can handle a failure to validate a database according to a predesigned schema, without
    crashing. Failure to validate a database returns the message, "cannot be queried. Inappropriate tables or headers."
    and a status code of 200.
    Monkeypatch creates fake parameters to test the database using the validate_database() database function.
    The 'form_type' and 'db_file' are required to test this aspect of the "Upload a Database to Query" portion of the
    app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response was successfully received (status code 200).
                   Test that "cannot be queried. Inappropriate tables or headers." is returned by the app.
    """

    # Monkeypatch creates a fake environment to initialise the validate_database() database function to validate the
    # database's schema.
    monkeypatch.setattr("app.app.validate_database", lambda path: False)
    # Monkeypatch also simulates os.remove without deleting any real files.
    monkeypatch.setattr("app.app.os.remove", lambda path: None)
    # Monkey patch prevents the fake database about to be made from saving to the 'databases' directory.
    monkeypatch.setattr(
        "werkzeug.datastructures.FileStorage.save",
        lambda self, dst: None
    )

    # Create a dict variable which stores the parameters required to test what happens if the wrong type of database
    # file is uploaded.
    data = {
        # This form-type tests the 'Upload a Database to Query' functionality in app.py.
        "form_type": "upload_db",
        # A fake database is provided. This should not work as it does not conform with the schema used by the
        # validate_database() function.
        "database_file": (BytesIO(b"fake"), "test.db")
    }

    # Use request POST to submit an invalid database to the app and retrieve the simulated response.
    # follow_redirects=True simulates the full User workflow after form submission.
    response = client.post(
        "/",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True
    )

    # A status code of 200 indicates that the simulated response was received successfully.
    assert response.status_code == 200
    # Test that "cannot be queried. Inappropriate tables or headers." is returned, indicating that the database did not
    # pass the validation but its failure was handled appropriately.
    assert b"cannot be queried. Inappropriate tables or headers." in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: Successful upload of a database to query.
# ----------------------------------------------------------------
def test_upload_db_success(monkeypatch, client):
    """
    This function tests if app.py can successfully validate a database file and redirect the User to the query page,
    essentially testing the full scope of the app's "Upload a Database to Query" section. A successful test is signified
    by the route to the query page appearing in the response's 'Location' header.
    Monkeypatch creates fake parameters to test the database using the validate_database() database function. If the
    validation is successful, the User would be redirected to the query page.
    The 'form_type' and 'db_file' are required to test this aspect of the Upload a Database to Query" portion of the
    app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that the query page was successfully redirected to without accessing it (status code 302).
                   Test that "/query" appears in the response's 'Location' header.
    """
    # Monkeypatch creates a fake environment to initialise the validate_database() database function to validate the
    # database's schema.
    monkeypatch.setattr("app.app.validate_database", lambda path: True)
    # Monkey patch prevents the fake database about to be made from saving to the 'databases' directory.
    monkeypatch.setattr(
        "werkzeug.datastructures.FileStorage.save",
        lambda self, dst: None
    )

    # Create a dict variable which stores the parameters required to test what happens if the database is successfully
    # uploaded.
    data = {
        # This form-type tests the 'Upload a Database to Query' functionality in app.py.
        "form_type": "upload_db",
        # A fake database is provided.
        "database_file": (BytesIO(b"fake"), "test.db")
    }

    # Use request POST to submit a database file to the app and retrieve the simulated response.
    # follow_redirects=False simulates the successful generation of the query page without actually accessing the page.
    # This ensures that the query page route appears in the response's 'Location' header. If it were true, the response
    # would consist of the query page's content.
    response = client.post(
        "/",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False
    )

    # A status code of 302 indicates that the query page was found but the response does not contain any of the page's
    # content. This is intended because the test does not want to access the page, only know that it was successfully
    # generated as result of a successful validation.
    assert response.status_code == 302
    # Test that the response derives from the query page, where the User should have been diverted to if the validation
    # was successful.
    assert "/query" in response.headers["Location"]

# ----------------------------------------------------------------
# Test Homepage-POST: PermissionError on database file upload.
# ----------------------------------------------------------------
def test_add_variant_permission_error(monkeypatch, client):
    """
    This function tests if app.py can successfully handle PermissionError exceptions at the point of uploading a
    database file to a database. Successful error handling is signified by the return of the message, "Failed to save
    test.db database. Permission denied." 'test.db' is the name of a fake database file utilised in this test.
    Monkeypatch creates fake parameters to raise the PermissionError exception.
    The 'form_type' and 'db_file' are required to test this aspect of the "Upload a Database to Query" portion of the
    app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Failed to save test.db. Permission denied." is returned by the app.
    """
    # Monkeypatch simulates a PermissionError exception raised from saving a variant file to the folder pretending to be
    # the 'temp' folder.
    monkeypatch.setattr(
        "werkzeug.datastructures.FileStorage.save",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError())
    )

    # Create a dict variable which stores the parameters required to test what happens if a .VCF file is uploaded.
    data = {
        # This tests the 'Upload a Database to Query' functionality in app.py.
        "form_type": "upload_db",
        # A fake database name is provided.
        "database_file": (BytesIO(b"db"), "test.db")
    }

    # Use request POST to submit a database file to the app and raise the PermissionError exception.
    response = client.post("/", data=data, content_type="multipart/form-data")

    # Test that "Failed to save test.db. Permission denied." is returned, indicating that the PermissionError
    # exception was handled successfully.
    assert b"Failed to save test.db database. Permission denied." in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: ENOSPC exception on database file upload.
# ----------------------------------------------------------------
def test_add_variant_disk_full(monkeypatch, client):
    """
    This function tests if app.py can successfully handle OSError- ENOSPC exceptions that are raised when there is no
    more diskspace, at the point of uploading a database file. Successful error handling is signified by the return of
    the message, "Failed to save test.db. There is a problem with your disk space." 'test.db' is the name of a fake
    database file utilised in this test.
    Monkeypatch creates fake parameters to raise the ENOSPC exception.
    The 'form_type' and 'db_file' are required to test this aspect of the "Upload a Database to Query" portion of the
    app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Failed to save test.db. There is a problem with your disk space." is returned by the
                   app.
    """
    # Monkeypatch simulates an ENOSPC exception raised from saving a fake variant file to the folder pretending to be
    # the 'temp' folder.
    monkeypatch.setattr(
        "werkzeug.datastructures.FileStorage.save",
        raise_enospc
    )

    data = {
        # This tests the 'Upload a Database to Query' functionality in app.py.
        "form_type": "upload_db",
        # A fake database name is provided.
        "database_file": (BytesIO(b"db"), "test.db")
    }

    # Use request POST to submit a database file to the app and raise the ENOSPC exception.
    response = client.post("/", data=data, content_type="multipart/form-data")

    # Test that "Failed to save test.db. There is a problem with your disk space." is returned, indicating that the
    # ENOSPC exception was handled successfully.
    assert b"Failed to save test.db. There is a problem with your disk space." in response.data

# ----------------------------------------------------------------
# Test Homepage-POST: OSError exception on database file upload.
# ----------------------------------------------------------------
def test_add_variant_os_error(monkeypatch, client):
    """
    This function tests if app.py can successfully handle OSError exceptions that are raised when there is a problem
    with the operating system, at the point of uploading a database file. Successful error handling is signified by the
    return of the message, "Failed to save test.db. There is an issue with the operating system:" 'test.db' is the name
    of a fake database file utilised in this test.
    Monkeypatch creates fake parameters to raise the OSError exception.
    The 'form_type' and 'db_file' are required to test this aspect of the "Upload a Database to Query" portion of the
    app.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Failed to save test.db. There is an issue with the operating system:" is returned by
                   the app.
    """
    # Monkeypatch simulates an OSError exception raised from saving a fake variant file to the folder pretending to be
    # the 'temp' folder.
    monkeypatch.setattr(
        "werkzeug.datastructures.FileStorage.save",
        raise_oserror
    )

    data = {
        # This tests the 'Upload a Database to Query' functionality in app.py.
        "form_type": "upload_db",
        # A fake database name is provided.
        "database_file": (BytesIO(b"db"), "test.db")
    }

    # Use request POST to submit a database file to the app and raise the OSError exception.
    response = client.post("/", data=data, content_type="multipart/form-data")

    # Test that "Failed to save test.db. There is an issue with the operating system:" is returned, indicating that
    # OSError exceptions are handled successfully.
    assert b"Failed to save test.db. There is an issue with the operating system:" in response.data

# --------------------------------------------------------------------
# Classes to simulate SQLite databases and functionality on Query page
# --------------------------------------------------------------------
class FakeCursor:
    """
    FakeCursor class simulates a fake cursor that can execute SQLite3 commands in Python.
    """
    def execute(self, *_):
        """
        Simulate the execution of a successful SQLite3 command.
        """
        pass
    def fetchall(self):
        """
        Return a result from the execution.
        """
        return [("P1",)]

class FakeConn:
    """
    Simulate the sqlite3.connect() function.
    """
    def cursor(self):
        """
        Simulates a fake cursor to connect, query and retrieve data from the SQLite3 database from FakeCursor.
        """
        return FakeCursor()

    def __enter__(self):
        """
        Simulates a 'with' block instance to initialise FakeConn.
        """
        return self

    def __exit__(self, *a):
        """
        Simulates the commitment and closing of the connection to the SQLite3 database, thereby ending the 'with'
        block.
        """
        pass

# --------------------------------------------------------------------
# Test Query page-GET: Successful upload of a database to query.
# --------------------------------------------------------------------
def test_query_get_success(monkeypatch, client):
    """
    This function tests if app.py can successfully connect to a database file via SQLite3. A successful connection is
    signified by a response status code of 200 and a rendered db_query_page.html page in the response. If an SQLite3
    database could not be connected to, the User would otherwise be directed to the homepage where the homepage.html
    would be rendered.
    Monkeypatch creates a fake environment in which a fake database can be queried. This prevents pytests from using,
    disturbing or relying on real clinical data and databases.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response was successfully received (status code 200).
                   Test that the db_query_page.html page is rendered by the flask app.
    """
    # Monkeypatch simulates the existence of an SQLite3 database file.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: FakeConn())

    # Use request GET to connect to a database file through the app and return the appropriate query page.
    response = client.get("/query/test.db")

    # A status code of 200 indicates that the simulated query page was received successfully.
    assert response.status_code == 200
    # Test that the db_query_page.html was rendered in the response. If an SQLite database could not be connected to
    # User would be redirected to the homepage.
    assert b"db_query_page.html" in response.data

# --------------------------------------------------------------------
# Test Query page-GET: Database file missing.
# --------------------------------------------------------------------
def test_query_get_db_missing(monkeypatch, client):
    """
    This function tests if app.py can successfully function while the selected database file is missing. When the
    database file cannot be found, the response should return status code 302 because the User would otherwise
    be redirected to the homepage. Therefore, the homepage.html page should be rendered in the response and the route to
    the homepage ('/') should be assigned to the response's 'Location' attribute. Furthermore, the message, "You should
    be redirected automatically to the target URL" should also be returned in the response.
    Monkeypatch creates a fake environment in which a fake database cannot be found. This prevents using, disturbing or
    relying on real clinical data and databases.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that the homepage was successfully redirected to, without accessing it (status code 302).
                   Test that the route to the homepage.html page is assigned to the response's 'Location' attribute.
                   Test that "You should be redirected automatically to the target URL" is returned.
    """
    # Monkeypatch simulates a fake database file called 'test.db' using the os.listdir function from app.py.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch then ensures that the os.path.exists function cannot find the file, thereby simulating that the
    # database file is missing.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: False)

    # Use request GET to submit a request to a page for a database file that is missing.
    # follow_redirects=False simulates the successful generation of the homepage without actually accessing the page.
    # This ensures that the query page route appears in the response's 'Location' header. If it were true, the response
    # would consist of content from the homepage.
    response = client.get("/query/test.db", follow_redirects=False)

    # A status code of 302 indicates that the homepage was found but the response does not contain any of the page's
    # content. This is intended because the test does not want to access the page, only know that it was successfully
    # generated as result of a successful error handler.
    assert response.status_code == 302
    # Test that the response derives from the homepage, which the User should have been diverted to if the
    # FileNotFoundError exception was handled correctly.
    assert "/" in response.headers["Location"]
    # Test that "You should be redirected automatically to the target URL" is returned, indicating that
    # FileNotFoundError exception is handled successfully.
    assert b"You should be redirected automatically to the target URL" in response.data

# --------------------------------------------------------------------
# Test Query page-GET: Database file not found.
# --------------------------------------------------------------------
def test_query_get_no_db_folder(monkeypatch, client):
    """
    This function tests if app.py can successfully handle the FileNotFoundError exception. If the FileNotFoundError
    exception was handled successfully, the response should return status code of 302 because the hUser would otherwise
    be redirected to the homepage. Therefore, the homepage.html page should be rendered in the response and the route to
    the homepage ('/') should be assigned to the response's 'Location' attribute. Furthermore, the message, "You should
    be redirected automatically to the target URL" should also be returned in the response.
    Monkeypatch creates a fake environment in which the FileNotFoundError exception is raised without using, disturbing
    or relying on real clinical data and databases.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that the homepage was successfully redirected to, without accessing it (status code 302).
                   Test that the route to the homepage.html page is assigned to the response's 'Location' attribute.
                   Test that "You should be redirected automatically to the target URL" is returned.
    """
    # Monkeypatch simulates a FileNotFoundError exception that is raised because the folder where the database file
    # should be stored does not exist.
    monkeypatch.setattr(
        "app.app.os.listdir",
        lambda *_: (_ for _ in ()).throw(FileNotFoundError())
    )

    # Use request GET to retrieve the simulated response from the app where a FileNotFoundError exception has been
    # raised.
    # follow_redirects=False simulates the successful generation of the homepage without actually accessing the page.
    # This ensures that the query page route appears in the response's 'Location' header. If it were true, the response
    # would consist of the homepage's content.
    response = client.get("/query/test.db", follow_redirects=False)

    # A status code of 302 indicates that the homepage was found but the response does not contain any of the page's
    # content. This is intended because the test does not want to access the page, only know that it was successfully
    # generated as result of a successful error handler.
    assert response.status_code == 302
    # Test that the response derives from the homepage, which the User should have been diverted to if the
    # FileNotFoundError exception was handled correctly.
    assert "/" in response.headers["Location"]
    # Test that "You should be redirected automatically to the target URL" is returned, indicating that
    # FileNotFoundError exception is handled successfully.
    assert b"You should be redirected automatically to the target URL" in response.data

# --------------------------------------------------------------------
# Test Query page-POST: Successful patient query.
# --------------------------------------------------------------------
def test_patient_query_success(monkeypatch, client):
    """
    This function tests if app.py can appropriately handle a successful patient query.

    WARNING: This function does NOT test the functionality of the patient query. All queries including patient queries
    are processed by the query_db() database function. Please refer to test_database_functions.py to test if the query
    works.

    To determine if the patient query can be handled by app.py successfully. A 200 status code should be returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response was received successfully (status code 200)
    """
    # Monkeypatch simulates the existence of an SQLite3 database file.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: FakeConn())
    # Monkeypatch simulates some fake SQLite database content to be processed by a fake version of query_db() in app.py.
    monkeypatch.setattr("app.app.query_db", lambda *a, **k: [{"patient_ID": "P1", "variant_NC": "NC_1"}])
    # Use request POST to render the output from the patient query (assigned to the 'data' variable) into the query
    # page.
    response = client.post("/query/test.db", data={"patient_ID": "P1"})
    # A status code of 200 indicates that the simulated response was received successfully and that patient queries are
    # handled appropriately by app.py.
    assert response.status_code == 200

# --------------------------------------------------------------------
# Test Query page-POST: Unsuccessful patient query.
# --------------------------------------------------------------------
def test_patient_query_not_found(monkeypatch, client):
    """
    This function tests if app.py can appropriately handle an unsuccessful patient query.

    WARNING: This function does NOT test the functionality of the patient query. All queries including patient queries
    are processed by the query_db() database function. Please refer to test_database_functions.py to test if the query
    works.

    To determine if the unsuccessful patient query can be handled by app.py successfully, "Patient Query: {patient_ID}
    could not be found in {db_name} database." should be returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Patient Query: X could not be found in test.db database." is returned.
    """
    # Monkeypatch simulates empty database content to be processed by a fake version of query_db() in app.py.
    monkeypatch.setattr("app.app.query_db", lambda *a, **k: None)
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: FakeConn())
    # Monkeypatch simulates the existence of an SQLite3 database file.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Use request POST to render the output from the unsuccessful patient query into the query page.
    response = client.post("/query/test.db", data={"patient_ID": "X"}, follow_redirects=True)
    # Test that predetermined message from an unsuccessful patient query is returned in the response.
    assert b"Patient Query: X could not be found in test.db database." in response.data

# --------------------------------------------------------------------
# Test Query page-POST: Successful variant query.
# --------------------------------------------------------------------
def test_variant_query_success(monkeypatch, client):
    """
    This function tests if app.py can appropriately handle a successful variant query.

    WARNING: This function does NOT test the functionality of the variant query. All queries including variant queries
    are processed by the query_db() database function. Please refer to test_database_functions.py to test if the query
    works.

    To determine if the variant query can be handled by app.py successfully. A 200 status code should be returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response was received successfully (status code 200)
    """
    # Monkeypatch simulates a fake variant to be processed by a fake version of get_mane_nc() in app.py.
    monkeypatch.setattr("app.app.get_mane_nc", lambda v: "NC_1")
    # Monkeypatch simulates some fake SQLite database content to be processed by a fake version of query_db() in app.py.
    monkeypatch.setattr("app.app.query_db", lambda *a, **k: [{"variant_NC": "NC_1"}])
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: FakeConn())
    # Monkeypatch simulates the existence of an SQLite3 database file.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Use request POST to render the output from the successful variant query into the query page.
    response = client.post("/query/test.db", data={"variant_NC": "NM_1:c.1A>T"})
    # A status code of 200 indicates that the simulated response was received successfully and that variant queries are
    # handled appropriately by app.py.
    assert response.status_code == 200

# --------------------------------------------------------------------
# Test Query page-POST: Unsuccessful gene query (gene not found).
# --------------------------------------------------------------------
def test_gene_query_not_found(monkeypatch, client):
    """
    This function tests if app.py can appropriately handle an unsuccessful gene query.

    WARNING: This function does NOT test the functionality of the gene query. All queries including gene queries
    are processed by the query_db() database function. Please refer to test_database_functions.py to test if the query
    works.

    To determine if the unsuccessful gene query can be handled by app.py successfully, "Gene Query: {gene}
    could not be found in {db_name} database." should be returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Gene Query: FAKE could not be found in test.db database." is returned.
    """
    # Monkeypatch simulates empty database content to be processed by a fake version of query_db() in app.py.
    monkeypatch.setattr("app.app.query_db", lambda *a, **k: None)
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: FakeConn())
    # Monkeypatch simulates the existence of an SQLite3 database file.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Use request POST to render the output from the unsuccessful gene query into the query page.
    response = client.post("/query/test.db", data={"gene": "FAKE"}, follow_redirects=True)
    # Test that the predetermined message from an unsuccessful gene query is returned in the response.
    assert b"Gene Query: FAKE could not be found in test.db database." in response.data

# --------------------------------------------------------------------
# Test Query page-ERROR: SQLite error during query.
# --------------------------------------------------------------------
def test_query_sqlite_error(monkeypatch, client):
    """
    This function tests if app.py can appropriately handle an sqlite3.DatabaseError exception as a result of executing
    the query_db() database function.

    To determine if the exception was handled appropriately, an assertion is made that the error message from the
    sqlite_error error handler, from error_handlers.py, is returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Something went wrong while accessing the database. Please report this to your friendly
                   neighbourhood Clinical Bioinformatician." is returned.
    """
    # Monkeypatch simulates an sqlite3.DatabaseError exception raised from querying a database.
    monkeypatch.setattr(
        "app.app.query_db",
        lambda *a, **k: (_ for _ in ()).throw(raise_sqlite_de())
    )
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: FakeConn())
    # Monkeypatch simulates the existence of an SQLite3 database file.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Use request POST to submit a query to the app so that the sqlite3.DatabaseError exception can be raised.
    response = client.post("/query/test.db", data={"patient_ID": "P1"}, follow_redirects=True)
    # Test that the predetermined message from an sqlite3.DatabaseError is returned in the response.
    assert (b"Something went wrong while accessing the database. Please report this to your friendly neighbourhood "
            b"Clinical Bioinformatician.") in response.data

# --------------------------------------------------------------------
# Test Query page-ERROR: IndexError from querying.
# --------------------------------------------------------------------
def test_export_index_error(monkeypatch, client):
    """
    This function tests if app.py can appropriately handle an IndexError exception from the output returned by the
    query_db() database function.

    To determine if the exception was handled appropriately, an assertion is made that the following message is
    returned, "Query Error: An error occurred while processing the query. It is not your fault. Please contact your
    nearest friendly neighbourhood Bioinformatician".

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Query Error: An error occurred while processing the query. It is not your fault. Please
                   contact your friendly neighbourhood Clinical Bioinformatician." is returned.
    """
    # Monkeypatch simulates a blank list that is processed by the query_db() database function from app.py.
    monkeypatch.setattr("app.app.query_db", lambda *a, **k: [None])
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: FakeConn())
    # Monkeypatch simulates the existence of an SQLite3 database file.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Use request POST to submit a query to the app so that the IndexError exception can be raised.
    response = client.post("/query/test.db", data={"patient_ID": "P1"})
    # Test that the predetermined message from an IndexError is returned in the response.
    assert (b"Query Error: An error occurred while processing the query. It is not your fault. Please contact your "
            b"nearest friendly neighbourhood Bioinformatician") in response.data

# --------------------------------------------------------------------
# Test Query page-ERROR: KeyError from querying.
# --------------------------------------------------------------------
def test_export_key_error(monkeypatch, client):
    """
    This function tests if app.py can appropriately handle a KeyError exception from the output returned by the
    query_db() database function.

    To determine if the exception was handled appropriately, an assertion is made that the following message is
    returned, "Query Error: An error occurred while processing the query. It is not your fault. Please contact your
    nearest friendly neighbourhood Bioinformatician".

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Query Error: An error occurred while processing the query. It is not your fault. Please
                   contact your friendly neighbourhood Clinical Bioinformatician." is returned.
    """
    # Monkeypatch simulates a fake variant to be processed by a fake version of get_mane_nc() in app.py.
    monkeypatch.setattr("app.app.get_mane_nc", lambda v: "NC_1")
    # Monkeypatch simulates fake SQLite database content to be processed by a fake version of query_db() in app.py.
    monkeypatch.setattr(
        "app.app.query_db",
        lambda *a, **k: [
            {"variant_NC": "NC_1", "gene": "CSF1R"},
            {"variant_NC": "NC_1"}
        ]
    )
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: FakeConn())
    # Monkeypatch simulates the existence of an SQLite3 database file.
    monkeypatch.setattr("app.app.os.listdir", lambda *_: ["test.db"])
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Use request POST to submit a query to the app so that the KeyError exception can be raised.
    response = client.post("/query/test.db", data={"variant_NC": "NM_1.1:c.1A>T"}, follow_redirects=True)
    # Test that the predetermined message from an KeyError is returned in the response.
    assert (b"Query Error: An error occurred while processing the query. It is not your fault. Please contact your "
            b"nearest friendly neighbourhood Bioinformatician") in response.data


# --------------------------------------------------------------------
# Fake SQLite database content to test
# --------------------------------------------------------------------
FAKE_ROWS = [
    {
        "patient_ID": "Patient1",
        "variant_NC": "NC_000019.10:g.41968837C>G",
        "variant_NM": "NM_152296.5:c.2767G>C",
        "variant_NP": "NP_689509.1:p.(Asp923His)",
        "gene": "ATP1A3",
        "HGNC_ID": "801",
        "Classification": "Pathogenic",
        "Conditions": "Dystonia 12",
        "Stars": "★",
        "Review_status": "criteria provided, single submitter",
    }
]

# --------------------------------------------------------------------
# Test Display page-GET: Successful display page
# --------------------------------------------------------------------
def test_display_db_success(monkeypatch, client):
    """
    This function tests if app.py can successfully connect to a database file via SQLite3 and display the database on
    the display page. A successful connection is signified by a response status code of 200. If an SQLite3 database
    could not be connected to, the User would otherwise be directed to the homepage where homepage.html would be
    rendered.

    Furthermore, the data held in the FAKE_ROWS array should be loaded into the response.data object. This allows
    assertions to be made on the content of the data.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response was successfully received (status code 200).
                   Test that the patient_ID is in response.data.
                   Test that the gene is in response.data.
    """
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda path: True)
    # Monkeypatch simulates fake SQLite database content to be processed by a fake version of query_db() in app.py by
    # using the data in the FAKE_ROWS array.
    monkeypatch.setattr(
        "app.app.query_db",
        lambda db_path, query, params: FAKE_ROWS
    )
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr(
        "app.app.sqlite3.connect",
        lambda *args, **kwargs: FakeConn()
    )
    # Use request GET to connect to a database file through the app and return the corresponding display page.
    response = client.get("/display/test.db")
    # A status code of 200 indicates that the simulated display page was returned successfully.
    assert response.status_code == 200
    # Test that the patient_ID from FAKE_ROWS was loaded into the page.
    assert b"Patient1" in response.data
    # Test that the gene from FAKE_ROWS was loaded into the page.
    assert b"ATP1A3" in response.data

# --------------------------------------------------------------------
# Test Display page-GET: database file does not exist.
# --------------------------------------------------------------------
def test_display_db_not_found(monkeypatch, client):
    """
    This function tests if app.py can successfully function while the selected database file is missing, on the display
    page. When the database file cannot be found, the response should return status code 302 because the User would
    otherwise be redirected to the homepage. Therefore, the homepage.html page should be rendered in the response and
    the route to the homepage ('/') should be assigned to the response's 'Location' attribute. Furthermore, the message,
    "You should be redirected automatically to the target URL" should also be returned in the response.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that the homepage was successfully redirected to, without accessing it (status code 302).
                   Test that the route to the homepage.html page is assigned to the response's 'Location' attribute.
                   Test that "You should be redirected automatically to the target URL" is returned.
    """
    # Monkeypatch ensures that the os.path.exists function cannot find the database file, thereby simulating that the
    # database file is missing.
    monkeypatch.setattr("app.app.os.path.exists", lambda path: False)

    # Use request GET to submit a request to the display page for a database file that is missing.
    # follow_redirects=False simulates the successful generation of the homepage without actually accessing the page.
    # This ensures that the query page route appears in the response's 'Location' header. If it were true, the response
    # would consist of content from the homepage.
    response = client.get("/query/test.db", follow_redirects=False)

    # A status code of 302 indicates that the homepage was found but the response does not contain any of the page's
    # content. This is intended because the test does not want to access the page, only know that it was successfully
    # generated as result of a successful error handler.
    assert response.status_code == 302

    # Test that the response derives from the homepage, which the User should have been diverted to if the
    # FileNotFoundError exception was handled correctly.
    assert "/" in response.headers["Location"]

    # Test that "You should be redirected automatically to the target URL" is returned, indicating that
    # FileNotFoundError exception is handled successfully.
    assert b"You should be redirected automatically to the target URL" in response.data

# --------------------------------------------------------------------
# Test Display page-POST: Successfully apply filters.
# --------------------------------------------------------------------
def test_display_db_filter(monkeypatch, client):
    """
    This functions tests if app.py can successfully function while the selected database file is filtered, on the
    display page.

    Filters require an operational version of the query_db() database function to be applied. Therefore, a fake version
    of query_db() with minimal functionality is used to only filter-in variants with a 'Pathogenic' classification and
    sort them by patient_ID. As the variant stored in the FAKE_ROWS array is classed as 'Pathogenic', it is returned as
    a result of the fake_query_db() function.

    A successful filtration and assortment is signified by a status code of 200 from the response.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response was successfully received (status code 200) for applying a filter.
                   Test that a response was successfully received (status code 200) for sorting the values.
    """
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda path: True)

    def fake_query_db(db_path, query, params):
        """
        This function creates a fake version of the query_db() database function with minimal functionality so that
        assertions can be made on the content of the data, specifically the classification.

        Assertions are made on the SQL query's integrity to ensure that filters and sort by values are effective. An
        assertion is also on the params' structure.

        :param: db_path: Path to the database file does not exist because this is a fake function.
                  query: A fake SQL query to specify the headers of the column to filter by and the column to sort by.
                 params: A fake value to replace the placeholder in the query string.

        :output: FAKE_ROWS: A fake row that would be returned by the query_db() function.
        """
        # The assertion checks that the SQL query includes a WHERE clause with a placeholder (?) so that the value
        # assigned to params takes its place.
        assert "WHERE Classification = ?" in query
        # The assertion checks the param is structured correctly, i.e. it is in a tuple and in the correct order.
        assert params == ("Pathogenic",)
        # The assertion checks that the SQL query includes an ORDER BY clause which sorts the order of the data by the
        # column header specified in the clause (patient_ID).
        assert "ORDER BY patient_ID" in query
        # The data in the FAKE_ROWS array is returned, as required.
        return FAKE_ROWS

    # Monkeypatch simulates the output from fake_query_db as a result whenever query_db() from app.py is executed.
    monkeypatch.setattr(
        "app.app.query_db",
        fake_query_db
    )
    # Monkeypatch simulates the sqlite3.connect function from app.py to connect to a fake database.
    monkeypatch.setattr(
        "app.app.sqlite3.connect",
        lambda *args, **kwargs: FakeConn()
    )
    # Use request POST to submit the values to filter by, as a test client, so that they are applied to a database file
    # through the app and returned to the corresponding display page.
    response = client.post(
        "/display/test.db",
        data={
            "filter_column": "Classification",
            "filter_value": "Pathogenic"}
    )
    # A status code of 200 indicates that the simulated response was received successfully.
    assert response.status_code == 200

    response = client.post(
        "/display/test.db",
        data={"sort_column": "patient_ID"}
    )
    assert response.status_code == 200

# --------------------------------------------------------------------
# Test Query page-ERROR: SQLite error on the display page.
# --------------------------------------------------------------------
def test_display_database_sqlite_error(client, monkeypatch):
    """
    This function tests if app.py can appropriately handle an sqlite3.OperationalError exception as a result of
    executing the query_db() database function on the display page.

    To determine if the exception was handled appropriately, an assertion is made that the error message from the
    sqlite_error error handler, from error_handlers.py, is returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "test.db Filter Error: Something went wrong while accessing the database." is returned.
    """
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Monkeypatch simulates the sqlite3.OperationalError exception when query_db() from app.py is executed.
    monkeypatch.setattr(
        "app.app.query_db",
        raise_sqlite_oe
    )
    # Use request GET to submit a request to the app so that the sqlite3.OperationalError exception is raised.
    response = client.get("/display/test.db")
    # Test that the predetermined message from an sqlite3.OperationalError is returned in the response.
    assert b'test.db Filter Error: Something went wrong while accessing the database.' in response.data

# ----------------------------------------------------------------------------
# Test Query page-ERROR: Generic exception on the display page from filtering.
# ----------------------------------------------------------------------------
def test_display_database_unexpected_exception(client, monkeypatch):
    """
    This function tests if app.py can appropriately handle an Exception being raised as a result of executing the
    query_db() database function on the display page while filters are being applied. The Exception error handler is
    used if none of the other error handlers managed to capture the exception.

    To determine if the exception was handled appropriately, an assertion is made that the appropriate error message is
    returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Filter Error: Failed to prepare test.db to be filtered" is returned.
    """
    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Monkeypatch simulates empty database content to be processed by a fake version of query_db() in app.py.
    monkeypatch.setattr(
        "app.app.query_db",
        lambda *a, **k: None
    )
    # Monkeypatch simulates a generic Exception raised while connecting to an SQLite3 database through app.py.
    monkeypatch.setattr(
        "app.app.sqlite3.connect",
        lambda _: (_ for _ in ()).throw(raise_generic())
    )
    # Use request GET to submit a request to the app so that the generic Exception is raised.
    response = client.get("/display/test.db")
    # Test that the predetermined message from a generic Exception is returned in the response.
    assert b'Filter Error: Failed to prepare test.db to be filtered' in response.data

# --------------------------------------------------------------------
# Test Database switch-POST: Successful database switch on query page.
# --------------------------------------------------------------------
def test_switch_db_success(client):
    """
    This function tests if the switch_db() function in app.py can appropriately handle a successful request to switch
    which database is queried. A successful switch is indicated by a successful redirection to a query page for the
    newly selected database. The request should return a status code of 302 and the db_query_page.html page should be
    rendered. Therefore, '/query/{database name}' should be assigned to the response's 'Location' attribute.

    To determine if the switch was successful, assertions are made that the appropriate status code and URL are
    returned in the response.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that the query page was successfully redirected to without accessing it (status code 302).
                   Test that "/query/test.db" appears in the response's 'Location' header.
    """
    # Use request POST to submit a request to switch databases to the app and retrieve the simulated response.
    # follow_redirects=False simulates the successful generation of the query page without actually accessing the page.
    # This ensures that the query page route appears in the response's 'Location' header. If it were true, the response
    # would consist of the query page's content and the status code would be 200.
    response = client.post(
        "/switch_db",
        data={"db_name": "test.db"},
        follow_redirects=False,
    )

    # A status code of 302 indicates that the query page was found but the response does not contain any of the page's
    # content. This is intended because the test does not want to access the page, only know that it was successfully
    # generated as result of a successful database switch.
    assert response.status_code == 302
    # Test that the response derives from the query page, where the User would have been diverted if the switch was
    # successful.
    assert "/query/test.db" in response.headers["Location"]

# ----------------------------------------------------------------------
# Test Database switch-POST: Unsuccessful database switch on query page.
# ----------------------------------------------------------------------
def test_switch_db_no_db_selected(client):
    """
    This function tests if the switch_db() function in app.py can appropriately handle an unsuccessful request to switch
    which database is queried, to a database that is no longer available. An unsuccessful switch request returns the
    message "Please select a database to query on the homepage." The User is not redirected to the homepage but instead,
    the flash message inserted into the rendered homepage. Therefore, a status code of 302 would not be returned but
    a status of code 200 would be.

    To determine if the failure to switch was handled successful, an assertion is made that the appropriate error
    message is returned in the response. The status code does not need to be tested for because the error message
    response implies that a 200 status code was returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Please select a database to query on the homepage." is returned.
    """
    # Use request POST to submit a request to switch databases to the app, using a blank data form, and retrieve the
    # simulated response.
    response = client.post(
        "/switch_db",
        data={},  # no db_name
        follow_redirects=True,
    )

    # Test that the predetermined error message to an unsuccessful switch is returned.
    assert b"Please select a database to query on the homepage." in response.data

# ----------------------------------------------------------------------------
# Test Database switch-ERROR: Generic exception when switching databases.
# ----------------------------------------------------------------------------
def test_switch_db_exception(client, monkeypatch):
    """
    This function tests if app.py can appropriately handle an Exception being raised as a result of unsuccessfully
    switching databases. The Exception error handler is used to simulate the exception.

    To determine if the exception was handled appropriately, an assertion is made that the appropriate error message is
    returned.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that "Failed to select a different database to query" is returned.
    """
    # The request.form.get object is an irregular function to simulate. Therefore, the only other function in the
    # corresponding try block: url_for(), is simulated instead to raise the generic Exception.
    monkeypatch.setattr("app.app.url_for", raise_generic)

    # Use request POST to submit a request to switch databases to the app, using a fake database name, and retrieve the
    # simulated response.
    response = client.post(
        "/switch_db",
        data={"db_name": "test.db"}
    )
    # Test that the predetermined error message that is generated from raising an Exception during to an unsuccessful
    # database switch is returned.
    assert b"Failed to select a different database to query" in response.data

# ----------------------------------------------------------------------------
# Test CSV Export-POST: Successful download of CSV file.
# ----------------------------------------------------------------------------
def test_export_csv_success(client):
    """
    This function tests if the export_csv() function in app.py can successfully handle a request to export the table
    rendered on either the query or display pages, in CSV format. The content of the table depends on the query or
    filtration and sort by values selected by the User, respectively.

    As the functionality of export_csv() is dependent on the content of a CSV, lists of values that represent the
    headers and values in the table are assigned to the 'columns' and 'rows' variables, respectively. The monkeypatch
    fixture is not used.

    To determine if the CSV was prepared for download successfully, several assertions are made along the process,
    including:
        - checking that export CSV handles the request without breaking, denoted as a status code of 200.
        - checking that a CSV file was returned, define by the file extension.
        - checking that the CSV has been encoded and converted into bytes correctly.
        - checking that the CSV content is correct.

    :param: client: A fake test client generated by the 'client' pytest fixture.

    :test outcome: Test that the mimetype extension is "text/csv", indicating that a CSV file was generated.
                   Test that "\ufeff" appears at the beginning of the file, indicating that the content of the CSV has
                   been  encoded using utf-8 and converted into bytes.
                   Test that the CSV includes the column headers and values in correct orientation.
    """
    # Prepare fake column headers.
    columns = ["patient_ID", "gene"]
    # Prepare fake rows in the CSV.
    rows = [
        ["Patient1", "ATP1A3"],
        ["Patient2", "SCN1A"],
    ]

    # Use request POST to submit a request to 'dump' the columns and rows into a fake JSON to that they can be loaded
    # and processed by app.py.
    response = client.post(
        "/export_csv",
        data={
            "columns": json.dumps(columns),
            "rows": json.dumps(rows),
            "db_name": "test.db",
        },
    )
    # A successful request and response is denoted by a response status code of 200.
    assert response.status_code == 200
    # The successful generation of a CSV file is denoted by the mimetype extension "text/csv".
    assert response.mimetype == "text/csv"

    # The CSV is converted into encoded by utf-8
    content = response.data.decode("utf-8")

    # "\ufeff" suggests that the CSV has been successfully encoded by utf-8 and converted into bytes.
    assert content.startswith("\ufeff")

    # Test that the CSV contains the column headers.
    assert "patient_ID,gene" in content
    # Test that the CSV contains the first row.
    assert "Patient1,ATP1A3" in content
    # Test that the CSV contains the second row.
    assert "Patient2,SCN1A" in content

# ----------------------------------------------------------------------------
# Test CSV Export-POST: Unsuccessful JSON table conversion.
# ----------------------------------------------------------------------------
def test_export_csv_json_decode_error(client, monkeypatch):
    """
    This function tests if the export_csv() function in app.py can successfully handle a json.JSONDecodeError exception,
    raised while exporting the table rendered on either the query or display pages, in CSV format. This error handler is
    activated when the content from the table is read in JSON format and loaded into a Python dictionary.

    The monkeypatch fixture is used to simulate the json.JSONDecodeError exception. The test client is used to submit a
    fake request to generate the CSV from some 'data' so that monkeypatch is activated.

    To determine if app.py can successfully handle the json.JSONDecodeError exception, a response status code of 200 is
    expected along with the designated error message, "CSV Export Error: Failed to parse values from the table for
    CSV export."

    :param: monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be
                         altered without changing the original attributes and variables being used.
                 client: A fake test client generated by the 'client' pytest fixture.

    :test outcome: Test that a response status code of 200 is returned.
                   Test that the error message, "CSV Export Error: Failed to parse values from the table for CSV
                   export." is returned.
    """
    # Monkeypatch simulates the json.JSONDecodeError exception, raised when the json.loads function is used in app.py.
    monkeypatch.setattr("app.app.json.loads", raise_json_error)
    # The fake test client and request POST are used to submit a fake dataset to the app, to raise the
    # json.JSONDecodeError exception.
    response = client.post(
        "/export_csv",
        data={
            "columns": "bad-json",
            "rows": "bad-json",
            "db_name": "test.db",
        },
    )
    # Test that a successful request and response were generated without breaking the app, denoted by a response status
    # code of 200.
    assert response.status_code == 200
    # Test that the expected error message from a json.JSONDecodeError exception, is returned.
    assert b"CSV Export Error: Failed to parse values from the table for CSV export." in response.data

# ----------------------------------------------------------------------------
# Test CSV Export-POST: Unsuccessful CSV file generation.
# ----------------------------------------------------------------------------
def test_export_csv_csv_writer_error(client, monkeypatch):
    """
    This function tests if the export_csv() function in app.py can successfully handle a csv.Error exception, raised
    while writing the table rendered on either the query or display pages, in CSV format. This error handler is
    activated when the content of the 'columns' and 'rows' Python dictionaries are written into a CSV.

    The monkeypatch fixture is used to simulate the csv.Error exception. The test client is used to submit a
    fake request to generate the CSV from a fake JSON dataset, so that monkeypatch is activated.

    To determine if app.py can successfully handle the csv.Error exception, a response status code of 200 is
    expected along with the designated error message, "CSV Export Error: Failed to write values into CSV. CSV cannot
    be exported."

    :param: monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be
                         altered without changing the original attributes and variables being used.
                 client: A fake test client generated by the 'client' pytest fixture.

    :test outcome: Test that a response status code of 200 is returned.
                   Test that the error message, "CSV Export Error: Failed to write values into CSV. CSV cannot be
                   exported." is returned.
    """
    # Monkeypatch simulates the csv.Error exception, raised when the csv.writer function is used in app.py.
    monkeypatch.setattr("app.app.csv.writer", raise_csv_error)
    # The fake test client and request POST are used to submit a fake dataset to the app, to raise the csv.Error
    # exception.
    response = client.post(
        "/export_csv",
        data={
            "columns": json.dumps(["a", "b"]),
            "rows": json.dumps([["1", "2"]]),
            "db_name": "sea.db",
        },
    )
    # Test that a successful request and response were generated without breaking the app, denoted by a response status
    # code of 200.
    assert response.status_code == 200
    # Test that the expected error message from a csv.Error exception, is returned.
    assert b"CSV Export Error: Failed to write values into CSV. CSV cannot be exported." in response.data

# -----------------------------------------------------------------------------------
# Test CSV Export-POST: CSV mismatched row skipped.
# -----------------------------------------------------------------------------------
def test_export_csv_row_length_mismatch_is_skipped(client):
    """
    This function tests if the export_csv() function in app.py can successfully handle a row in the input that is not
    the same length as the columns variable. In app.py, the row would be skipped. This handler is activated when the
    content of the CSV is being converted into bytes.

    As the functionality of export_csv() is dependent on the content of a CSV, lists of values that represent the
    headers and values in the table are assigned to the 'columns' and 'rows' variables, respectively. The monkeypatch
    fixture is not used.

    To determine if app.py can successfully handle the mismatched row, a response status code of 200 is expected.
    Furthermore, the values assigned to 'columns' is expected to be in the response while the values from the mismatched
    row are not.

    :param: client: A fake test client generated by the 'client' pytest fixture.

    :test outcome: Test that a response status code of 200 is returned.
                   Test that the values in the 'columns' variable are in the response but the values from the mismatched
                   row are not.
    """
    # The fake test client and request POST are used to submit a fake dataset to the app. 'rows' is a shorter length
    # than 'columns'.
    response = client.post(
        "/export_csv",
        data={
            "columns": json.dumps(["a", "b"]),
            "rows": json.dumps([["1"]]),  # mismatch
            "db_name": "test.db",
        },
    )
    # The response from the request is encoded using utf-8.
    content = response.data.decode("utf-8")
    # Test that the values from 'columns' appear in the encoded response.
    assert "a,b" in content
    # Test that the values from the mismatched row do not appear in the encoded response proving that it was skipped.
    assert "1," not in content

def test_export_csv_generic_exception(client, monkeypatch):
    """
    This function tests if the export_csv() function in app.py can appropriately handle an Exception being raised as a
    result of unsuccessfully generating the CSV file for download. The Exception error handler (raise_generic) is used
    to simulate the exception.

    To determine if the exception was handled appropriately, a response status code of 200 is expected along with the
    expected error message, "CSV Export Error: Failed to prepare CSV. CSV cannot be exported."

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response status code of 200 is returned.
                   Test that the error message, "CSV Export Error: Failed to prepare CSV. CSV cannot be exported", is
                   returned.
    """
    # Monkeypatch simulates the generic Exception error which is raised when the send_file function is executed in
    # app.py.
    monkeypatch.setattr("app.app.send_file", raise_generic)
    # The fake test client and request POST are used to submit a fake dataset to the app, to raise the Exception error.
    response = client.post(
        "/export_csv",
        data={
            "columns": json.dumps(["a"]),
            "rows": json.dumps([["1"]]),
            "db_name": "sea.db",
        },
    )
    # Test that a successful request and response were generated without breaking the app, denoted by a response status
    # code of 200.
    assert response.status_code == 200
    # Test that the expected error message from an Exception error, is returned.
    assert b"CSV Export Error: Failed to prepare CSV. CSV cannot be exported" in response.data

# --------------------------------------------------------------------
# Test Query page-GET: Database file missing.
# --------------------------------------------------------------------
def test_dropdown_db_not_found(client, monkeypatch):
    """
    This function tests if the dropdown_data() function in app.py can successfully function while the selected database
    file is missing when trying to generate the dropdown menus on the query page. When the database file cannot be
    found, the response should return status code 200 because the homepage.html template would be rendered. Furthermore,
    the message, "{database name} database not found. Please select a database to query on the homepage." should also be
    returned in the response.

    Monkeypatch creates a fake environment in which a fake database cannot be found. This prevents using, disturbing or
    relying on real clinical data and databases.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response status code of 200 is returned.
                   Test that "test.db database not found. Please select a database to query on the homepage." is
                   returned.
    """
    # Monkeypatch then ensures that the os.path.exists function cannot find the file, thereby simulating that the
    # database file is missing.
    monkeypatch.setattr("app.app.os.path.exists", lambda _: False)
    # Use request GET to submit a request to generate dropdown menus, to the app to find the selected database.
    response = client.get("/api/dropdown/test.db")
    # Test that a successful request and response were generated without breaking the app, denoted by a response status
    # code of 200.
    assert response.status_code == 200
    # Test that the appropriate error message is returned.
    assert b"test.db database not found. Please select a database to query on the homepage." in response.data

# ---------------------------------------------------------------------------
# Test Query page-GET: Successful generation of dropdown menus on query page.
# ---------------------------------------------------------------------------
def test_dropdown_success(client, monkeypatch):
    """
    This function tests if the dropdown_data() function in app.py can successfully generate the dropdown menus on the
    query page, the response should return status code 200. Furthermore, the content of each dropdown menu for each
    query type on the query page are simulated using the DummyCursor class. Assertions are made on what would appear in
    the dropdown menus based on the contents of the response from monkeypatch simulation.

    Monkeypatch creates a fake environment in which a fake database cannot be found. This prevents using, disturbing or
    relying on real clinical data and databases.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response status code of 200 is returned.
                   Test that the 'patients' key is assigned 'Patient1' and 'Patient2' from the DummyCursor class.
                   Test that the 'variants' key is assigned 'NC_000019.10:g.1' from the DummyCursor class.
                   Test that the 'genes' key is assigned 'ATP1A3' from the DummyCursor class.
    """
    class DummyCursor:
        """
        FakeCursor class simulates a fake cursor that can execute SQLite3 commands in Python.
        """
        def __init__(self):
            """
            This function resets the number of queries being performed.
            """
            # While self.calls = 0, no queries are being run.
            self.calls = 0

        def execute(self, *_):
            """
            This function iterates through the SQL SELECT clause. It returns the 'patient_ID', 'variants' and 'genes'.
            """
            # Increase self.calls by 1 while the DummyCursor class is in operation.
            self.calls += 1

        def fetchall(self):
            """
            Depending on the number of self.calls, this function returns a corresponding list of tuples.
            """
            # If self.calls is 1, the patient_ID column is being queried and 2 patient IDs are returned.
            if self.calls == 1:
                return [("Patient1",), ("Patient2",)]
            # If self.calls is 2, the variants column is being queried and a variant is returned.
            elif self.calls == 2:
                return [("NC_000019.10:g.1",)]
            # If self.calls is 3, the genes column is being queried and a gene symbol is returned.
            elif self.calls == 3:
                return [("ATP1A3",)]
            # Otherwise no queries are being conducted and an empty list should be returned.
            return []

    class DummyConnection:
        """
        Simulate the sqlite3.connect() function.
        """
        def __enter__(self):
            """
            Simulates a 'with' block instance to initialise FakeConn.
            """
            return self

        def __exit__(self, *args):
            """
            Simulates the commitment and closing of the connection to the SQLite3 database, thereby ending the 'with'
            block.
            """
            pass

        def cursor(self):
            """
            Simulates a fake cursor to connect, query and retrieve data from the SQLite3 database from FakeCursor.
            """
            return DummyCursor()

    # Monkeypatch also simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda *_: True)
    # Monkeypatch simulates the sqlite3.connect function from app.py to create a fake connection to a fake database.
    monkeypatch.setattr("app.app.sqlite3.connect", lambda *_: DummyConnection())
    # Use request GET to submit a request to generate dropdown menus on the query page for a selected database.
    response = client.get("/api/dropdown/test.db")
    # Test that a successful request and response were generated without breaking the app, denoted by a response status
    # code of 200.
    assert response.status_code == 200
    # Assign the responses from DummyCursor into the corresponding key values named after the column headers that were
    # queried.
    data = response.get_json()
    # Test that the values from when self.call = 1 are assigned to the "patients" key, signifying the values that would
    # be in the patient query dropdown menu.
    assert data["patients"] == ["Patient1", "Patient2"]
    # Test that the values from when self.call = 2 are assigned to the "variants" key, signifying the values that would
    # be in the variant query dropdown menu.
    assert data["variants"] == ["NC_000019.10:g.1"]
    # Test that the values from when self.call = 3 are assigned to the "genes" key, signifying the values that would
    # be in the gene query dropdown menu.
    assert data["genes"] == ["ATP1A3"]

# -------------------------------------------------------------------------------------
# Test Query page-ERROR: SQLite error when generating dropdown menus on the query page.
# -------------------------------------------------------------------------------------
def test_dropdown_sqlite_error(client, monkeypatch):
    """
    This function tests if app.py can appropriately handle an sqlite3.OperationalError exception as a result of
    executing the dropdown_data() function on the query page, when generating dropdown menus for each type of query.

    To determine if the exception was handled appropriately, the response should return a 200 status code as well as the
    corresponding error message from the sqlite_error error handler.

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response status code of 200 is returned.
                   Test that "Dropdown Menu Error: Something went wrong while accessing the database." is returned.
    """
    # Monkeypatch simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("app.app.os.path.exists", lambda _: True)
    # Monkeypatch simulates the sqlite3.OperationalError exception when dropdown_data() from app.py is executed.
    monkeypatch.setattr("app.app.sqlite3.connect", raise_sqlite_oe)
    # Use request GET to submit a request to generate dropdown menus, in order to raise the sqlite3.OperationalError
    # exception.
    response = client.get("/api/dropdown/test.db")
    # Test that a successful request and response were generated without breaking the app, denoted by a response status
    # code of 200.
    assert response.status_code == 200
    # Test that the corresponding error message is returned when the sqlite3.OperationalError exception is raised while
    # generating the dropdown menus.
    assert b"Dropdown Menu Error: Something went wrong while accessing the database." in response.data

# ----------------------------------------------------------------------------------------
# Test Query page-ERROR: Exception error when generating dropdown menus on the query page.
# ----------------------------------------------------------------------------------------
def test_dropdown_generic_exception(client, monkeypatch):
    """
    This function tests if the dropdown_data() function in app.py can appropriately handle a generic Exception being
    raised as a result of unsuccessfully generating the dropdown menus on the query page. The Exception error handler
    (raise_generic) is used to simulate the exception.

    To determine if the exception was handled appropriately, a response status code of 200 is expected along with the
    expected error message, "Dropdown Menu Error: Dropdown menus do not work."

    :param: client: A fake test client generated by the 'client' pytest fixture.
       monkeypatch: An in-built pytest fixture that allows attributes and variables used in a software to be altered
                    without changing the original attributes and variables being used.

    :test outcome: Test that a response status code of 200 is returned.
                   Test that the error message, "Dropdown Menu Error: Dropdown menus do not work", is returned.
    """
    # Monkeypatch simulates a fake check to determine if the SQLite3 database exists using the os.path.exists
    # function from app.py.
    monkeypatch.setattr("os.path.exists", lambda _: True)
    # Monkeypatch simulates the Exception error when dropdown_data() from app.py is executed.
    monkeypatch.setattr("sqlite3.connect", raise_generic)
    # Use request GET to submit a request to generate dropdown menus, in order to raise the generic Exception error.
    response = client.get("/api/dropdown/test.db")
    # Test that a successful request and response were generated without breaking the app, denoted by a response status
    # code of 200.
    assert response.status_code == 200
    # Test that the corresponding error message is returned when the Exception error is raised while generating the
    # dropdown menus.
    assert b"Dropdown Menu Error: Dropdown menus do not work" in response.data