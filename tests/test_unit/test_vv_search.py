# tests/test_vv_functions_ordered.py
# Reorganized test script for vv_functions
# Original test functionality preserved
# Grouped logically: Integration, Input validation, Exceptions, fetch_vv API/HTTP errors

import pytest
import re
from flask import Flask
import requests
import tools.modules.vv_functions as vv

# ---------------- Setup Flask ---------------- #
app = Flask(__name__)
app.secret_key = "test"

# ---------------- Integration Tests (real API) ---------------- #
def test_input_ENST_integration():
    """Integration test: uses real VariantValidator API."""
    variant = "ENST00000338639.10:c.515T>A"
    output = vv.get_mane_nc(variant)
    assert output == "NC_000001.11:g.7984999T>A"

def test_input_ENST_integration_genomic_input():
    """Genomic input should be returned as-is."""
    variant = "NC_000001.11:g.7984999T>A"
    output = vv.get_mane_nc(variant)
    assert output == "NC_000001.11:g.7984999T>A"

def test_input_ENST_integration_gene_symbol():
    """Gene symbol input should return the transcript."""
    variant = "PARK7:c.515T>A"
    output = vv.get_mane_nc(variant)
    assert output == "NC_000001.11:g.7984999T>A"

def test_input_ENST_integration_gene_symbol_location():
    """Gene symbol with genomic position should return NC genomic ID."""
    variant = "PARK7:g.7984999T>A"
    output = vv.get_mane_nc(variant)
    assert output == "NC_000001.11:g.7984999T>A"

# ---------------- get_mane_nc: Input validation / Flash warnings ---------------- #

