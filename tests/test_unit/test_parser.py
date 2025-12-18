# tests/test_unit/test_variant_parser.py

import os
import textwrap
import pytest
from tools.utils.parser import variant_parser
from unittest.mock import patch

def test_variant_parser_vcf_basic(tmp_path):
    """
    variant_parser should correctly parse a simple VCF file:
    - skip header lines starting with '#'
    - parse chrom/pos/ref/alt into 'chrom-pos-ref-alt'
    - strip 'chr' prefix from CHROM field
    """
    vcf_content = textwrap.dedent(
        """\
        ##fileformat=VCFv4.2
        #CHROM\tPOS\tID\tREF\tALT
        chr17\t45983420\trs1\tG\tT
        chr4\t89822305\trs2\tC\tG
        """
    )

    vcf_file = tmp_path / "Patient1.vcf"
    vcf_file.write_text(vcf_content)

    result = variant_parser(str(vcf_file))

    assert result == [
        "17-45983420-G-T",
        "4-89822305-C-G",
    ]


def test_variant_parser_vcf_uppercase_extension(tmp_path):
    """
    variant_parser should also work when the file has a .VCF (uppercase) extension.
    """
    vcf_content = textwrap.dedent(
        """\
        ##header
        chr1\t1000\t.\tA\tG
        """
    )

    vcf_file = tmp_path / "Sample.VCF"
    vcf_file.write_text(vcf_content)

    result = variant_parser(str(vcf_file))

    assert result == ["1-1000-A-G"]


from flask import Flask

def test_variant_parser_vcf_skips_irregular_lines_and_prints_message(tmp_path, capsys):
    app = Flask(__name__)
    app.secret_key = 'test'  # Needed for flashing messages

    vcf_file = tmp_path / "Irregular.vcf"
    vcf_file.write_text(
        "##fileformat=VCFv4.2\n"
        "chr1\t1234\t.\tA\tG\n"
        "chr2\t5678\t.\tC\n"
    )

    with app.test_request_context('/'):
        result = variant_parser(str(vcf_file))

    assert '1-1234-A-G' in result


# -----------------------------
# Basic CSV parsing test
# -----------------------------
def test_variant_parser_csv_basic(tmp_path):
    # Make sure we use tabs (\t) between fields
    csv_content = textwrap.dedent(
        """\
        #CHROM\tPOS\tID\tREF\tALT\tOTHER
        chr17\t45983420\trs1\tG\tT\tfoo
        chr4\t89822305\trs2\tC\tG\tbar
        """
    )

    csv_file = tmp_path / "Patient2.csv"
    csv_file.write_text(csv_content)

    # Patch flash to avoid Flask context issues
    with patch("tools.utils.parser.flash"):
        result = variant_parser(str(csv_file))

    # Check the variants are correctly parsed
    assert result is not None
    assert '17-45983420-G-T' in result
    assert '4-89822305-C-G' in result


# -----------------------------
# CSV file with uppercase extension
# -----------------------------
def test_variant_parser_csv_uppercase_extension(tmp_path):
    csv_content = textwrap.dedent(
        """\
        #CHROM\tPOS\tID\tREF\tALT
        chr1\t1000\t.\tA\tG
        """
    )
    csv_file = tmp_path / "Sample.CSV"
    csv_file.write_text(csv_content)

    with patch("tools.utils.parser.flash"):
        result = variant_parser(str(csv_file))

    assert result is not None
    assert '1-1000-A-G' in result


# -----------------------------
# Unsupported file type returns None
# -----------------------------
def test_variant_parser_non_vcf_csv_returns_empty_list(tmp_path):
    txt_file = tmp_path / "not_variants.txt"
    txt_file.write_text("chr1\t1000\t.\tA\tG\n")

    with patch("tools.utils.parser.flash"):
        result = variant_parser(str(txt_file))

    # Parser should return None when no valid variants were found
    assert result is None


# -----------------------------
# CSV with insufficient columns
# -----------------------------
def test_variant_parser_csv_insufficient_columns(tmp_path):
    csv_content = textwrap.dedent(
        """\
        #CHROM\tPOS\tID
        chr1\t1000\t.
        """
    )
    csv_file = tmp_path / "insufficient.csv"
    csv_file.write_text(csv_content)

    with patch("tools.utils.parser.flash"):
        result = variant_parser(str(csv_file))

    # All rows are skipped, so result should be None
    assert result is None
