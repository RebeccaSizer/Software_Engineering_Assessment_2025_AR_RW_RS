import os
import sqlite3
from ...utils.parseVCF import parseVCF
from ...modules.HGVS_convertion import HGVS_converter
from ...modules.detailed_request import get_clinvar_full_info
from ...modules.Entrez import Entrez_fetch_transcript_record

def variantAnnotationsTable(filepath):
    '''
    This function creates the sea.db database, if it doesn't already exist.
    It then creates or updates a table in the database called 'variant_annotations', which is populated by variants
    extracted from .vcf files uploaded by the user on our flask website.

    :params: filepath: This leads to the subdirectory where the .vcf files uploaded by the user are stored.
                       The subdirectory is called 'data' and is located in the base-directory of this software package.
                       The filepath is not hardcoded into the script because it is the absolute filepath within the
                       respective computer that this software package was loaded in.

                 E.g.: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/'

    :output: sea.db database: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/sea.db'

             variant_annotations table:
             No.|HGVS NC_ nomenclature|HGVS NM_ nomenclature|HGVS NP_ nomenclature|Gene symbol|HGNC ID|Classification|Conditions|Star-Rating|Review status

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

    # Create a list of the filepaths to all of the .vcf files in the 'data' subdirectory.
    vcf_paths = []

    # Iterate through the files in the filepath provided by the user and add the files with a .vcf extension to the vcf_paths list.
    for file in os.listdir(filepath):
        if file.endswith('.vcf'):
            vcf_paths.append(f'{filepath}/{file}')
        else:
            continue

    # Iterate through the absolute filepaths to the .vcf files.
    for path in vcf_paths:

        # Apply the parseVCF function to extract the mutations listed in the files.
        vcf = parseVCF(path)

        # Create (or connect to) the sea.db database file.
        conn = sqlite3.connect('database/sea.db')

        # Create a cursor to run SQL commands.
        cursor = conn.cursor()

        # Create the variant_annotations table if it does not already exist.
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
            
            /* 
             The NC_, NM_, and NP_, accession numbers are collectively treated as unique. 
             If any of them are different while the others are the same, a new entry will be made in the table.
             */
            UNIQUE(variant_NC, variant_NM, variant_NP)
        )
        """)

        # Data is then assigned to each header:

        # VariantValidator is queried through HGVS_converter to retrieve the input to ClinVar,
        # the variant in the NM_ transcript and the variant in the corresponding NP_ sequence, both in HGVS
        # nomenclature.
        hgvs_dict, transcript, np_change = HGVS_converter(vcf[1])

        # The 'value' in hgvs_dict is the input to ClinVar and Genbank.
        for key, value in hgvs_dict.items():

            # Genbank is queried via Entrez to retrieve the gene symbol and HGNC ID.
            transcript_dict = Entrez_fetch_transcript_record('A.N.Other@example.com', value)
            gene = transcript_dict['Gene_symbol']
            HGNC_ID = transcript_dict['HGNC_ID']

            # CliVar is queried to retrieve the variant classification, associated conditions, the star-ratings
            # and the review statuses.
            clinVar_response = get_clinvar_full_info(value)
            classification = clinVar_response['classification']
            conditions = clinVar_response['conditions']
            stars = clinVar_response['stars']
            review_status = clinVar_response['review_status']

            # The HGVS nomenclatures, gene symbol, HGNC ID and ClinVar annotations for each variant are added to
            # the variant_annotations table.
            cursor.execute("""
                           INSERT INTO variant_annotations 
                           (variant_NC, variant_NM, variant_NP, gene, HGNC_ID, classification, conditions, stars, review_status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                           
                           -- If a variant already exists in the table, the table is updated with the latest annotations. 
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

    # A message is printed in the back-end to indicate that the table was successfully created or updated.
    print("variant_annotations created/updated successfully!")
