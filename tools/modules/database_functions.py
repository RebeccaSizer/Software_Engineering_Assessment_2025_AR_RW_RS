import os
import time
import sqlite3
from ..utils.parser import variantParser
from .HGVS_fetcher import fetch_vv
from .clinvar_functions import clinvar_annotations

def patient_variant_table(filepath, db_name):
    '''
    This function creates a database, if it doesn't already exist.
    It creates or updates a table in the database called 'patient_variant', which is populated by patients and their
    respective variants. The patients' IDs are taken from the name of the .vcf files uploaded by the user on our flask
    website, while the variants are extracted from each patient's .vcf file.

    :params: filepath: This leads to the subdirectory where the .vcf files uploaded by the user are stored.
                       The subdirectory is called 'data' and is located in the base-directory of this software package.
                       The filepath is not hardcoded into the script because it is the absolute filepath within the
                       respective computer that this software package was loaded in.

                 E.g.: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/'

              db_name: The user-specified name of the database.

                 E.g.: 'my_database'

    :output: my_database.db database: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db'

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

              To access database: sqlite3 /<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db

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

        # Create (or connect to) the database file.
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Build absolute path to the database
        db_path = os.path.abspath(
            os.path.join(script_dir, '..', '..', 'databases', f'{db_name}.db'))

        # Ensure the folder exists (optional)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Connect to the database
        conn = sqlite3.connect(db_path)

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

            variant_info = fetch_vv(variant)

            # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not overloaded with requests.
            time.sleep(0.5)

            if not variant_info or variant_info in ('null', 'empty_result'):
                continue

            else:

                # The patient ID and corresponding variant are added to the patient_variant table.
                cursor.execute("INSERT OR IGNORE INTO patient_variant (patient_ID, variant) VALUES (?, ?)", (patient_name, variant_info[0]))

        # Save (commit) changes and close connection
        conn.commit()
        conn.close()

    # A message is printed in the back-end to indicate that the table was successfully created or updated.
    print("patient_variant table created/updated successfully!")



def variant_annotations_table(filepath, db_name):
    '''
    This function creates a database, if it doesn't already exist.
    It then creates or updates a table in the database called 'variant_annotations', which is populated by variants
    extracted from .vcf files uploaded by the user on our flask website.

    :params: filepath: This leads to the subdirectory where the .vcf files uploaded by the user are stored.
                       The subdirectory is called 'data' and is located in the base-directory of this software package.
                       The filepath is not hardcoded into the script because it is the absolute filepath within the
                       respective computer that this software package was loaded in.

                 E.g.: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/'

              db_name: The user-specified name of the database.

                 E.g.: 'my_database'

    :output: my_database.db database: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db'

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

              To access database: sqlite3 /<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db

              To view table: SELECT * FROM variant_annotations;
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
        script_dir = os.path.dirname(os.path.abspath(__file__)) #RS

        # Absolute path to database
        db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'databases', f'{db_name}.db')) #RS
        # Create (or connect to) the database file.
        conn = sqlite3.connect(db_path)

        # Create a cursor to run SQL commands.
        cursor = conn.cursor()

        # Create the variant_annotations table if it does not already exist.
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS variant_annotations (
                                                                          No INTEGER PRIMARY KEY,
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

        # VariantValidator is queried through fetchVV to retrieve the NC_, NM_ and NP_ accession numbers of each
        # variant in the variant_list, in HGVS nomenclature.
        for variant in variant_list:

            variant_info = fetch_vv(variant)
            # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not overloaded with requests.
            time.sleep(0.5)

            if not variant_info or variant_info in ('null', 'empty_result') or len(variant_info) != 5:
                continue

            try:
                nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id = variant_info

            except ValueError:
                continue

            # CliVar is queried to retrieve the variant classification, associated conditions, the star-ratings
            # and the review statuses.
            clinVar_response = clinvar_annotations(nc_variant, nm_variant)

            if not clinVar_response or len(clinVar_response) == 0:
                continue

            elif len(clinVar_response) > 0:

                classification = clinVar_response['classification']
                conditions = clinVar_response['conditions']
                stars = clinVar_response['stars']
                review_status = clinVar_response['reviewstatus']

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
                               """, (nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id, classification, conditions, stars, review_status))

            else:
                continue

        # Save (commit) changes and close connection
        conn.commit()
        conn.close()

    # A message is printed in the back-end to indicate that the table was successfully created or updated.
    print("variant_annotations created/updated successfully!")


def validate_database(db_path):

    EXPECTED_SCHEMA = {
        "patient_variant": {"No", "patient_ID", "variant"},
        "variant_annotations": {
            "No",
            "variant_NC",
            "variant_NM",
            "variant_NP",
            "gene",
            "HGNC_ID",
            "Classification",
            "Conditions",
            "Stars",
            "Review_status",
        },
    }

    """Check whether the uploaded database matches expected tables and columns."""
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cur.fetchall()}

            if not EXPECTED_SCHEMA.keys() <= tables:
                return False

            for table, expected_cols in EXPECTED_SCHEMA.items():
                cur.execute(f"PRAGMA table_info({table});")
                cols = {row[1] for row in cur.fetchall()}
                if not expected_cols <= cols:
                    return False
        return True
    except Exception:
        return False


def query_db(db_path, query, args=(), one=False):
    """Execute SQL query on a database and return results as sqlite3.Row objects."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv