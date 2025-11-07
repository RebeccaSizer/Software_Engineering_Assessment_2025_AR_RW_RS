import os
import sqlite3
from ...utils.parseVCF import parseVCF
from ...modules.HGVS_convertion import HGVS_converter
from ...modules.detailed_request import get_clinvar_full_info
from ...modules.Entrez import Entrez_fetch_transcript_record

def variantAnnotationsTable(filepath):

    vcf_paths = []

    for file in os.listdir(filepath):
        if file.endswith('.vcf'):
            vcf_paths.append(f'{filepath}/{file}')
        else:
            continue

    for path in vcf_paths:

        vcf = parseVCF(path)

        # Create (or connect to) a database file
        conn = sqlite3.connect('database/sea.db')

        # Create a cursor to run SQL commands
        cursor = conn.cursor()

        # Create a table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS variant_annotations (
            No INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_NC TEXT NOT NULL,
            variant_NM TEXT NOT NULL,
            variant_NP TEXT NOT NULL,
            gene TEXT NOT NULL,
            HGNC_ID INTEGER NOT NULL,
            Classification TEXT NOT NULL,
            Conditions TEXT NOT NULL,
            Stars,
            Review_status TEXT NOT NULL,
            UNIQUE(variant_NC, variant_NM, variant_NP)
        )
        """)

        # Insert example data

        hgvs_dict, transcript, np_change = HGVS_converter(vcf[1])

        for key, value in hgvs_dict.items():

            transcript_dict = Entrez_fetch_transcript_record('A.N.Other@example.com', value)
            gene = transcript_dict['Gene_symbol']
            HGNC_ID = transcript_dict['HGNC_ID']

            clinVar_response = get_clinvar_full_info(value)
            classification = clinVar_response['classification']
            conditions = clinVar_response['conditions']
            stars = clinVar_response['stars']
            review_status = clinVar_response['review_status']

            cursor.execute("""INSERT INTO variant_annotations (variant_NC, variant_NM, variant_NP, gene, HGNC_ID, classification, conditions, stars, review_status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (key, transcript, np_change, gene, HGNC_ID, classification, conditions, stars, review_status))

        # Save (commit) changes and close connection
        conn.commit()
        conn.close()

    print("variant_annotations created/updated successfully!")
