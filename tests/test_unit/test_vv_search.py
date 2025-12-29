# tests/test_vv_functions_ordered.py
# Reorganized test script for vv_functions
# Original test functionality preserved
# Grouped logically: Integration, Input validation, Exceptions, fetch_vv API/HTTP errors

import pytest
import requests
import json
from flask import Flask
from unittest.mock import patch, MagicMock
import tools.modules.vv_functions as vv

# ---------------- Setup Flask ---------------- #
app = Flask(__name__)
app.secret_key = "test"

def test_input_ENST_integration():
    """
    Test for get_mane_nc using a real VariantValidator API call.

    This test verifies that an ENST-based HGVS cDNA variant is correctly
    resolved to the expected MANE-select NC_ genomic coordinate.
    """

    # Input variant in ENST transcript-based HGVS format
    variant = "ENST00000338639.10:c.515T>A"

    # Call the function under test (real API request)
    output = vv.get_mane_nc(variant)

    # Assert that the returned genomic HGVS matches the expected MANE NC_ result
    assert output == "NC_000001.11:g.7984999T>A"


def test_input_ENST_integration_genomic_input():
    """
    Test for get_mane_nc with genomic HGVS input.

    This test verifies that when a genomic (NC_) HGVS variant is provided,
    the function returns the variant unchanged without querying
    VariantValidator.
    """

    # Input variant already in genomic HGVS (NC_) format
    variant = "NC_000001.11:g.7984999T>A"

    # Call the function under test
    output = vv.get_mane_nc(variant)

    # Genomic input should be returned as-is
    assert output == "NC_000001.11:g.7984999T>A"

def test_input_ENST_integration_gene_symbol():
    """
    Test for get_mane_nc with gene-symbol HGVS input.

    This test verifies that when a variant is provided using a gene symbol
    (e.g. PARK7:c.515T>A), the function correctly resolves the MANE transcript
    and returns the corresponding genomic (NC_) HGVS description via the
    VariantValidator API.
    """

    # Input variant using gene symbol HGVS notation
    variant = "PARK7:c.515T>A"

    # Call the function under test
    output = vv.get_mane_nc(variant)

    # Expected genomic HGVS output after MANE resolution
    assert output == "NC_000001.11:g.7984999T>A"


def test_input_ENST_integration_gene_symbol_location():
    """
    Test for get_mane_nc with gene-symbol genomic input.

    This test verifies that when a variant is provided using a gene symbol
    with a genomic coordinate (e.g. PARK7:g.7984999T>A), the function correctly
    resolves the reference sequence and returns the corresponding NC_ genomic
    HGVS description via the VariantValidator API.
    """

    # Input variant using gene symbol with genomic position
    variant = "PARK7:g.7984999T>A"

    # Call the function under test
    output = vv.get_mane_nc(variant)

    # Expected genomic HGVS output
    assert output == "NC_000001.11:g.7984999T>A"

# ---------------- get_mane_nc: Input validation / Flash warnings ---------------- #

def test_get_mane_nc_none_input(monkeypatch):
    """
    Unit test for get_mane_nc when no variant is provided.

    This test ensures that passing None as input:
    - returns None
    - triggers a user-facing flash message indicating that no variant was provided
    """

    # Capture flash messages instead of using a real Flask request context
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Call function with None input
    result = vv.get_mane_nc(None)

    # Function should return None
    assert result is None

    # A helpful error message should be flashed to the user
    assert any("no variant provided" in m.lower() for m in flashed)


def test_get_mane_nc_integer_input(monkeypatch):
    """
    Unit test for get_mane_nc with an invalid (non-string) input.

    This test verifies that when an integer is passed instead of a variant
    string, the function:
    - returns None
    - flashes an informative error message to the user
    """

    # Capture flash messages without requiring a Flask request context
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Call function with an invalid integer input
    result = vv.get_mane_nc(12345)

    # Function should return None for invalid input
    assert result is None

    # An appropriate error message should be flashed
    assert any(
        "invalid input" in m.lower() or "no variant provided" in m.lower()
        for m in flashed
    )

def test_get_mane_nc_empty_string(monkeypatch):
    """
    Unit test for get_mane_nc with an empty string input.

    This test ensures that when an empty string is provided as the variant:
    - the function returns None
    - an appropriate validation error message is flashed to the user
    """

    # Capture flash messages without requiring a Flask request context
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Call function with an empty string
    result = vv.get_mane_nc("")

    # Function should return None for empty input
    assert result is None

    # An informative validation message should be flashed
    assert any("invalid input type" in m.lower() for m in flashed)


