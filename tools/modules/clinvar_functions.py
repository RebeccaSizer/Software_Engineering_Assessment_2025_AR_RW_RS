import os
import re
import csv
import gzip
import sqlite3
import requests
from ..utils.timer import timer
from tools.utils.logger import logger

@timer
def clinvar_vs_download():
    '''
    This function retrieves the most recent ClinVar variant summary records from NCBI and loads them into a database.
    The records are parsed into the clinvar.db database because it is much quicker to query and annotate variants than
    querying a zip file.

    :outputs: clinvar_db_summary.txt.gz: A compressed .txt file which contains the variant summaries from ClinVar.

              clinvar.db: a sqlite database containing the variant summaries from ClinVar.

              Last-Modified: When the ClinVar variant summaries database was last updated.
                       E.g.: "ClinVar database last modified: Sun, 16 Nov 2025 22:54:32 GMT

    :command: clinvar_vs_download()
    '''


    # The url to the database where the variant summary records are downloaded from.
    url =  'https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz'

    # Test if the url is OK to request a response from.
    try:
        # Log the start of the test.
        logger.info(f'Downloading ClinVar summary records from {url}')

        # Stream the download so we don't load the entire file into memory at once.
        clinvar_db = requests.get(url, stream=True)

        # Raise an error if download failed.
        clinvar_db.raise_for_status()

        # Log that the download was successful and when the records were last modified.
        logger.info(f"Request OK. ClinVar variant summary records last modified: {requests.head(url).headers['Last-Modified']}")

    # Raise an exception if the url test failed.
    except Exception as e:
        # Log the error, describing the reason why the test failed, using the exception output message.
        logger.error(f'ClinVar variant summary record download failed:{str(e)}', exc_info=True)

    # Test if the clinvar subdirectory can be made in the app folder.
    try:
        # Retrieve the path to this script and create a relative path to where the variant summary records will be stored.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        clinvar_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "app", "clinvar"))

        #Log the start of the test.
        logger.info(f'Creating a clinvar directory to store the variant summary records...')

        # Make a clinvar subdirectory in the app folder located in the base directory if it doesn't already exist.
        os.makedirs(clinvar_dir, exist_ok=True)

        # Designate where the ClinVar variant summary records and clinvar.db should be.
        clinvar_file_path = os.path.abspath(os.path.join(clinvar_dir, "clinvar_db_summary.txt.gz"))
        clinvar_records = os.path.abspath(os.path.join(clinvar_dir, "clinvar.db"))

        # Log that the clinvar directory was built.
        logger.info(f'Successfully created clinvar directory to store the variant summary records: {clinvar_dir}')

    # Raise an exception if the clinvar directory could not be built.
    except Exception as e:
        # Log the error, describing the reason why the test failed, using the exception output.
        logger.error(f'Failed to create a directory to store the variant summary records: {str(e)}', exc_info=True)

    # Test if the variant summary records could be downloaded into a zip file.
    try:
        # Log the start of the test including the name of the zip file.
        logger.info('Downloading variant summary records into clinvar/clinvar_db_summary.txt.gz...')

        # Write the records into the zip file, using its absolute file path.
        # Consider changing chunk_size to chunk_size=8192 if bandwidth is low.
        # Consider changing chunk_size to chunk_size=65536 if bandwidth is medium.
        # Consider changing chunk_size to chunk_size=1024*1024 if bandwidth is high.
        # Or let the requests module decide by using: clinvar_db.iter_content(chunk_size=None).
        # Code from lines 81 to 84 from ChatGPT.
        with open(clinvar_file_path, "wb") as f:
            for chunk in clinvar_db.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        # Log that the records were successfully downloaded.
        logger.info('ClinVar variant summary records downloaded successfully!')

    # Raise an exception if the variant summary records could not be downloaded into the zip file.
    except Exception as e:
        # Log the error, describing why the records could not be downloaded, using the exception output.
        logger.error(f'Failed to download the ClinVar variant summary records: {str(e)}', exc_info=True)

    # The records are parsed into the clinvar.db database because it is much quicker to query and annotate variants
    # than querying a zip file.
    # Test if the variant summary records whose names start with 'NM_' can be parsed into a database.
    try:
        # Log the start of the test.
        logger.info('Loading ClinVar variant summary records into clinvar.db database...')

        # Create the clinvar.db database and the clinvar table in that database.
        conn = sqlite3.connect(clinvar_records)
        cur = conn.cursor()

        cur.execute("""
                CREATE TABLE IF NOT EXISTS clinvar (
                    nc_accession TEXT,
                    nm_hgvs TEXT,
                    clinical_significance TEXT,
                    conditions TEXT,
                    stars TEXT,
                    review_status TEXT             
                );
            """)

        # Wipe the database clean so that it can be populated by the most recent variant summary records.
        cur.execute("DELETE FROM clinvar;")

        # Log that a new database was built successfully.
        logger.info('Created new clinvar.db database.')

        # Create a list to store all of the variant information that the user wants from each variant summary record.
        # A list was chosen instead of a dictionary because it is easier to add the values from a list under the
        # headers in the clinvar table, in the clinvar.db database.
        variant_info = []

        # A counter to show how many records have been loaded into the database. This is to help users understand how
        # likely it might be to annotate a variant.
        # i.e. a 'high' number indicates a higher likelihood, whereas a 'low' number indicates a low likelihood.
        record_counter = 0

        # Each record in the zip file can be queried like its a dictionary. From each record in the zip file:
        #   - Get the NC_ accession number from 'ChromosomeAccession'. This is to help find the record using the
        #     variant validator output.
        #   - Take the record's name and convert it into NM_ HGVS nomenclature. This is to help find the record using the
        #     variant validator output.
        #   - Get the variant's classification from 'ClinicalSignificance' because the user wants this.
        #   - Get the conditions associated with the variant from 'PhenotypeList' because the user wants this.
        #   - Get the variant star-rating from 'ReviewStatus' because the user wants this.
        #   - Get the review status from 'ReviewStatus' so that the user is aware of how valid the star-rating is.
        with gzip.open(clinvar_file_path, "rt") as gz:
            reader = csv.DictReader(gz, delimiter="\t")

            # Log that the records with 'NM_' accession numbers in their name will now be added to the database.
            logger.info("Parsing variant summary records named after 'NM_' accession numbers from the most recent download into database...")

            for record in reader:

                # Some records include the gene symbol and the consequence on the protein.
                # E.g. NM_000360.4(TH):c.1442G>A (Gly481Asp)
                # The following code removes the gene symbol and protein consequence from the nomenclature if a '('
                # exists in the name, so that the database is more easily queryable using the NM_ HGVS nomenclature
                # (from the variant validator output). Not all records are named after the RefSeq NM_ accession number
                # so this specifies the ones that are.
                if record['Name'].startswith('NM'):

                    if '(' in record['Name']:
                        record_nm_hgvs = f'{record['Name'].split('(')[0]}{record['Name'].split(')')[1].split(' ')[0]}'

                    else:
                        record_nm_hgvs = record['Name']

                    # Some of the conditions submitted in the variant summary record are described as 'not provided' or
                    # 'not specified', even if conditions are provided by other submitters. This removes 'not provided'
                    # and 'not specified' from the conditions stored in the database.
                    record_condition = (
                        record['PhenotypeList']
                        .replace('not provided| ', '')
                        .replace('not specified| ', '')
                        .replace('not provided|', '')
                        .replace('not specified|', '')
                        .replace('not provided', '')
                        .replace('not specified', '')
                        .replace('|', '; ')
                    )

                    # Return 'None provided' if no disorders/conditions were provided in the variant summary record
                    # so that there are no empty fields in the database. This will help the user to filter in/out any
                    # variants which are not associated with a specific condition.
                    if record_condition == '':
                        record_condition = 'None provided'

                    # Ascertain the ClinVar star-rating from the key phrases used in the record's review status, as
                    # described in ClinVar's documentation (https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/).
                    if 'practice guideline' in record['ReviewStatus']:
                        stars = '★★★★'
                    elif 'reviewed by expert panel' in record['ReviewStatus']:
                        stars = '★★★'
                    elif 'multiple submitters' in record['ReviewStatus']:
                        stars = '★★'
                    elif 'single submitter' in record['ReviewStatus']:
                        stars = '★'
                    else:
                        stars = '0★'

                    # Consolidate the information that the user wants from the variant summary record into a list.
                    variant_info.append((record['ChromosomeAccession'],
                                    record_nm_hgvs,
                                    record['ClinicalSignificance'],
                                    record_condition,
                                    stars,
                                    record['ReviewStatus']
                    ))

                    record_counter += 1

                # Ignore the record if its name does not start with NM_.
                else:
                    continue

        # Populate the database with the information from the variant_info list.
        cur.executemany("""
                INSERT INTO clinvar VALUES (?, ?, ?, ?, ?, ?)
            """, variant_info)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_clinvar ON clinvar (nc_accession, nm_hgvs);")
        conn.commit()
        conn.close()

        # Log the number of variant summary records that the database was successfully populated by.
        logger.info(f'clivar.db successfully populated by {record_counter} variant summary records.')

    # Raise an exception if the database could not be successfully populated with variant summary records.
    except Exception as e:
        # Log the error, describing why the database could not be successfully populated, using the exception output.
        logger.error(f'Failed to write ClinVar variant summary records into clinvar.db database.')


