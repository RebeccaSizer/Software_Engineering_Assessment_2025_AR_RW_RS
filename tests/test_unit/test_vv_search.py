
# These tests check the function which searches VariantValidator using an ID inputted by the user and returns the 
# corresponding MANE NC_ genomic sID.  Some were written by the developer and checked and refined by them using ChatGPT.
# Some tests were suggested by ChatGPT and refined by the developer.   ChatGPT suggested using monkeypatch
# to mock API responses to avoid making real API calls during testing.

import os
import io
import pytest
from tools.modules.vv_functions import get_mane_nc 
import tools.modules.vv_functions as vv 


def test_input_ENST_integration():
    """
    Integration test: uses real VariantValidator API.
    """
    variant = "ENST00000338639.10:c.515T>A"
    output = get_mane_nc(variant)

    # The function should return the NC_ genomic ID only,
    assert output == "NC_000001.11:g.7984999T>A"

def test_input_ENST_integration_genomic_input():
    """
    If the user inputs a genomic ID, the function should return it as is.
    """
    variant = "NC_000001.11:g.7984999T>A"
    output = get_mane_nc(variant)

    # The function should return the NC_ genomic ID,
    
    assert output == "NC_000001.11:g.7984999T>A"

def test_input_ENST_integration_gene_symbol():
    """
    If the user inputs a gene symbol, the function should return the transcript.
    """
    variant = "PARK7:c.515T>A"
    output = get_mane_nc(variant)

    # The function should return the NM transcript ID,
    
    assert output == "NC_000001.11:g.7984999T>A"

def test_input_ENST_integration_gene_symbol_location():
    """
    If the user inputs a gene symbol and base number, the function should return the genomic ID.
    """
    variant = "PARK7:g.7984999T>A"
    output = get_mane_nc(variant)

    # The function should return the NC Genomic transcript ID,
    
    assert output == "NC_000001.11:g.7984999T>A"

def test_enst_without_c_notation(monkeypatch):
    flashed = []

    def fake_flash(msg):
        flashed.append(msg)

    monkeypatch.setattr(vv, "flash", fake_flash)

    # This should hit the branch where ENST + non-c. is rejected
    variant = "ENST00000338639.10:g.515T>A"
    output = vv.get_mane_nc(variant)

    # Output is probably None, but key thing: warning is flashed
    assert any("must use c. notation" in m for m in flashed)

    def test_get_mane_nc_retries_on_408(monkeypatch):
      
        calls = {"count": 0}

    class FakeResponse:
        def __init__(self, status_code=200):
            self.status_code = status_code
        def raise_for_status(self):
            if self.status_code != 200:
                raise vv.requests.exceptions.HTTPError(response=self)

        def json(self):
            # Success payload if we reach here
            return {
                "NM_007262.5:c.515T>A": {
                    "primary_assembly_loci": {
                        "grch38": {
                            "hgvs_genomic_description": "NC_000001.11:g.7984999T>A"
                        }
                    }
                }
            }

    def fake_get(url):
        calls["count"] += 1
        # First call: 408 -> should be retried
        if calls["count"] == 1:
            return FakeResponse(status_code=408)
        return FakeResponse(status_code=200)

    def fake_request_status_codes(e, variant, url, api_name, attempt):
        return "RETRY_ERROR"

    monkeypatch.setattr(vv.requests, "get", fake_get)
    monkeypatch.setattr(vv, "request_status_codes", fake_request_status_codes)
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    variant = "ENST00000338639.10:c.515T>A"
    output = vv.get_mane_nc(variant)

    assert output == "NC_000001.11:g.7984999T>A"
    assert calls["count"] == 2  # 1 failure + 1 retry

    def test_get_mane_nc_connection_error_no_internet(monkeypatch):

        class Dummy(Exception):
            pass

    def fake_get(url):
        # Simulate ConnectionError with OSError(errno=101) as __cause__
        oe = OSError()
        oe.errno = 101
        err = vv.requests.exceptions.ConnectionError("no internet")
        err.__cause__ = oe
        raise err

    monkeypatch.setattr(vv.requests, "get", fake_get)

    variant = "ENST00000338639.10:c.515T>A"
    output = vv.get_mane_nc(variant)

    assert "problem connecting to the internet" in output

    def test_fetch_vv_success(monkeypatch):

    # ---- Fake HTTP response ----
        class FakeResponse:
            status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "NM_000360.4:c.1442G>A": {
                    "primary_assembly_loci": {
                        "grch38": {
                            "hgvs_genomic_description": "NC_000011.10:g.2164285C>T"
                        }
                    },
                    "hgvs_predicted_protein_consequence": {
                        "tlr": "NP_000351.2:p.(Gly481Asp)"
                    },
                    "gene_symbol": "TH",
                    "gene_ids": {
                        "hgnc_id": "HGNC:11782"
                    }
                }
            }

    # ---- Monkey patch HTTP + sleep ----
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    # ---- Call function under test ----
    result = vv.fetch_vv("11-2164285-C-T")

    # ---- Assertion ----
    assert result == (
        "NC_000011.10:g.2164285C>T",
        "NM_000360.4:c.1442G>A",
        "NP_000351.2:p.(Gly481Asp)",
        "TH",
        "11782",
    )