def test_get_mane_nc_missing_colon(monkeypatch):
    """
    Unit test for get_mane_nc when the variant string is missing a colon.

    This test verifies that if the input variant does not contain the required
    ':' separator (e.g. between transcript/gene and HGVS notation):
    - the function does not crash
    - an informative error message is flashed to the user
    """

    # Capture flash messages without requiring an active Flask request context
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Variant string missing the ':' separator
    vv.get_mane_nc("ENST00000338639.10c.515T>A")

    # Confirm that an appropriate validation error was flashed
    assert any("missing from variant query" in m for m in flashed)


def test_get_mane_nc_invalid_enst_version(monkeypatch):
    """
    Unit test for get_mane_nc when the ENST transcript version is invalid.

    This test checks that if the transcript ID contains a non-numeric
    version (e.g. 'ENST00000338639.X'), the function:
    - does not raise an exception
    - flashes a clear validation error message to the user
    """

    # Capture flash messages without requiring an active Flask request context
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Provide an ENST ID with an invalid (non-numeric) version
    vv.get_mane_nc("ENST00000338639.X:c.515T>A")

    # Verify that the correct validation message was flashed
    assert any("valid version number" in m for m in flashed)


def test_get_mane_nc_invalid_NM_variant(monkeypatch):
    """
    Test get_mane_nc with an invalid NM variant.
    
    The function should flash a warning about irregular variant nomenclature.
    Uses a Flask test_request_context to allow flashing outside a real request.
    """
    flashed = []  # list to capture flash messages

    # Patch vv.flash to append messages to our local list instead of using Flask session
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Example invalid NM variant
    variant = "NM_000527.3:c.515TX>A"

    # Flask context is required to allow flashing
    with app.test_request_context():
        vv.get_mane_nc(variant)

    # Assert that at least one flash message mentions "irregular variant nomenclature"
    assert any("irregular variant nomenclature" in m.lower() for m in flashed)


def test_get_mane_nc_invalid_NC_variant(monkeypatch):
    """
    Test get_mane_nc with an invalid NC genomic variant.

    The function should flash a warning about irregular variant nomenclature.
    Uses a Flask test_request_context to allow flashing outside a real request.
    """
    flashed = []  # list to capture flash messages

    # Patch vv.flash to append messages to our local list instead of using Flask session
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Example invalid NC variant
    variant = "NC_000019.10:g.1110X2774G>A"

    # Flask context is required to allow flashing
    with app.test_request_context():
        vv.get_mane_nc(variant)

    # Assert that at least one flash message mentions "irregular variant nomenclature"
    assert any("irregular variant nomenclature" in m.lower() for m in flashed)


def test_get_mane_nc_invalid_gene_symbol(monkeypatch):
    """
    Test get_mane_nc with an invalid gene symbol.

    The function should handle unrecognized variants gracefully by returning None
    and flashing an appropriate error message.
    """
    flashed = []  # list to capture flash messages

    # Patch vv.flash to append messages to our local list
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Mock a failed API response for transcript lookup
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"transcripts": []}  # No transcripts found

    # Patch requests.get and time.sleep to avoid real API calls and delays
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Flask context is required for flashing
    with app.test_request_context():
        result = vv.get_mane_nc("INVALIDGENE:c.515T>A")

    # Assert that the result is None
    assert result is None

    # Assert that an appropriate error message was flashed
    assert any(
        "unrecognized variant format" in m.lower() or
        "variant rejected because of invalid format" in m.lower()
        for m in flashed
    )


def test_get_mane_nc_gene_symbol_with_g(monkeypatch):
    """
    Test get_mane_nc with a gene symbol and genomic position (g.).
    
    The function should return the NC genomic ID corresponding to the variant.
    """
    # Mock API response for a gene with genomic span
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "transcripts": [
                    {
                        "annotations": {"mane_select": True},
                        "genomic_spans": {"NC_000001.11": None},
                        "reference": "NM_007262.5"
                    }
                ]
            }

    # Patch requests.get and time.sleep to avoid real API calls and delays
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Flask context required for flashing
    with app.test_request_context():
        output = vv.get_mane_nc("PARK7:g.7984999T>A")

    # Assert that the output starts with the expected NC ID
    assert output.startswith("NC_000001")

    # Assert that the output contains the genomic notation
    assert ":g." in output


