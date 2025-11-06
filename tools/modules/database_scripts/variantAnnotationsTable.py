import os
import sqlite3
from ...utils.parseVCF import parseVCF
from ...modules.HGVS_convertion import HGVS_converter
from ...modules.detailed_request import get_clinvar_full_info

vcf_paths = ['/home/ubuntu/Desktop/Software_Engineering_Assessment_2025_AR_RW_RS/Patient1.vcf']

for path in vcf_paths:

    vcf = parseVCF(path)

    # Create (or connect to) a database file
    conn = sqlite3.connect('/home/ubuntu/Desktop/Software_Engineering_Assessment_2025_AR_RW_RS/database/sea.db')

    # Create a cursor to run SQL commands
    cursor = conn.cursor()

    # Create a table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS variant_annotations (
        No INTEGER PRIMARY KEY AUTOINCREMENT,
        variant TEXT UNIQUE NOT NULL,
        variant_NM TEXT UNIQUE NOT NULL,
        gene TEXT NOT NULL,
        HGNC_ID INTEGER NOT NULL,
        Classification TEXT NOT NULL,
        Conditions TEXT NOT NULL,
        Stars,
        Review_status TEXT NOT NULL
    )
    """)

    # Insert example data
    for key, value in HGVS_converter(vcf[1]).items():

        clinVar_response = get_clinvar_full_info(value)
        classification = clinVar_response['classification']
        conditions = clinVar_response['conditions']
        stars = clinVar_response['stars']
        review_status = clinVar_response['review_status']

        transcript = value.split(':')[0]


    cursor.execute("INSERT INTO variant_annotations (variant, variant_NM, classification, conditions, stars, review_status) VALUES (?, ?)", (key, value, classification, conditions, stars, review_status))

    # Save (commit) changes and close connection
    conn.commit()
    conn.close()

print("variant_annotations created/updated successfully!")
