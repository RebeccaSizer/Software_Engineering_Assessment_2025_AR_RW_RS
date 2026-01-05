"""
Unit tests for parser (tools/utils/parser.py).

This module contains pytest-based tests that verify correct behaviour
and error handling for functions in parser. 

Some tests were initially generated with assistance from ChatGPT and
subsequently refined by the developer.
"""

import textwrap
import pytest
from flask import Flask
from unittest.mock import patch
from tools.utils.parser import variant_parser

def test_variant_parser_vcf_basic(tmp_path):
    """
    Test that `variant_parser` correctly parses a basic VCF file.

    The parser should:
    - Ignore header lines beginning with '#'
    - Extract CHROM, POS, REF, and ALT fields
    - Remove any 'chr' prefix from the chromosome field
    - Format variants as 'chrom-pos-ref-alt'
    """
    # Create minimal VCF content with headers and two variant records
    vcf_content = textwrap.dedent(
        """\
        ##fileformat=VCFv4.2
        #CHROM\tPOS\tID\tREF\tALT
        chr17\t45983420\trs1\tG\tT
        chr4\t89822305\trs2\tC\tG
        """
    )

    # Write the VCF content to a temporary file
    vcf_file = tmp_path / "Patient1.vcf"
    vcf_file.write_text(vcf_content)

    # Run the variant parser on the temporary VCF file
    result = variant_parser(str(vcf_file))

    # Verify that variants are correctly parsed and formatted
    assert result == [
        "17-45983420-G-T",
        "4-89822305-C-G",
    ]


def test_variant_parser_vcf_uppercase_extension(tmp_path):
    """
    Test that `variant_parser` correctly processes files with an uppercase
    `.VCF` file extension.
    """
    # Minimal VCF content with a single variant record
    vcf_content = textwrap.dedent(
        """\
        ##header
        chr1\t1000\t.\tA\tG
        """
    )

    # Create a VCF file using an uppercase file extension
    vcf_file = tmp_path / "Sample.VCF"
    vcf_file.write_text(vcf_content)

    # Run the parser on the VCF file
    result = variant_parser(str(vcf_file))

    # Confirm that the variant is parsed and formatted correctly
    assert result == ["1-1000-A-G"]



def test_variant_parser_vcf_skips_irregular_lines_and_prints_message(
    tmp_path,
    capsys,
):
    """
    Test that `variant_parser`:
    - correctly parses valid VCF lines
    - skips irregular or malformed variant lines
    - continues processing without raising an exception
    """
    # Create a minimal Flask app to support flashing or request context usage
    app = Flask(__name__)
    app.secret_key = "test"  # Required for flash messages

    # Create a VCF file with one valid line and one malformed line
    vcf_file = tmp_path / "Irregular.vcf"
    vcf_file.write_text(
        "##fileformat=VCFv4.2\n"
        "chr1\t1234\t.\tA\tG\n"   # Valid VCF line
        "chr2\t5678\t.\tC\n"      # Invalid VCF line (missing ALT column)
    )

    # Run the parser within a Flask request context
    with app.test_request_context("/"):
        result = variant_parser(str(vcf_file))

    # Confirm the valid variant was parsed correctly
    assert "1-1234-A-G" in result


# -----------------------------
# Basic CSV parsing test
# -----------------------------
def test_variant_parser_csv_basic(tmp_path):
    """
    Test that `variant_parser` correctly parses a basic CSV file:
    - fields are tab-delimited
    - header lines are ignored
    - chromosome prefixes ('chr') are stripped
    - variants are returned in 'chrom-pos-ref-alt' format
    """
    # Define tab-delimited CSV content (VCF-like structure)
    csv_content = textwrap.dedent(
    """\
    #CHROM,POS,ID,REF,ALT,OTHER
    chr17,45983420,rs1,G,T,foo
    chr4,89822305,rs2,C,G,bar
    """
    )

    # Write the CSV file to a temporary directory
    csv_file = tmp_path / "Patient2.csv"
    csv_file.write_text(csv_content)

    # Patch `flash` to avoid requiring a Flask request context
    with patch("tools.utils.parser.flash"):
        result = variant_parser(str(csv_file))

    # Verify that parsing succeeded
    assert result is not None

    # Confirm that both variants were parsed correctly
    assert "17-45983420-G-T" in result
    assert "4-89822305-C-G" in result


# -----------------------------
# CSV file with uppercase extension
# -----------------------------
def test_variant_parser_csv_uppercase_extension(tmp_path):
    """
    Test that `variant_parser` correctly parses a CSV file with an uppercase
    '.CSV' extension:
    - header lines starting with '#' are ignored
    - chromosome prefixes ('chr') are stripped
    - variants are returned in 'chrom-pos-ref-alt' format
    """
    # Define tab-delimited CSV content
    csv_content = textwrap.dedent(
        """\
        #CHROM,POS,ID,REF,ALT
        chr1,1000,.,A,G
        """
    )

    # Write the CSV file with uppercase extension
    csv_file = tmp_path / "Sample.CSV"
    csv_file.write_text(csv_content)

    # Patch `flash` to avoid requiring a Flask request context
    with patch("tools.utils.parser.flash"):
        result = variant_parser(str(csv_file))

    # Verify that parsing succeeded
    assert result is not None

    # Confirm that the variant was parsed correctly
    assert "1-1000-A-G" in result


# -----------------------------
# Unsupported file type returns None
# -----------------------------
def test_variant_parser_non_vcf_csv_returns_empty_list(tmp_path):
    """
    Test that `variant_parser` returns None when a non-VCF/CSV file is provided:
    - lines in a plain text file are not recognized as variants
    - no exceptions should be raised
    """
    # Create a plain text file that resembles variant data but is not a recognized format
    txt_file = tmp_path / "not_variants.txt"
    txt_file.write_text("chr1\t1000\t.\tA\tG\n")

    # Patch `flash` to avoid Flask request context errors
    with patch("tools.utils.parser.flash"):
        result = variant_parser(str(txt_file))

    # Expect the parser to return None for unrecognized formats
    assert result is None


# -----------------------------
# CSV with insufficient columns
# -----------------------------
def test_variant_parser_csv_insufficient_columns(tmp_path):
    """
    Test that `variant_parser` returns None when CSV/VCF rows have insufficient columns:
    - CSV has only CHROM, POS, ID fields
    - Required REF and ALT fields are missing
    - All rows should be skipped without raising exceptions
    """
    # Create a CSV file with insufficient columns
    csv_content = textwrap.dedent(
        """\
        #CHROM\tPOS\tID
        chr1\t1000\t.
        """
    )
    csv_file = tmp_path / "insufficient.csv"
    csv_file.write_text(csv_content)

    # Patch `flash` to prevent Flask context errors during testing
    with patch("tools.utils.parser.flash"):
        result = variant_parser(str(csv_file))

    # Expect parser to return None since no valid variants exist
    assert result is None