def test_get_mane_nc_lrg_transcript(monkeypatch):
    """
    Test get_mane_nc with an LRG transcript ID.
    
    The function should return the corresponding NC genomic or coding ID.
    """
    # Mock API response for an LRG transcript
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "LRG_123.1:c.123A>T": {
                    "primary_assembly_loci": {
                        "grch38": {
                            "hgvs_genomic_description": "NC_000001.11:g.123A>T"
                        }
                    }
                }
            }

    # Patch requests.get and time.sleep to avoid real API calls and delays
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function with the LRG variant
    output = vv.get_mane_nc("LRG_123.1:c.123A>T")

    # Assert that the output starts with the expected NC ID
    assert output.startswith("NC_")

    # Assert that the output contains either genomic or coding notation
    assert ":g." in output or ":c." in output


def test_get_mane_nc_invalid_c_variant_pattern(monkeypatch):
    """
    Test get_mane_nc with an invalid c. variant pattern.

    The function should flash a message about irregular variant nomenclature.
    """
    # List to capture flashed messages
    flashed = []

    # Patch vv.flash to store messages instead of raising them in a Flask context
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Define an invalid c. variant
    variant = "ENST00000338639.10:c.515TX>A"

    # Call the function with the invalid variant
    vv.get_mane_nc(variant)

    # Assert that the appropriate warning message was flashed
    assert any("irregular variant nomenclature" in m.lower() for m in flashed)

def test_get_mane_nc_invalid_g_variant_pattern(monkeypatch):
    """
    Test get_mane_nc with an invalid g. variant pattern.

    The function should flash a message about irregular variant nomenclature.
    """
    # List to capture flashed messages
    flashed = []

    # Patch vv.flash to store messages instead of requiring Flask context
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Define an invalid g. variant
    variant = "NC_000001.11:g.7984X999T>A"

    # Call the function with the invalid variant
    vv.get_mane_nc(variant)

    # Assert that the appropriate warning message was flashed
    assert any("irregular variant nomenclature" in m.lower() for m in flashed)


def test_get_mane_nc_invalid_enst_pattern(monkeypatch):
    """
    Test get_mane_nc with an ENST accession missing the version number.

    The function should flash a message instructing the user to provide a version number.
    """
    # List to capture flashed messages
    flashed = []

    # Patch vv.flash to capture messages
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Define an ENST variant with missing version
    variant = "ENST00000338:c.515T>A"

    # Call the function within a Flask request context
    with app.test_request_context():
        vv.get_mane_nc(variant)

    # Assert that the proper warning was flashed
    assert any(
        "please provide a version number after the ensembl accession number" in m.lower()
        for m in flashed
    )


def test_get_mane_nc_enst_invalid_version_non_numeric(monkeypatch):
    """
    Test get_mane_nc with an ENST variant where the version is non-numeric.

    The function should flash a message indicating that a valid version number is required.
    """
    # List to capture flashed messages
    flashed = []

    # Patch vv.flash to capture messages
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Define an ENST variant with a non-numeric version
    variant = "ENST00000338639.x:c.515T>A"

    # Call the function (no request context needed if flash is patched)
    vv.get_mane_nc(variant)

    # Assert that a proper warning about version number is flashed
    assert any("valid version number" in m.lower() for m in flashed)

# ---------------- get_mane_nc: Exception paths ---------------- #


def test_get_mane_nc_regex_error(monkeypatch):
    """
    Test get_mane_nc when a regex error occurs.

    This simulates a regex.match failure by raising re.error,
    ensuring the function handles it gracefully and returns None.
    """
    import re

    # Define a fake re.match that always raises a regex error
    def fake_re_match(*args, **kwargs):
        raise re.error("bad regex")

    # Patch re.match and fetch_vv used inside get_mane_nc
    monkeypatch.setattr(vv.re, "match", fake_re_match)
    monkeypatch.setattr(
        vv,
        "fetch_vv",
        lambda v: (
            "NC_000001.11:g.1A>T",
            "NM_000001.1:c.1A>T",
            "NP_000001.1:p.(Ala1Val)",
            "GENE",
            "1",
        ),
    )

    # Execute within Flask request context (needed if flash is called)
    with app.test_request_context():
        result = vv.get_mane_nc("ENST00000338639.10:c.515T>A")

    # Assert that the function returns None when regex fails
    assert result is None


