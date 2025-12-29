import pytest
from tools.utils.stringify import stringify


def test_stringify_regular_string():
    """
    Test that stringify returns a regular string unchanged.
    """
    # Input is already a valid string
    assert stringify("Patient1") == "Patient1"


def test_stringify_integer():
    """
    Test that stringify converts an integer input to a string.
    """
    # Integer input should be cast to its string representation
    assert stringify(16369) == "16369"


def test_stringify_unicode_character():
    """
    Test that stringify correctly handles and preserves unicode characters.
    """
    # Unicode input should be returned unchanged as a string
    assert stringify("★") == "★"


@pytest.mark.parametrize(
    "value, expected",
    [
        ("=1+1", "'=1+1"),
        ("+SUM(A1:A3)", "'+SUM(A1:A3)"),
        ("-value", "'-value"),
        ("@command", "'@command"),
        ("*important", "'*important"),
    ],
)
def test_stringify_excel_unsafe_prefixes(value, expected):
    """
    Test that stringify safely escapes Excel-unsafe prefixes.

    Strings starting with characters that may be interpreted as formulas
    in spreadsheet software should be prefixed with a single quote.
    """
    # Verify that potentially unsafe spreadsheet input is escaped
    assert stringify(value) == expected


def test_stringify_empty_string():
    """
    Test that stringify returns an empty string when given an empty string.
    """
    # An empty string should remain unchanged
    assert stringify("") == ""
