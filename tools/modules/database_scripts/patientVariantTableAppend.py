import os
import sqlite3
from ...utils.parseVCF import parseVCF
from ...modules.HGVS_convertion import HGVS_converter

def patientVariantTable(filepath):

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
        CREATE TABLE IF NOT EXISTS patient_variant (
            No INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_ID TEXT NOT NULL,
            variant TEXT NOT NULL
        )
        """)

        # Insert example data

        hgvs_dict, transcript, np_change = HGVS_converter(vcf[1])

        for key, value in hgvs_dict.items():

            cursor.execute("INSERT INTO patient_variant (patient_ID, variant) VALUES (?, ?)", (vcf[0], key))

        # Save (commit) changes and close connection
        conn.commit()
        conn.close()

    print("patient_variant table created/updated successfully!")