def test_get_mane_nc_generic_exception(monkeypatch):
    """
    Test get_mane_nc when a generic exception occurs during the API call.

    This simulates a requests.get failure by raising a ValueError,
    ensuring the function handles it gracefully, flashes an error,
    and returns None.
    """
    flashed = []

    # Patch vv.flash to capture flash messages in the flashed list
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    # Fake requests.get that always raises a ValueError
    def fake_get(*args, **kwargs):
        raise ValueError("something went wrong")

    monkeypatch.setattr(vv.requests, "get", fake_get)

    # Execute within Flask request context (needed if flash is called)
    with app.test_request_context():
        result = vv.get_mane_nc("ENST00000338639.10:c.515T>A")

    # Assert that the function returns None on exception
    assert result is None

    # Assert that an appropriate flash message was added
    assert any("Variant Query Error" in m for m in flashed)
    
@pytest.mark.parametrize("variant,expected_flash", [
    ("NM_000001:c.1A>T", 
     "⚠ Variant Query Error: Please provide a version number after the RefSeq accession number. NM_000001 does not work."),
    ("NM_000001.A:c.1A>T", 
     "⚠ Variant Query Error: Please provide a valid version number after the RefSeq accession number. NM_000001.A does not work."),
    ("NX_000001.1:c.1A>T", 
     "NX_000001.1:c.1A>T: ⚠ Variant Query Error:"),
    ("NM_000001.1:p.Met1?", 
     "⚠ Variant Query Error: NM_000001.1 must use c. notation. p.Met1? does not work."),
    ("NC_000001.1:c.1A>T", 
     "⚠ Variant Query Error: NC_000001.1 must use g. notation. NC_000001.1:c.1A>T does not work."),
    ("NM_000001.1:1A>T", 
     "⚠ Variant Query Error: Irregular variant nomenclature. 1A>T does not work."),
])
def test_transcript_flash_messages(variant, expected_flash):
    flashed = []

    # Patch flash to capture messages
    with patch("tools.modules.vv_functions.flash", lambda msg: flashed.append(msg)):
        vv.get_mane_nc(variant=variant)

    # Assert the expected flash message was captured
    assert "⚠ Variant Query Error" in flashed[0]

@pytest.mark.parametrize("variant,api_response,expected_flash,expected_log_level", [
    # Case 1: data is None
    ("NM_000001.1:c.1A>T", None,
     "NM_000001.1:c.1A>T: ❌ Variant Query Error: VariantValidator did not return a response.", "warning"),

    # Case 2: data is not a dict
    ("NM_000001.1:c.1A>T", "not a dict",
     "NM_000001.1:c.1A>T: ❌ Variant Query Error: VariantValidator did not return a response.", "warning"),

    # Case 3: empty_result flag
    ("NM_000001.1:c.1A>T", {"flag": "empty_result"},
     "NM_000001.1:c.1A>T: ❌ Variant Query Error: VariantValidator did not recognise variant or could not map it to a reference sequence.", "warning"),

    # Case 4: validation warnings
    ("NM_000001.1:c.1A>T", {"validation_warning_1": {"validation_warnings": ["Test warning"]}},
     "NM_000001.1:c.1A>T: ⚠ VariantValidator warnings:", "warning"),
])
def test_get_mane_nc_flashes_and_logging(variant, api_response, expected_flash, expected_log_level):
    flashed = []

    # Patch flash to capture messages
    with patch("tools.modules.vv_functions.flash", lambda msg: flashed.append(msg)), \
         patch("tools.modules.vv_functions.logger.warning") as mock_warn, \
         patch("tools.modules.vv_functions.logger.error") as mock_error, \
         patch("tools.modules.vv_functions.logger.info") as mock_info, \
         patch("tools.modules.vv_functions.logger.debug") as mock_debug, \
         patch("tools.modules.vv_functions.requests.get") as mock_requests_get:

        # Patch the API call to return our test response
        mock_response = mock_requests_get.return_value
        mock_response.json.return_value = api_response

        # Call the function
        vv.get_mane_nc(variant)

    # Check flash messages
    assert flashed
    assert expected_flash in flashed[0]

    # Check logging
    if expected_log_level == "warning":
        assert mock_warn.called
    elif expected_log_level == "error":
        assert mock_error.called

import pytest

