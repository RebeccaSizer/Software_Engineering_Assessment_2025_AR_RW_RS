import os
import sqlite3
from ...utils.parseVCF import parseVCF
from ...modules.HGVS_convertion import HGVS_converter

'''
vcf_filepath = '/home/ubuntu/Desktop/ParkVCF/'

vcf_paths = []

for file in os.listdir(vcf_filepath):
    if file.endswith('.vcf'):
        vcf_paths.append(f'{vcf_filepath}/{file}')
    else:
        continue
'''

for path in vcf_paths:

    vcf = parseVCF(path)

    # Create (or connect to) a database file
    conn = sqlite3.connect('/home/ubuntu/Desktop/Software_Engineering_Assessment_2025_AR_RW_RS/database/sea.db')

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
    for key, value in HGVS_converter(vcf[1]).items():

        cursor.execute("INSERT INTO patient_variant (patient_ID, variant) VALUES (?, ?)", (vcf[0], key))

    # Save (commit) changes and close connection
    conn.commit()
    conn.close()

print("patient_variant table created/updated successfully!")
