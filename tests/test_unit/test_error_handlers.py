"""
Unit tests for error_handlers (tools/utils/error_handlers.py).

This module contains pytest-based tests that verify correct behaviour
and error handling for functions in error_handlers. Some external
dependencies such as databases, files, and network requests are mocked
using pytest fixtures (e.g. monkeypatch) to ensure deterministic and
isolated testing.

Some tests were initially generated with assistance from ChatGPT and
subsequently refined by the developer.
"""

import json
import sqlite3
import requests
import pytest
from http.client import RemoteDisconnected

from tools.utils.error_handlers import (
    request_status_codes,
    connection_error,
    json_decoder_error,
    regex_error,
    sqlite_error,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

class DummyResponse:
    """
    A dummy response object to simulate `requests.Response` for testing.
    
    Attributes
    ----------
    status_code : int
        HTTP status code to simulate in tests.
    """

    def __init__(self, status_code):
        self.status_code = status_code


class DummyHTTPError(requests.exceptions.HTTPError):
    """
    A dummy HTTPError to simulate `requests.exceptions.HTTPError` with
    an attached response object for testing retry/error handling.

    Attributes
    ----------
    response : DummyResponse
        A dummy response containing the simulated HTTP status code.
    """

    def __init__(self, status_code):
        # Initialize the parent HTTPError with a message
        super().__init__(f"HTTP {status_code}")
        # Attach a dummy response object
        self.response = DummyResponse(status_code)


# ---------------------------------------------------------------------
# request_status_codes tests
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "status_code, expected_text",
    [
        (400, "HTTPError 400"),
        (404, "HTTPError 404"),
        (500, "HTTPError 500"),
        (503, "HTTPError 503"),
        (504, "HTTPError 504"),
    ],
)

def test_request_status_codes_returns_message(status_code, expected_text):
    """
    Test that `request_status_codes` correctly formats a message for
    different HTTP status codes using a dummy HTTPError.

    Parameters
    ----------
    status_code : int
        The simulated HTTP status code.
    expected_text : str
        The expected substring in the formatted error message.
    """
    # Create a dummy HTTPError with the given status code
    e = DummyHTTPError(status_code)

    # Call the function under test
    msg = request_status_codes(
        e,
        variant="11-2164285-C-T",
        url="http://example.com",
        API="TestAPI",
        attempt=0,
    )

    # Ensure a message was returned
    assert msg is not None
    # Ensure the status code text appears in the message
    assert expected_text in msg
    # Ensure the variant string is included in the message
    assert "11-2164285-C-T" in msg


def test_request_status_codes_408_final_attempt(monkeypatch):
    """
    Test that `request_status_codes` handles HTTP 408 (Request Timeout)
    correctly on the final retry attempt without sleeping.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch time.sleep to avoid delays in tests.
    """
    # Patch time.sleep to skip actual sleeping during retries
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # Create a dummy HTTPError for status code 408
    e = DummyHTTPError(408)

    # Call the function simulating the final retry attempt (attempt=3)
    msg = request_status_codes(
        e,
        variant="VAR",
        url="http://example.com",
        API="TestAPI",
        attempt=3,
    )

    # Ensure the message contains the expected HTTP error code
    assert "HTTPError 408" in msg


def test_request_status_codes_429_final_attempt(monkeypatch):
    """
    Test that `request_status_codes` handles HTTP 429 (Too Many Requests)
    correctly on the final retry attempt without sleeping.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch time.sleep to avoid delays in tests.
    """
    # Patch time.sleep to avoid actual delays during retries
    monkeypatch.setattr("time.sleep", lambda *_: None)

    # Create a dummy HTTPError for status code 429
    e = DummyHTTPError(429)

    # Call the function simulating the final retry attempt (attempt=4)
    msg = request_status_codes(
        e,
        variant="VAR",
        url="http://example.com",
        API="TestAPI",
        attempt=4,
    )

    # Ensure the message contains the expected HTTP error code
    assert "HTTPError 429" in msg