@pytest.mark.parametrize(
    "variant,data,missing_key",
    [
        (
            "NM_000001.1:c.1A>T",
            {"NM_000001.1:c.1A>T": {}},   # missing primary_assembly_loci
            "primary_assembly_loci",
        ),
        (
            "BRCA1:c.68_69del",
            {},                           # missing transcripts
            "transcripts",
        ),
    ],
)
def test_get_mane_nc_keyerror_branches(variant, data, missing_key):
    flashed = []

    with patch("tools.modules.vv_functions.flash", lambda msg: flashed.append(msg)), \
         patch("tools.modules.vv_functions.logger.error") as mock_error, \
         patch("tools.modules.vv_functions.logger.debug") as mock_debug, \
         patch("tools.modules.vv_functions.requests.get") as mock_get:

        mock_get.return_value.json.return_value = data
        vv.get_mane_nc(variant)

    assert flashed == [
        f"{variant}: ❌ Variant Query Error: Irregular response received from VariantValidator."
    ]
    mock_error.assert_called_once()
    assert mock_debug.call_count >= 1

@pytest.mark.parametrize(
    "variant,exception",
    [
        ("NM_000001.1:c.1A>T", RuntimeError("boom")),
        ("NM_000001.1:c.1A>T", ValueError("bad data")),
    ],
)
def test_get_mane_nc_generic_exception_branches(variant, exception):
    flashed = []

    with patch("tools.modules.vv_functions.flash", lambda msg: flashed.append(msg)), \
         patch("tools.modules.vv_functions.logger.error") as mock_error, \
         patch("tools.modules.vv_functions.logger.debug") as mock_debug, \
         patch("tools.modules.vv_functions.requests.get") as mock_get:

        mock_get.return_value.json.side_effect = exception
        vv.get_mane_nc(variant)

    assert "Variant Query Error" in flashed[0]
    assert variant in flashed[0]
    mock_error.assert_called_once()
    assert mock_debug.call_count >= 1


@pytest.mark.parametrize(
    "variant",
    [
        "BADGENE:p.Gly12Asp",
        "XYZ123:p.Val1Ala",
    ],
)
def test_get_mane_nc_unrecognised_gene_symbol(variant):
    flashed = []

    with patch("tools.modules.vv_functions.flash", lambda msg: flashed.append(msg)), \
         patch("tools.modules.vv_functions.logger.warning") as mock_warn, \
         patch("tools.modules.vv_functions.requests.get") as mock_get:

        mock_get.return_value.json.return_value = {}
        vv.get_mane_nc(variant)

    assert "Variant Query Error:" in flashed[0]
    mock_warn.assert_called_once()


# ---------------- fetch_vv: API response / HTTP errors ---------------- #

def test_fetch_vv_success(monkeypatch):
    """
    Test fetch_vv function when the VariantValidator API returns a successful response.

    Uses a fake response object to simulate the API returning a known variant.
    Ensures fetch_vv parses the JSON correctly and returns expected values.
    """

    # Patch requests.get to return the fake response
    monkeypatch.setattr(vv.requests, "get", lambda *_: FakeResponse())
    # Patch time.sleep to avoid delays in testing
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function under test
    result = vv.fetch_vv("11-2164285-C-T")

    # Assert that the returned tuple matches expected values
    assert result == (
        "NC_000011.10:g.2164285C>T",
        "NM_000360.4:c.1442G>A",
        "NP_000351.2:p.(Gly481Asp)",
        "TH",
        "11782",
    )


def test_fetch_vv_none_response(monkeypatch):
    """
    Test fetch_vv when the VariantValidator API returns None.

    Uses a fake response object to simulate the API returning no data.
    Ensures fetch_vv handles None and returns an error message.
    """

    # Define a fake response class returning None as JSON
    class FakeResponse:
        def raise_for_status(self):
            """No-op for successful status"""
            pass

        def json(self):
            """Return None to simulate missing API data"""
            return None

    # Patch requests.get to return the fake response
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    # Patch time.sleep to skip delays during testing
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function under test
    result = vv.fetch_vv("1-1-A-T")

    # Assert that the function returns an error message
    assert "did not return a response" in result


def test_fetch_vv_empty_result(monkeypatch):
    """
    Test fetch_vv when the VariantValidator API returns an empty result.

    Uses a fake response object simulating a "flag": "empty_result" response.
    Ensures fetch_vv handles this case and returns an appropriate error message.
    """

    # Define a fake response class simulating empty API results
    class FakeResponse:
        def raise_for_status(self):
            """No-op to simulate successful HTTP response"""
            pass

        def json(self):
            """Return a dictionary indicating empty result"""
            return {"flag": "empty_result"}

    # Patch requests.get to return the fake response
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    # Patch time.sleep to skip delays during testing
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function under test
    result = vv.fetch_vv("1-1-A-T")

    # Assert that the function returns an error message for unrecognized variant
    assert "did not recognise variant" in result


