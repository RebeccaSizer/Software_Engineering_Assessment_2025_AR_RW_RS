# tests/test_unit/test_variant_parser.py

import os
import textwrap

import pytest

from tools.utils.parser import variant_parser


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


def test_variant_parser_vcf_skips_irregular_lines_and_prints_message(tmp_path, capsys):
    """
    Lines with fewer than 5 tab-separated fields should be skipped and a message printed.
    """
    vcf_content = textwrap.dedent(
        """\
        ##fileformat=VCFv4.2
        chr1\t1234\t.\tA\tG
        chr2\t5678\t.\tC       # <-- irregular: less than 5 fields after split
        """
    )
    # We introduce an irregular line by omitting ALT and separating with tabs
    # "chr2\t5678\t.\tC\n" -> len(split) == 4

    # Build the content exactly:
    vcf_content = "##fileformat=VCFv4.2\n" \
                  "chr1\t1234\t.\tA\tG\n" \
                  "chr2\t5678\t.\tC\n"

    vcf_file = tmp_path / "Irregular.vcf"
    vcf_file.write_text(vcf_content)

    result = variant_parser(str(vcf_file))
    captured = capsys.readouterr()

    # Only the valid first variant should be parsed
    assert result == ["1-1234-A-G"]

    # Check that an irregular-line message was printed for line 3
    assert "Variant in line 3 from Irregular.vcf is irregular and was not parsed." in captured.out


def test_variant_parser_csv_basic(tmp_path):
    """
    variant_parser should correctly parse a simple CSV file:
    - skip rows whose first column starts with '#'
    - require at least 5 columns
    - combine chrom/pos/ref/alt into 'chrom-pos-ref-alt'
    """
    csv_content = textwrap.dedent(
        """\
        #CHROM,POS,ID,REF,ALT,OTHER
        chr17,45983420,rs1,G,T,foo
        chr4,89822305,rs2,C,G,bar
        """
    )

    csv_file = tmp_path / "Patient2.csv"
    csv_file.write_text(csv_content)

    result = variant_parser(str(csv_file))

    assert result == [
        "17-45983420-G-T",
        "4-89822305-C-G",
    ]


def test_variant_parser_csv_uppercase_extension(tmp_path):
    """
    variant_parser should also work when the file has a .CSV (uppercase) extension.
    """
    csv_content = "chr1,1000,.,A,G\n"
    csv_file = tmp_path / "Sample.CSV"
    csv_file.write_text(csv_content)

    result = variant_parser(str(csv_file))
    assert result == ["1-1000-A-G"]


def test_variant_parser_csv_skips_irregular_rows_and_prints_message(tmp_path, capsys):
    """
    CSV rows with <= 4 columns should be skipped and a message printed.
    """
    csv_content = textwrap.dedent(
        """\
        chr1,1234,.,A,G
        chr2,5678,.,C
        """
    )
    # Second line has only 4 columns (chr2,5678,.,C) -> irregular

    csv_file = tmp_path / "Irregular.csv"
    csv_file.write_text(csv_content)

    result = variant_parser(str(csv_file))
    captured = capsys.readouterr()

    # Only the first row should be parsed
    assert result == ["1-1234-A-G"]

    # Irregular message should mention line 2
    assert "Variant in line 2 from Irregular.csv is irregular and was not parsed." in captured.out


def test_variant_parser_non_vcf_csv_returns_empty_list(tmp_path):
    """
    Files with unsupported extensions should result in an empty list.
    """
    txt_file = tmp_path / "not_variants.txt"
    txt_file.write_text("chr1\t1000\t.\tA\tG\n")

    result = variant_parser(str(txt_file))
    assert result == []