import os
import sqlite3
from ...utils.parser import variantParser
from ...modules.HGVS_fetcher import fetchVV

def patientVariantTable(filepath):
    '''
    This function creates the sea.db database, if it doesn't already exist.
    It then creates or updates a table in the database called 'patient_variant', which is populated by patients
    and their respective variants. The patients' IDs are taken from the name of the .vcf files uploaded by the user
    on our flask website, while the variants are extracted from each patient's .vcf file.

    :params: filepath: This leads to the subdirectory where the .vcf files uploaded by the user are stored.
                       The subdirectory is called 'data' and is located in the base-directory of this software package.
                       The filepath is not hardcoded into the script because it is the absolute filepath within the
                       respective computer that this software package was loaded in.

                 E.g.: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/'

    :output: sea.db database: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/sea.db'

             patient_variant table:
             No.|patient_ID|HGVS NC_ nomenclature

             E.g.:

             1|Patient2|NC_000017.11:g.45990019G>A
             2|Patient2|NC_000012.12:g.40295535A>T
             3|Patient2|NC_000012.12:g.40346849C>G
             4|Patient2|NC_000017.11:g.44350271C>A
             5|Patient2|NC_000004.12:g.89835580C>G

    :command: filepath = '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/'
              patientVariantTable(filepath)

              To access database: sqlite3 /<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/sea.db

              To view table: SELECT * FROM patientVariantTable;
    '''

    # Create a list of the filepaths to all of the .vcf files in the 'data' subdirectory.
    vcf_paths = []

    # Iterate through the files in the filepath provided by the user and add the files with a .vcf or .csv extension to the vcf_paths list.
    for file in os.listdir(filepath):
        if file.endswith('.vcf') or file.endswith('.csv'):
            vcf_paths.append(f'{filepath}/{file}')
        else:
            continue

    # Iterate through the absolute filepaths to the .vcf files.
    for path in vcf_paths:

        # Apply the variantParser function to extract the variants listed in the files.
        variant_list = variantParser(path)

        # Create (or connect to) the sea.db database file.
        conn = sqlite3.connect('database/sea.db')

        # Create a cursor to run SQL commands
        cursor = conn.cursor()

        # Create the patient_variant table if it does not already exist.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_variant (
            No INTEGER PRIMARY KEY,
            patient_ID TEXT NOT NULL,
            variant TEXT NOT NULL,

            /* 
             The patient ID and respective variant are collectively treated as unique. 
             If either of them are different while the other exits in the table, a new entry will be made in the table.
             */
            UNIQUE(patient_ID, variant)
        )
        """)

        # Data is then assigned to each header:

        # The patient's ID appears in the filepath, after the final directory, which ends in a '/', and before the
        # .vcf file extension.
        patient_name = path.split('/')[-1].split('.')[0]

        # VariantValidator is queried through fetchVV to retrieve the NC_ accession number of each
        # variant in the variant_list, in HGVS nomenclature.
        for variant in variant_list:

            nc_variant = fetchVV(variant)[0]

            if nc_variant == 'empty_result':
                continue

            elif nc_variant == 'null':
                continue

            else:

                # The patient ID and corresponding variant are added to the patient_variant table.
                cursor.execute("INSERT OR IGNORE INTO patient_variant (patient_ID, variant) VALUES (?, ?)", (patient_name, nc_variant))

        # Save (commit) changes and close connection
        conn.commit()
        conn.close()

    # A message is printed in the back-end to indicate that the table was successfully created or updated.
    print("patient_variant table created/updated successfully!")