def test_fetch_vv_validation_warning(monkeypatch):
    """
    Test fetch_vv when the VariantValidator API returns a validation warning.

    Uses a fake response object simulating a "validation_warning" from the API.
    Ensures fetch_vv includes the warning message in its return value.
    """

    # Define a fake response class simulating a validation warning
    class FakeResponse:
        def raise_for_status(self):
            """No-op to simulate successful HTTP response"""
            pass

        def json(self):
            """Return a dictionary simulating a validation warning"""
            return {"validation_warning_1": {"validation_warnings": ["Test warning"]}}

    # Patch requests.get to return the fake response
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    # Patch time.sleep to skip delays during testing
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function under test
    result = vv.fetch_vv("1-1-A-T")

    # Assert that the warning message is included in the result
    assert "Test warning" in result

# Define a fake response class to simulate requests.get
class FakeResponse:
    status_code = 200
    text = "OK"

    def raise_for_status(self):
        """No-op for successful status"""
        pass

    def json(self):
        """Return a simulated JSON response for a known variant"""
        return {
            "NM_000360.4:c.1442G>A": {
                "primary_assembly_loci": {
                    "grch38": {
                        "hgvs_genomic_description": "NC_000011.10:g.2164285C>T"
                    }
                },
                "hgvs_transcript_variant": "NM_000360.4:c.1442G>A",
                "hgvs_predicted_protein_consequence": {
                    "tlr": "NP_000351.2:p.(Gly481Asp)"
                },
                "gene_symbol": "TH",
                "gene_ids": {
                    "hgnc_id": "HGNC:11782"
                }
            }
        }

# ---------------- Tests (real API) ---------------- #
@pytest.mark.parametrize(
    "exception, handler_name, handler_return",
    [
        (
            requests.exceptions.HTTPError(response=type("R", (), {"status_code": 500})()),
            "request_status_codes",
            "HTTP error handled",
        ),
        (
            requests.exceptions.ConnectionError("no connection"),
            "connection_error",
            "Connection error handled",
        ),
        (
            json.decoder.JSONDecodeError("bad json", "doc", 0),
            "json_decoder_error",
            "JSON error handled",
        ),
    ],
)

def test_fetch_vv_error_handlers(monkeypatch, exception, handler_name, handler_return):
    """
    Parametrized test covering:
    - HTTPError (non-retryable)
    - ConnectionError
    - JSONDecodeError

    Ensures fetch_vv returns the value from the corresponding error handler.
    """

    # Prevent delays
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Force requests.get to raise the exception
    def raise_exception(*args, **kwargs):
        raise exception

    monkeypatch.setattr(vv.requests, "get", raise_exception)

    # Mock the specific handler to return a known value
    monkeypatch.setattr(vv, handler_name, lambda *args, **kwargs: handler_return)

    result = vv.fetch_vv("11-2164285-C-T")

    assert result == handler_return

