import os
import sqlite3
from ...utils.parseVCF import parseVCF
from ...modules.HGVS_convertion import HGVS_converter
from ...modules.detailed_request import get_clinvar_full_info
from ...modules.Entrez import Entrez_fetch_transcript_record

def variantAnnotationsTable(filepath):
    '''
    This function creates the sea.db database, if it doesn't already exist.
    It then creates or updates a table in the database that is populated by variants extracted from .vcf files uploaded
    by the user on our flask website.

    :params: filepath: This leads to the subdirectory where the .vcf files uploaded by the user are stored.
                       The subdirectory is called 'data' and is located in the base-directory of this software package.
                       The filepath is not hardcoded into the script because it is the absolute filepath within the
                       respective computer that this software package was loaded in.

                 E.g.: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/'

    :output: sea.db database: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/sea.db'

             variant_annotations table:
             No|HGVS NC_ nomenclature|HGVS NM_ nomenclature|HGVS NP_ nomenclature|Gene symbol|HGNC ID|Classification|Conditions|Star-Rating|Review status

             E.g.:

             1|NC_000017.11:g.45990019G>A|NM_007262.5:c.541G>C|NP_009193.2:p.(Val181Leu)|MAPT|6893|Pathogenic|Unknown|★★|criteria provided, multiple submitters, no conflicts
             2|NC_000012.12:g.40295535A>T|NM_007262.5:c.541G>C|NP_009193.2:p.(Val181Leu)|LRRK2|18618|Pathogenic|Unknown|★★|criteria provided, multiple submitters, no conflicts
             3|NC_000012.12:g.40346849C>G|NM_007262.5:c.541G>C|NP_009193.2:p.(Val181Leu)|LRRK2|18618|Pathogenic|Unknown|★★|criteria provided, multiple submitters, no conflicts
             4|NC_000004.12:g.89835580C>G|NM_007262.5:c.541G>C|NP_009193.2:p.(Val181Leu)|SNCA|11138|Pathogenic|Unknown|★★|criteria provided, multiple submitters, no conflicts
             5|NC_000019.10:g.41985036A>C|NM_007262.5:c.541G>C|NP_009193.2:p.(Val181Leu)|ATP1A3|801|Pathogenic|Unknown|★★|criteria provided, multiple submitters, no conflicts

    :command: filepath = '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/'
              variantAnnotationsTable(filepath)

              To access database: sqlite3 /<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/sea.db

              To view table: SELECT * FROM variant_annotations;
    '''

    # create a list of the filepath to all of the .vcf files in the data subdirectory
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

            cursor.execute("""
                           INSERT INTO variant_annotations 
                           (variant_NC, variant_NM, variant_NP, gene, HGNC_ID, classification, conditions, stars, review_status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(variant_NC, variant_NM, variant_NP)
                           DO UPDATE SET
                               gene = excluded.gene,
                               HGNC_ID = excluded.HGNC_ID,
                               classification = excluded.classification,
                               conditions = excluded.conditions,
                               stars = excluded.stars,
                               review_status = excluded.review_status
                           """, (key, transcript, np_change, gene, HGNC_ID, classification, conditions, stars, review_status))

        # Save (commit) changes and close connection
        conn.commit()
        conn.close()

    print("variant_annotations created/updated successfully!")
