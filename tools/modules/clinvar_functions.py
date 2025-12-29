import os
import re
import csv
import gzip
import errno
import sqlite3
import requests
from ..utils.timer import timer
from tools.utils.logger import logger
from tools.utils.error_handlers import request_status_codes, connection_error, sqlite_error

@timer
def clinvar_vs_download():
    '''
    This function retrieves the most recent ClinVar variant summary records from NCBI and loads them into a database.
    The records are parsed into the clinvar.db database because it is much quicker to query and annotate variants than
    querying the downloaded zip file.

    :outputs: clinvar.db: a sqlite database containing the variant summaries from ClinVar.

              Last-Modified: When the ClinVar variant summaries database was last updated.
                       E.g.: "ClinVar database last modified: Sun, 16 Nov 2025 22:54:32 GMT

    :command: clinvar_vs_download()
    '''

    # The url to the database where the variant summary records are downloaded from.
    url =  'https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz'

    # For loop enables 5 attempts to query ClinVar API, in case 408 or 429 request errors occur.
    for attempt in range(5):
        # Test if the url is OK to request a response from.
        try:
            # Log the start of the test.
            logger.info(f'Downloading ClinVar summary records from {url}')

            # Stream the download so we don't load the entire file into memory at once.
            clinvar_db = requests.get(url, stream=True)

            # Raise an error if download failed.
            clinvar_db.raise_for_status()

            # Log that the download was successful and when the records were last modified.
            last_modified = requests.head(url).headers['Last-Modified']
            logger.info(f"Request OK. ClinVar variant summary records last modified: "
                        f"{last_modified}")

            # Break out fo the loop if the request to downloaded ClinVar summary records was successful
            break

        # Catch any network or HTTP errors raised by 'requests'.
        except requests.exceptions.HTTPError as e:

            # Handle HTTP errors that need to be tried again.
            if e.response.status_code in [408, 429]:
                error_message = request_status_codes(e, 'ClinVar_Download', url, 'ClinVar', attempt)

                # Once the error message has been received, return.
                if error_message:
                    return
                # Move to the next attempt to see if the 408 or 429 error response can be avoided.
                continue

            # Handle HTTP errors that do not need to be tried again.
            else:
                request_status_codes(e, 'ClinVar_Download', url, 'ClinVar', attempt)
            return

        # Raise an exception if there is a problem with the connection to the remote server.
        except requests.exceptions.ConnectionError as e:
            connection_error(e, 'ClinVar_Download', 'ClinVar', url)
            return

        # Raise an exception if any other errors occurred.
        except Exception as e:
            # Log the error using the exception output message.
            logger.error(f'ClinVar_Download: Failed to download variant summary records from {url}. {e}')
            return

    # Test if the clinvar subdirectory can be made in the app folder.
    try:
        # Retrieve the path to this script and create a relative path to where the variant summary records will be
        # stored.
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

    # Raise an exception if the User lacks permission to create clinvar directory.
    except PermissionError as e:
        # Log the error, explaining the User's lack of permission, using the exception output.
        logger.error(f'Failed to create clinvar directory to store the variant summary records because the User lacks '
                     f'permissions: {str(e)}')
        return

    # Raise an exception if there is an error with the system, preventing the clinvar directory from being made.
    except OSError as e:
        # from ChatGPT.
        if e.errno == errno.ENOSPC:
            # Log the error, explaining there isn't enough disk space, using the exception output.
            logger.error(f'Failed to create clinvar directory because there is not enough disk space to store the '
                         f'variant summary records: {str(e)}')

        else:
            # Log that there was an error with the operating system, using the exception output.
            logger.error(f'Failed to create clinvar directory to store the variant summary records because there is '
                         f'an issue with the operating system: {str(e)}')
        return

    # Raise an exception if the clinvar directory could not be built.
    except Exception as e:
        # Log the error, describing the reason why the test failed, using the exception output.
        logger.error(f'Failed to create clinvar directory to store the variant summary records: {str(e)}')
        return

    # Test if the variant summary records could be downloaded into a zip file.
    try:
        # Log the start of the test including the name of the zip file.
        logger.info('Downloading variant summary records into clinvar/clinvar_db_summary.txt.gz...')

        # Write the records into the zip file, using its absolute file path.
        # Consider changing chunk_size to chunk_size=8192 if bandwidth is low.
        # Consider changing chunk_size to chunk_size=65536 if bandwidth is medium.
        # Consider changing chunk_size to chunk_size=1024*1024 if bandwidth is high.
        # Or let the requests module decide by using: clinvar_db.iter_content(chunk_size=None).
        # (from ChatGPT).
        with open(clinvar_file_path, "wb") as f:
            for chunk in clinvar_db.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        # Log that the records were successfully downloaded.
        logger.info('ClinVar variant summary records downloaded successfully!')

    # Raise an exception if the User lacks permission to create and/or write to the clinvar_db_summary.txt.gz file.
    except PermissionError as e:
        # Log the error, explaining the User's lack of permission, using the exception output.
        logger.error(f'Failed to write ClinVar variant summary records to clinvar_db_summary.txt.gz because the User '
                     f'lacks permissions: {str(e)}')
        return

    # Raise an exception if there is an error with the system, preventing clinvar_db_summary.txt.gz from being made or
    # written to.
    except OSError as e:
        # from ChatGPT.
        if e.errno == errno.ENOSPC:
            # Log the error, explaining there isn't enough disk space, using the exception output.
            logger.error(f'Failed to create clinvar_db_summary.txt.gz because there is not enough disk space: {str(e)}')

        else:
            # Log that there was an error with the operating system, using the exception output.
            logger.error(f'Failed to create clinvar_db_summary.txt.gz because there is an issue with the '
                         f'operating system: {str(e)}')
        return

    # Raise an exception if the variant summary records could not be downloaded into the zip file.
    except Exception as e:
        # Log the error, describing why the records could not be downloaded, using the exception output.
        logger.error(f'Failed to write the ClinVar variant summary records to clinvar_db_summary.txt.gz: {str(e)}')
        return

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

        # Wipe the clinvar table clean so that it can be populated by the most recent variant summary records.
        cur.execute("DELETE FROM clinvar;")

        # Create the 'download' table with the header 'last_updated'.
        # This will store when the variant summary database from ClinVar was last updated.
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS download (
                        last_updated TEXT
                    );
                    """)

        # Wipe the download table clean so that it can be populated by the most recent variant summary records.
        cur.execute("DELETE FROM download;")

        # Log that a new database was built successfully.
        logger.info('Created new clinvar.db database.')

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately.
        sqlite_error(e, 'clinvar.db')
        return

    # Raise an exception if the there was an issue creating clinvar.db.
    except Exception as e:
        # Log the error, describing why clinvar.db could not be made, using the exception output.
        logger.error(f'Failed to create clinvar.db: {str(e)}')
        return

    # Create a list to store all of the variant information that the user wants from each variant summary record.
    # A list was chosen instead of a dictionary because it is easier to add the values from a list under the
    # headers in the clinvar table, in the clinvar.db database.
    variant_info = []

    # A counter to show how many records have been loaded into the database. This is to help users understand how
    # likely it might be to annotate a variant.
    # i.e. a 'high' number indicates a higher likelihood, whereas a 'low' number indicates a low likelihood.
    record_counter = 0

    # Test the zip file to ensure that it has integrity and records that can be written into clinvar.db.
    try:
        # Each record in the zip file can be queried like its a dictionary. From each record in the zip file:
        #   - Get the NC_ accession number from 'ChromosomeAccession'. This is to help find the record using the
        #     variant validator output.
        #   - Take the record's name and convert it into NM_ HGVS nomenclature. This is to help find the record using
        #     the variant validator output.
        #   - Get the variant's classification from 'ClinicalSignificance' because the user wants this.
        #   - Get the conditions associated with the variant from 'PhenotypeList' because the user wants this.
        #   - Get the variant star-rating from 'ReviewStatus' because the user wants this.
        #   - Get the review status from 'ReviewStatus' so that the user is aware of how valid the star-rating is.
        with gzip.open(clinvar_file_path, "rt") as gz:
            reader = csv.DictReader(gz, delimiter="\t")

            # Log that the records with 'NM_' accession numbers in their name will now be added to the database.
            logger.info("Parsing variant summary records named after 'NM_' accession numbers from the most recent "
                        "download into clinvar.db...")

            for record in reader:

                # Some records include the gene symbol and the consequence on the protein.
                # E.g. NM_000360.4(TH):c.1442G>A (Gly481Asp)
                # The following code removes the gene symbol and protein consequence from the nomenclature if a '('
                # exists in the name, so that the database is more easily queryable using the NM_ HGVS nomenclature
                # (from the variant validator output). Not all records are named after the RefSeq NM_ accession number
                # so this specifies the ones that are.
                if record['Name'].startswith('NM'):

                    if '(' in record['Name']:
                        record_nm_hgvs = f"{record['Name'].split('(')[0]}{record['Name'].split(')')[1].split(' ')[0]}"

                    else:
                        record_nm_hgvs = record['Name']

                    # Some of the conditions in a variant's summary record contain 'not provided' or 'not specified'
                    # even if conditions are provided by other submitters. This removes 'not provided' and
                    # 'not specified' from the conditions stored in the database and converts the | character into a
                    # semicolon.
                    raw_conditions = (
                        record['PhenotypeList']
                        .replace('not provided', '')
                        .replace('not specified', '')
                        .replace('|', ';')
                    )

                    # Conditions are separated into separate values and added to a list, after any white space has been
                    # removed before and after.
                    conditions_list = []
                    for condition in raw_conditions.split(';'):
                        if condition.strip() != '':
                            conditions_list.append(condition.strip())

                    # Assign 'None provided' to the 'record_conditions' variable if no disorders/conditions were
                    # provided in the variant summary record so that there are no empty fields in the database. This
                    # will help the user to filter in/out any variants which are not associated with a specific
                    # condition.
                    if not conditions_list:
                        record_conditions = 'None provided'
                    # Otherwise join the conditions in the list back together in a string, separated by a semicolon and
                    # space.
                    else:
                        # Sort the condition into alphabetical order before putting them back into a string.
                        conditions_list.sort()
                        record_conditions = '; '.join(conditions_list)

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
                                    record_conditions,
                                    stars,
                                    record['ReviewStatus']
                    ))

                    record_counter += 1

                # Ignore the record if its name does not start with NM_.
                else:
                    continue

    # Raise an exception if clinvar_db_summary.txt.gz is corrupted.
    except gzip.BadGzipFile as e:
        # Log an error if clinvar_db_summary.txt.gz is corrupted.
        logger.error(f'clinvar_db_summary.txt.gz is corrupted: {e}')
        return

    # Raise an exception if the compressed .csv cannot be converted into a dictionary.
    except csv.Error as e:
        # Log an error if the .csv file is malformed.
        logger.error(f'The .CSV file compressed in clinvar_db_summary.txt.gz is malformed: {e}')
        return

    try:
        # Populate the database with the information from the variant_info list.
        cur.executemany("""
                INSERT INTO clinvar VALUES (?, ?, ?, ?, ?, ?)
            """, variant_info)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_clinvar ON clinvar (nc_accession, nm_hgvs);")

        # Populate the database with the date when the ClinVar variant summary records were last updated.
        cur.execute(
            "INSERT INTO download VALUES (?)",
            (last_modified,)
        )

        # Commit the update and close the database.
        conn.commit()
        conn.close()

        # Log the number of variant summary records that the database was successfully populated by.
        logger.info(f'clivar.db successfully populated by {record_counter} variant summary records.')

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately.
        sqlite_error(e, 'clinvar.db')
        return

    # Raise an exception if the database could not be successfully populated with variant summary records.
    except Exception as e:
        # Log the error, describing why the database could not be successfully populated, using the exception output.
        logger.error(f'Failed to write ClinVar variant summary records into clinvar.db database: {e}')
        return

    # Delete the ClinVar zip file.
    os.remove(clinvar_file_path)

@timer
def clinvar_annotations(nc_variant, nm_variant):
    '''
    This function retrieves variant information from the clinvar.db database. It uses the HGVS transcript description
    and the Refseq NC_ accession number to find the corresponding variant summary record in the database. It then
    returns a dictionary containing the variant classification, associated conditions, star-rating and Review status
    from that record.

    :params: nc_variant: The HGVS genomic description, using the RefSeq NC_ accession number.
                   E.g.: 'NC_000011.10:g.2164285C>T'

             nm_variant: The HGVS transcript description, using the RefSeq NM_ accession number.
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

    # Isolate the NC_ accession number from the NC_ HGVS nomenclature to find the corresponding variant summary record.
    vv_nc_accession = nc_variant.split(":")[0]

    # Creates a python dictionary to store the variant information from ClinVar.
    clinvar_output = {}

    # Retrieve the path to this script and create a relative path to clinvar.db.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    clinvar_db = os.path.abspath(os.path.join(script_dir, "..", "..", "app", "clinvar", "clinvar.db"))

    # Log where the clinvar.db is (recommended by ChatGPT).
    logger.debug(f'Using clinvar.db SQLite database at: {clinvar_db}')

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

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately and returns an error message which can be implemented
        # into a flash message.
        error_message = sqlite_error(e, 'clinvar.db')
        return f'{nc_variant}: ❌ clinvar.db query error: {error_message}'

    # Raise an exception if the there was an issue querying clinvar.db.
    except Exception as e:
        # Log the error, describing why clinvar.db could not be queried, using the exception output.
        logger.error(f'{nc_variant}: Failed to prepare clinvar.db to be queried: {str(e)}')
        # Return a flash message to the User, notifying them of the error.
        return f'{nc_variant}: ❌ clinvar.db query error: Failed to prepare clinvar.db to be queried: {str(e)}'

    # Log which variant's summary record could not be found in clinvar.db.
    if not record:
        logger.warning(f'Could not find {nc_variant} variant summary record in clinvar.db.')
        return f'⚠ Could not find {nc_variant} variant summary record in clinvar.db'

    else:
        # Log which variant's summary record could be found in clinvar.db.
        logger.info(f'{nc_variant}: Variant summary record found in clinvar.db.')

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