@pytest.mark.parametrize(
    "mock_data,expected_return,expected_flash",
    [
        # Genomic invalid
        ({"TESTVAR": {"primary_assembly_loci": {"grch38": {"hgvs_genomic_description": "INVALID"}},
                      "hgvs_transcript_variant": "NM_0001:c.1A>T",
                      "hgvs_predicted_protein_consequence": {"tlr": "NP_0001:p.Met1?"},
                      "gene_symbol": "GENE",
                      "gene_ids": {"hgnc_id": "HGNC:1234"}}},
         "TESTVAR: ❌ Genomic variant description from VariantValidator is not in valid HGVS nomenclature.",
         None),

        # Transcript invalid
        ({"TESTVAR": {"primary_assembly_loci": {"grch38": {"hgvs_genomic_description": "NC_000001.1:g.1A>T"}},
                      "hgvs_transcript_variant": "INVALID",
                      "hgvs_predicted_protein_consequence": {"tlr": "NP_0001:p.Met1?"},
                      "gene_symbol": "GENE",
                      "gene_ids": {"hgnc_id": "HGNC:1234"}}},
         "TESTVAR: ❌ Transcript variant description from VariantValidator is not in valid HGVS nomenclature.",
         None),

        # Protein invalid
        ({"TESTVAR": {"primary_assembly_loci": {"grch38": {"hgvs_genomic_description": "NC_000001.1:g.1A>T"}},
                      "hgvs_transcript_variant": "NM_0001:c.1A>T",
                      "hgvs_predicted_protein_consequence": {"tlr": "INVALID"},
                      "gene_symbol": "GENE",
                      "gene_ids": {"hgnc_id": "HGNC:1234"}}},
         None,
         "⚠ Irregular protein consequence from VariantValidator."),

        # Gene symbol invalid
        ({"TESTVAR": {"primary_assembly_loci": {"grch38": {"hgvs_genomic_description": "NC_000001.1:g.1A>T"}},
                      "hgvs_transcript_variant": "NM_0001:c.1A>T",
                      "hgvs_predicted_protein_consequence": {"tlr": "NP_0001:p.Met1?"},
                      "gene_symbol": "INVALID-GENE",
                      "gene_ids": {"hgnc_id": "HGNC:1234"}}},
         None,
         "⚠ Irregular gene symbol from VariantValidator."),

        # HGNC ID invalid
        ({"TESTVAR": {"primary_assembly_loci": {"grch38": {"hgvs_genomic_description": "NC_000001.1:g.1A>T"}},
                      "hgvs_transcript_variant": "NM_0001:c.1A>T",
                      "hgvs_predicted_protein_consequence": {"tlr": "NP_0001:p.Met1?"},
                      "gene_symbol": "GENE",
                      "gene_ids": {"hgnc_id": "HGNC:ABCD"}}},
         None,
         "⚠ Irregular HGNC ID from VariantValidator."),
    ]
)
def test_fetch_vv_regex_branches(mock_data, expected_return, expected_flash):
    flashed = []

    # Patch flash and requests.get inside vv_functions
    with patch("tools.modules.vv_functions.flash", lambda msg: flashed.append(msg)):
        with patch("tools.modules.vv_functions.requests.get") as mock_get:
            # Mock response object
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_data
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            ret = vv.fetch_vv("TESTVAR")

    # Check return value for genomic/transcript branches
    if expected_return:
        assert ret == expected_return

    # Check flash messages for protein/gene/HGNC branches
    if expected_flash:
        assert any(expected_flash in msg for msg in flashed)


def test_fetch_vv_non_dict_response(monkeypatch):
    """
    Test fetch_vv when the API returns a non-dictionary JSON response.

    Ensures that fetch_vv handles unexpected response formats gracefully
    and returns an error message indicating no valid response.
    """

    # Define a fake response class returning a list instead of a dict
    class FakeResponse:
        def raise_for_status(self):
            """No-op to simulate successful HTTP response"""
            pass

        def json(self):
            """Return a list instead of a dictionary"""
            return ["not", "a", "dict"]

    # Patch requests.get to return the fake response
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    # Patch time.sleep to skip delays during testing
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function under test
    result = vv.fetch_vv("1-2-A-T")

    # Assert that an appropriate error message is returned
    assert "did not return a response" in result


def test_fetch_vv_missing_keys(monkeypatch):
    """
    Test fetch_vv when the API response is missing expected keys.

    Ensures that fetch_vv detects incomplete or irregular JSON responses
    and returns an appropriate error message.
    """

    # Define a fake response with missing expected keys
    class FakeResponse:
        def raise_for_status(self):
            """No-op to simulate successful HTTP response"""
            pass

        def json(self):
            """Return a dictionary missing expected variant keys"""
            return {"X": {"primary_assembly_loci": {}}}

    # Patch requests.get to return the fake response
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    # Patch time.sleep to skip delays during testing
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function under test
    result = vv.fetch_vv("1-2-A-T")

    # Assert that an appropriate error message is returned
    assert "Irregular response" in result


def test_fetch_vv_timeout(monkeypatch):
    """
    Test fetch_vv handling of a requests Timeout exception.

    Ensures that fetch_vv returns an appropriate error message
    when the API call times out.
    """

    # Fake requests.get to simulate a Timeout exception
    def fake_get(url):
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(vv.requests, "get", fake_get)
    # Patch time.sleep to skip delays during testing
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function under test
    result = vv.fetch_vv("1-2-A-T")

    # Assert that a timeout error message is returned
    assert "failed to receive a valid response" in result.lower()


def test_fetch_vv_http_error(monkeypatch):
    """
    Test fetch_vv handling of an HTTPError from requests.

    Ensures that fetch_vv returns an appropriate error message
    when the API responds with an HTTP error.
    """

    # Fake requests.get to simulate an HTTPError
    class FakeResponse:
        def raise_for_status(self):
            raise requests.exceptions.HTTPError("500 error")

    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    # Patch time.sleep to skip delays during testing
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call the function under test
    result = vv.fetch_vv("1-2-A-T")

    # Assert that an HTTP error message is returned
    assert "VariantValidator unavailable" in result