@timer
def clinvar_annotations(nc_variant, nm_variant):
    '''
    This function retrieves variant information from the compressed the clinvar.db database. It takes a variant
    in NC_ and NM_ HGVS nomenclature as input and uses them to find the corresponding variant summary record in the
    database. It then returns a dictionary containing the variant classification, associated conditions, star-rating
    and Review status from that record.

    :params: nc_variant: The variant described in HGVS nomenclature, using the RefSeq NC_ accession number
                   E.g.: 'NC_000011.10:g.2164285C>T'

             nm_variant: The variant described in HGVS nomenclature, using the RefSeq NM_ accession number
                   E.g.: 'NM_000360.4:c.1442G>A'

    :output: clinvar_output: A python dictionary containing the variant classification, associated conditions,
                             star-rating and Review status from that record.

                       E.g.: {
                                'classification': 'Conflicting classifications of pathogenicity',
                                'conditions': 'Autosomal recessive DOPA responsive dystonia|Inborn genetic diseases',
                                'stars': '0★',
                                'reviewstatus': 'criteria provided, conflicting classifications'
                             }

    :command: clinvarAnnotations('NC_000011.10:g.2164285C>T', 'NM_000360.4:c.1442G>A')
    '''

    # Ensure that the input genomic variant is in the appropriate HGVS nomenclature.
    if not re.match('^NC_\d+.\d{1,2}:g[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]>[ACGT]|delins[ACGT]*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', nc_variant):
        logger.error(f'{nc_variant} is not in valid HGVS nomenclature.')
        return f'{nc_variant} is not in valid HGVS nomenclature.'

    # Ensure that the input transcript variant is in the appropriate HGVS nomenclature.
    elif not re.match('^NM_\d+.\d{1,2}:c[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]>[ACGT]|delins[ACGT]*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', nm_variant):
        logger.error(f'{nm_variant} is not in valid HGVS nomenclature.')
        return f'{nm_variant} is not in valid HGVS nomenclature.'

    # Isolate the NC_ accession number from the NC_ HGVS nomenclature to find the corresponding variant summary record.
    else:
        vv_nc_accession = nc_variant.split(":")[0]

    # Creates a python dictionary to store the variant information from ClinVar.
    clinvar_output = {}

    # Test the path to clinvar.db (recommended by ChatGPT).
    try:
        # Retrieve the path to this script and create a relative path to clinvar.db.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        clinvar_db = os.path.abspath(os.path.join(script_dir, "..", "..", "app", "clinvar", "clinvar.db"))

        # Log where the clinvar.db is (recommended by ChatGPT).
        logger.debug(f"Using clinvar.db SQLite database at: {clinvar_db}")

    # Raise an exception if a path to clinvar.db cannot be made (recommended by ChatGPT).
    except Exception as e:
        #Log the error using the exception output message.
        logger.error(f'clinvar.db path error: {str(e)}', exc_info=True)
        return (f"clinvar.db file path error whilst searching for {nc_variant}.\n"
                f"Please delete clinvar folder in {os.path.abspath(os.path.join(script_dir, '..', '..', 'app'))}"
                f"and run 'python main.py' again."
        )

    # Test if a variant summary record can be retrieved from clinvar.db.
    try:
        # Log which variant is being searched for in clinvar.db.
        logger.info(f'Searching for {nc_variant}/{nm_variant} in clinvar.db...')

        # Connect to clinvar.db.
        conn = sqlite3.connect(clinvar_db)
        cursor = conn.cursor()

        # Retrieve the required variant information from the record where the inputs to this function match the
        # NC_ accession number and NM_ HGVS nomenclature in the record.
        cursor.execute("""
                       SELECT clinical_significance, conditions, stars, review_status
                       FROM clinvar
                       WHERE nc_accession = ?
                         AND nm_hgvs LIKE ? 
                         LIMIT 1
                       """, (vv_nc_accession, nm_variant + '%'))

        # Assign the variant information the variable 'record'
        record = cursor.fetchone()
        conn.close()

    # Raise an exception if clinvar.db could not be queried.
    except Exception as e:
        # Log the error using the exception output message.
        logger.error(f'Failed to query clinvar.db: {str(e)}', exc_info=True)
        return (f"Failed to query clinvar.db whilst searching for {nc_variant}.\n"
                f"Please delete clinvar folder in {os.path.abspath(os.path.join(script_dir, '..', '..', 'app'))}"
                f"and run 'python main.py' again."
        )

    # Log which variant's summary record could not be found in clinvar.db.
    if not record:
        logger.warning(f'Could not find {nc_variant} variant summary record in clinvar.db')
        return f'Could not find {nc_variant} variant summary record in clinvar.db'

    else:
        # Log which variant's summary record could be found in clinvar.db.
        logger.info(f'{nc_variant} variant summary record found in clinvar.db')

        # Parse the variant information out of the record.
        clinical_significance, conditions, stars, review_status = record

        # Compiles clinvar_out dictionary with variant information.
        clinvar_output['classification'] = clinical_significance
        clinvar_output['conditions'] = conditions
        clinvar_output['stars'] = stars
        clinvar_output['reviewstatus'] = review_status

        # Returns the clinvar_output dictionary, even if length is 0.
        return clinvar_output
'''
# Example
if __name__ == "__main__":
    result = get_clinvar_full_info(('NC_000017.11:g.45983420G>T', 'NM_001377265.1:c.841G>T', 'NP_001364194.1:p.(Ala281Ser)', 'MAPT', '6893'))
    print(result)
'''

#print(clinvar_annotations('NC_000011.10:g.2164285C>T', 'NM_000360.4:c.1442G>A'))