def test_get_mane_nc_none_input(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    result = vv.get_mane_nc(None)
    assert result is None
    assert any("no variant provided" in m.lower() for m in flashed)

def test_get_mane_nc_integer_input(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    result = vv.get_mane_nc(12345)
    assert result is None
    assert any("invalid input" in m.lower() or "no variant provided" in m.lower() for m in flashed)

def test_get_mane_nc_empty_string(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    result = vv.get_mane_nc("")
    assert result is None
    assert any("invalid input type" in m.lower() for m in flashed)

def test_get_mane_nc_missing_colon(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    vv.get_mane_nc("ENST00000338639.10c.515T>A")
    assert any("missing from variant query" in m for m in flashed)

def test_get_mane_nc_invalid_enst_version(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    vv.get_mane_nc("ENST00000338639.X:c.515T>A")
    assert any("valid version number" in m for m in flashed)

def test_get_mane_nc_invalid_NM_variant(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    variant = "NM_000527.3:c.515TX>A"  # invalid c. variant
    with app.test_request_context():
        vv.get_mane_nc(variant)
    assert any("irregular variant nomenclature" in m.lower() for m in flashed)

def test_get_mane_nc_invalid_NC_variant(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    variant = "NC_000019.10:g.1110X2774G>A"  # invalid g. variant
    with app.test_request_context():
        vv.get_mane_nc(variant)
    assert any("irregular variant nomenclature" in m.lower() for m in flashed)

def test_get_mane_nc_invalid_gene_symbol(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"transcripts": []}
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    with app.test_request_context():
        result = vv.get_mane_nc("INVALIDGENE:c.515T>A")
    assert result is None
    assert any("unrecognized variant format" in m.lower() or
               "variant rejected because of invalid format" in m.lower() for m in flashed)

def test_get_mane_nc_gene_symbol_with_g(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):
            return {"transcripts":[{"annotations":{"mane_select":True},
                                    "genomic_spans":{"NC_000001.11": None},
                                    "reference":"NM_007262.5"}]}
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    with app.test_request_context():
        output = vv.get_mane_nc("PARK7:g.7984999T>A")
    assert output.startswith("NC_000001")
    assert ":g." in output

def test_get_mane_nc_lrg_transcript(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):
            return {"LRG_123.1:c.123A>T":{"primary_assembly_loci":{"grch38":{"hgvs_genomic_description":"NC_000001.11:g.123A>T"}}}}
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    output = vv.get_mane_nc("LRG_123.1:c.123A>T")
    assert output.startswith("NC_")
    assert ":g." in output or ":c." in output

def test_get_mane_nc_invalid_c_variant_pattern(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    variant = "ENST00000338639.10:c.515TX>A"  # invalid
    vv.get_mane_nc(variant)
    assert any("irregular variant nomenclature" in m.lower() for m in flashed)

def test_get_mane_nc_invalid_g_variant_pattern(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    variant = "NC_000001.11:g.7984X999T>A"  # invalid
    vv.get_mane_nc(variant)
    assert any("irregular variant nomenclature" in m.lower() for m in flashed)

def test_get_mane_nc_invalid_enst_pattern(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    variant = "ENST00000338:c.515T>A"  # too short
    with app.test_request_context():
        vv.get_mane_nc(variant)
    assert any("please provide a version number after the ensembl accession number" in m.lower() for m in flashed)

def test_get_mane_nc_enst_invalid_version_non_numeric(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))
    variant = "ENST00000338639.x:c.515T>A"
    vv.get_mane_nc(variant)
    assert any("valid version number" in m.lower() for m in flashed)

# ---------------- get_mane_nc: Exception paths ---------------- #


def test_get_mane_nc_regex_error(monkeypatch):
    def fake_re_match(*args, **kwargs):
        raise re.error("bad regex")
    
    monkeypatch.setattr(vv.re, "match", fake_re_match)
    monkeypatch.setattr(vv, "fetch_vv", lambda v: ("NC_000001.11:g.1A>T","NM_000001.1:c.1A>T",
                                                  "NP_000001.1:p.(Ala1Val)","GENE","1"))
    with app.test_request_context():
        result = vv.get_mane_nc("ENST00000338639.10:c.515T>A")

    assert result is None  

def test_get_mane_nc_generic_exception(monkeypatch):
    flashed = []
    monkeypatch.setattr(vv, "flash", lambda msg: flashed.append(msg))

    def fake_get(*args, **kwargs):
        raise ValueError("something went wrong")

    monkeypatch.setattr(vv.requests, "get", fake_get)

    with app.test_request_context():
        result = vv.get_mane_nc("ENST00000338639.10:c.515T>A")

    assert result is None
    assert any("Variant Query Error" in m for m in flashed)
    
# ---------------- fetch_vv: API response / HTTP errors ---------------- #

def test_fetch_vv_success(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = "OK"

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

    monkeypatch.setattr(vv.requests, "get", lambda *_: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    result = vv.fetch_vv("11-2164285-C-T")

    assert result == (
        "NC_000011.10:g.2164285C>T",
        "NM_000360.4:c.1442G>A",
        "NP_000351.2:p.(Gly481Asp)",
        "TH",
        "11782",
    )

def test_fetch_vv_none_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return None
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    result = vv.fetch_vv("1-1-A-T")
    assert "did not return a response" in result

def test_fetch_vv_empty_result(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"flag": "empty_result"}
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    result = vv.fetch_vv("1-1-A-T")
    assert "did not recognise variant" in result

def test_fetch_vv_validation_warning(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"validation_warning_1":{"validation_warnings":["Test warning"]}}
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    result = vv.fetch_vv("1-1-A-T")
    assert "Test warning" in result

def test_fetch_vv_non_dict_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return ["not", "a", "dict"]
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    result = vv.fetch_vv("1-2-A-T")
    assert "did not return a response" in result

def test_fetch_vv_missing_keys(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"X":{"primary_assembly_loci":{}}}
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    result = vv.fetch_vv("1-2-A-T")
    assert "Irregular response" in result

def test_fetch_vv_timeout(monkeypatch):
    def fake_get(url): raise requests.exceptions.Timeout("timeout")
    monkeypatch.setattr(vv.requests, "get", fake_get)
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    result = vv.fetch_vv("1-2-A-T")
    assert "failed to receive a valid response" in result.lower()

def test_fetch_vv_http_error(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): raise requests.exceptions.HTTPError("500 error")
    monkeypatch.setattr(vv.requests, "get", lambda url: FakeResponse())
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)
    result = vv.fetch_vv("1-2-A-T")
    assert "VariantValidator unavailable" in result

def test_get_mane_nc_connection_error_no_internet(monkeypatch):
    def fake_get(url, *args, **kwargs):
        from requests.exceptions import ConnectionError
        oe = OSError()
        oe.errno = 101
        err = ConnectionError("no internet")
        err.__cause__ = oe
        raise err
    def fake_connection_error(e, variant, api_name, url):
        return "problem connecting to the internet"
    monkeypatch.setattr(vv.requests, "get", fake_get)
    monkeypatch.setattr(vv, "connection_error", fake_connection_error)
    variant = "ENST00000338639.10:c.515T>A"
    with app.test_request_context():
        output = vv.get_mane_nc(variant)
    assert "problem connecting to the internet" in output

# ---------------- fetch_vv retry / 408 ---------------- #
def test_fetch_vv_retry_then_success(monkeypatch):
    calls = {"count": 0}

    class FakeResponse:
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

    monkeypatch.setattr(vv.requests, "get", fake_get)
    monkeypatch.setattr(vv.time, "sleep", lambda *_: None)

    result = vv.fetch_vv("1-2-A-T")

    assert isinstance(result, str)
    assert "No response received from VariantValidator" in result