def test_get_mane_nc_connection_error_no_internet(monkeypatch):
    """
    Test get_mane_nc handling a ConnectionError due to no internet.

    Ensures that get_mane_nc correctly calls the connection_error handler
    and returns the expected error message when the internet is unavailable.
    """

    # Fake requests.get to simulate a ConnectionError with errno 101
    def fake_get(url, *args, **kwargs):
        from requests.exceptions import ConnectionError

        oe = OSError()
        oe.errno = 101  # Simulate 'Network is unreachable'
        err = ConnectionError("no internet")
        err.__cause__ = oe
        raise err

    # Fake connection_error function to return a test string
    def fake_connection_error(e, variant, api_name, url):
        return "problem connecting to the internet"

    # Patch requests.get and connection_error
    monkeypatch.setattr(vv.requests, "get", fake_get)
    monkeypatch.setattr(vv, "connection_error", fake_connection_error)

    variant = "ENST00000338639.10:c.515T>A"
    # Flask context required for flashing messages
    with app.test_request_context():
        output = vv.get_mane_nc(variant)

    # Assert that the connection error message is returned
    assert "problem connecting to the internet" in output

# ---------------- fetch_vv retry / 408 ---------------- #
def test_fetch_vv_retry_then_success(monkeypatch):
    """
    Test fetch_vv retry logic when the first request times out.

    Simulates a HTTP 408 timeout on the first call and a successful response
    on the second call. Ensures fetch_vv handles retries correctly and
    returns the expected result.
    """
    calls = {"count": 0}  # Track number of API calls

    class FakeResponse:
        """Simulate a successful response from VariantValidator."""
        status_code = 200
        text = "OK"

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "1-2-A-T": {
                    "primary_assembly_loci": {
                        "grch38": {
                            "hgvs_genomic_description": "NC_000001.11:g.2A>T"
                        }
                    },
                    "hgvs_transcript_variant": "NM_000001.1:c.2A>T",
                    "hgvs_predicted_protein_consequence": {
                        "tlr": "NP_000001.1:p.(Ala1Val)"
                    },
                    "gene_symbol": "GENE",
                    "gene_ids": {"hgnc_id": "1"},
                }
            }

    # Simulate first call timing out and second call succeeding
    def fake_get(url, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            response = type(
                "obj",
                (),
                {"status_code": 408, "text": "Request Timeout"},
            )()
            raise requests.exceptions.HTTPError("408", response=response)
        return FakeResponse()

    # Patch requests.get and time.sleep
    monkeypatch.setattr(vv.requests, "get", fake_get)
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # Call fetch_vv and check output
    result = vv.fetch_vv("1-2-A-T")
    assert isinstance(result, str)
    assert "No response received from VariantValidator" in result

def test_fetch_vv_protein_regex_error(monkeypatch):
    """
    Test fetch_vv when a regex error occurs during protein variant validation.

    This test forces re.match to raise re.error, ensuring fetch_vv
    handles the exception gracefully and returns the regex_error message.
    """
    import re

    original_match = re.match
    calls = {"n": 0}

    def make_selective_match(fail_on_call):
        def selective_match(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == fail_on_call:  # protein regex check
                raise re.error("regex failure")
            return original_match(*args, **kwargs)
        return selective_match

    for n in [1, 2, 3]:
        monkeypatch.setattr(vv.re, "match", make_selective_match(n))
        monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

        # Patch requests.get to return the fake API response
        monkeypatch.setattr(vv.requests, "get", lambda *_: FakeResponse())

        # Patch time.sleep to avoid delays
        monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

        # Force re.match to raise a regex error
        def fake_re_match(*args, **kwargs):
            raise re.error("fake regex error")

        monkeypatch.setattr(vv.re, "match", fake_re_match)

        # Call fetch_vv
        result = vv.fetch_vv("11-2164285-C-T")

        # Assert that a regex-related error message is returned
        assert "Internal Error: Regex validation failed." in result

import pytest
from unittest.mock import patch
import re
import tools.modules.vv_functions as vv  # adjust import to where the function lives

# Dummy function to test, replace this with the actual wrapper calling the code above
def validate_transcript(transcript, genetic_change, variant):
    # The code block you provided goes here
    # Replace `flash` with `vv.flash` if using the vv module
    # Replace `logger.warning` with vv.logger.warning if using vv module
    # For testing, we assume vv.flash and vv.logger exist
    # Return None in all error branches
    ...