# ---------------------------------------------------------------------
# connection_error tests
# ---------------------------------------------------------------------

def test_connection_error_internet_down_errno_101():
    """
    Test that `connection_error` correctly handles a ConnectionError 
    caused by no internet (OSError with errno 101).

    Ensures that the returned message indicates an internet connection issue.
    """
    # Create a ConnectionError and set its cause to OSError(101) (Network unreachable)
    err = requests.exceptions.ConnectionError()
    err.__cause__ = OSError(101, "Network unreachable")

    # Call the connection_error function with dummy parameters
    msg = connection_error(
        err,
        variant="VAR",
        API="TestAPI",
        url="http://example.com",
    )

    # Check that the message mentions an internet connection problem
    assert "internet connection" in msg.lower()


def test_connection_error_remote_disconnected():
    """
    Test that `connection_error` correctly handles a ConnectionError
    caused by a RemoteDisconnected exception.

    Ensures that the returned message indicates the server dropped the connection.
    """
    # Create a ConnectionError and set its cause to RemoteDisconnected
    err = requests.exceptions.ConnectionError()
    err.__cause__ = RemoteDisconnected("Connection closed")

    # Call the connection_error function with dummy parameters
    msg = connection_error(
        err,
        variant="VAR",
        API="TestAPI",
        url="http://example.com",
    )

    # Check that the message mentions the server dropped the connection
    assert "server dropped the connection" in msg.lower()


def test_connection_error_generic():
    """
    Test that `connection_error` handles a generic ConnectionError.

    Ensures that the returned message indicates there is a general problem
    with the user's connection.
    """
    # Create a generic ConnectionError
    err = requests.exceptions.ConnectionError("boom")

    # Call the connection_error function with dummy parameters
    msg = connection_error(
        err,
        variant="VAR",
        API="TestAPI",
        url="http://example.com",
    )

    # Check that the message mentions a general connection problem
    assert "problem with your connection" in msg.lower()


# ---------------------------------------------------------------------
# json_decoder_error tests
# ---------------------------------------------------------------------

def test_json_decoder_error_returns_message():
    """
    Test that `json_decoder_error` returns an appropriate message
    when a JSONDecodeError is raised.

    Ensures that the returned message indicates the variant data is
    not in valid JSON format.
    """
    # Create a JSONDecodeError for testing
    e = json.JSONDecodeError("Expecting value", "{}", 1)

    # Call the json_decoder_error function with dummy parameters
    msg = json_decoder_error(
        e,
        variant="VAR",
        url="http://example.com",
    )

    # Assert that a message is returned
    assert msg is not None
    # Assert that the message mentions invalid JSON format
    assert "not in JSON format" in msg

# ---------------------------------------------------------------------
# regex_error tests
# ---------------------------------------------------------------------

def test_regex_error_returns_message():
    """
    Test that `regex_error` returns an appropriate message when a
    regular expression compilation fails.

    Ensures that the returned message indicates a regex validation failure.
    """
    import re

    try:
        # Attempt to compile an invalid regex pattern
        re.compile("[z-a]")
    except re.error as e:
        # Call the regex_error function with the caught exception
        msg = regex_error(e, "VAR")

    # Assert that a message is returned
    assert msg is not None
    # Assert that the message mentions regex validation failure
    assert "Regex validation failed" in msg

# ---------------------------------------------------------------------
# sqlite_error tests
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "exception",
    [
        sqlite3.OperationalError("fail"),
        sqlite3.DatabaseError("fail"),
        sqlite3.ProgrammingError("fail"),
    ],
)

def test_sqlite_error_returns_generic_message(exception):
    """
    Test that `sqlite_error` returns a generic error message when
    a SQLite exception occurs.

    Ensures that the returned message mentions a problem with the database.
    """
    # Call the sqlite_error function with the provided exception
    msg = sqlite_error(exception, "test.db")

    # Assert that a message is returned
    assert msg is not None
    # Assert that the message indicates a database problem
    assert "something wrong with the database" in msg.lower()