import os
import time
import sqlite3
from flask import flash
from .vv_functions import fetch_vv
from tools.utils.logger import logger
from ..utils.parser import variant_parser
from .clinvar_functions import clinvar_annotations
from tools.utils.error_handlers import sqlite_error

def patient_variant_table(filepath, db_name):
    """
    This function creates a database, if it doesn't already exist.
    It creates or updates a table in the database called 'patient_variant', which is populated by patients and their
    respective variants. The patients' IDs are taken from the names of the variant files uploaded by the user on our
    flask app, while the variants are extracted from each patient's variant file and validated through VariantValidator.

    :params: filepath: This leads to the 'temp' subdirectory where the variant files uploaded by the User are stored.
                       'temp' is located in the base-directory of this software package.The filepath is not hardcoded
                       into the script because it is the absolute filepath within the respective computer that this
                       software package was loaded in.

                 E.g.: '/<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                         Software_Engineering_Assessment_2025_AR_RW_RS/temp/'

              db_name: The user-specified name of the database.

                 E.g.: 'my_database'

    :output: A database containing the patient_variant table.
             The database will be saved at: '/<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                                              Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db'

             patient_variant table: A table consisting of a unique index number, the patient ID and the HGVS genomic
                                    description of the variant parsed from the respective patient's variant file.

                              E.g.:  No | patient_ID | variant
                                    ----|------------|-----------------------------
                                      1 | Patient2   | NC_000017.11:g.45990019G>A
                                      2 | Patient2   | NC_000012.12:g.40295535A>T
                                      3 | Patient3   | NC_000012.12:g.40346849C>G
                                      4 | Patient3   | NC_000017.11:g.44350271C>A
                                      5 | Patient4   | NC_000004.12:g.89835580C>G

    :command: filepath = '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/temp/'
              patientVariantTable(filepath, 'my_database.db')

              To access database: sqlite3 /<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                                           Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db

              To view table: SELECT * FROM patientVariantTable;
    """

    # Log the start of the function.
    logger.info('Preparing patient_variant_table()...')
    # Log the absolute filepath to the 'temp' directory where the data is going to be pulled into the database from.
    # And the name of the database being updated/created by the user.
    logger.debug(f'patient_variant_table: Filepath to variant files: {filepath}; database to be populated: {db_name}')

    # Create a list of the filepaths to all the variant files in the 'temp' subdirectory.
    variant_paths = []

    # Iterate through the files in the filepath provided by the user and add the files with a .vcf or .csv extension to
    # the vcf_paths list.
    for file in os.listdir(filepath):
        if file.endswith('.vcf') or file.endswith('.csv'):
            variant_paths.append(f'{filepath}/{file}')
        else:
            continue

    # If there aren't any variant files in the 'temp' folder (i.e. files that do not have a .vcf or .csv extension),
    # notify the user through a flash message and log the warning.
    if len(variant_paths) == 0:
        logger.warning(f"patient_variant_table: No VCF/CSV files detected in 'temp' directory: {filepath}")
        flash(
            '⚠ No variant files have been uploaded. Please upload a .VCF or .CSV file or select a database to query.')
        # Return an 'error' message to be processed by app.py.
        return 'error'

    # Log the number of variant files in temp directory.
    logger.info(f'{len(variant_paths)} variant files in {filepath}.')

    # Log the variant file names that will be processed.
    for file in variant_paths:
        logger.debug(f"patient_variant_table: Uploaded files: {file.split('/')[-1]}")

    # Create (or connect to) the database file:
    # Get the filepath to the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Build absolute path to the database
    db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'databases', f'{db_name}.db'))
    # Make the databases folder if it does not exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Check that the sqlite3 database is operational and has integrity.
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        # Create a cursor to run SQL commands
        cursor = conn.cursor()
        # Log the filepath to the database.
        logger.info(f'patient_variant_table: Connected to {db_name}.db: {db_path}')

        # Create the patient_variant table if it does not already exist. UNIQUE groups the patient_ID and variant
        # together to ensure that they can only appear together, once, in the table.
        cursor.execute("""
                           CREATE TABLE IF NOT EXISTS patient_variant (
                                                                          No INTEGER PRIMARY KEY,
                                                                          patient_ID TEXT NOT NULL,
                                                                          variant TEXT NOT NULL,
                                                                          UNIQUE(patient_ID, variant)
                               )
                           """)

        # Log that the patient_table exists and can be populated.
        logger.info(
            'patient_variant_table: '
            'Successfully prepared patient_variant table to be populated by patients and their respective variants.')

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately and returns an error message which can be implemented
        # into a flash message, on the homepage page.
        error_message = sqlite_error(e, f'{db_name}.db')
        logger.error(f'patient_variant_table SQLite3 Error: Failed to create/check patient_variant table.')
        flash(f'❌ patient_variant_table SQLite3 Error: {error_message}.')
        # Close the connection to the database.
        conn.close()
        # Return an 'error' message to be processed by app.py.
        return 'error'

    # Raise an exception if the headers cannot be created.
    except Exception as e:
        logger.error(f'patient_variant_table Error: Failed to create/check patient_variant table: {e}')
        # Notify the user of that there was an error while preparing the database.
        flash(f'❌ patient_variant_table Error occurred while preparing {db_name}.db.')
        # Close the connection to the database.
        conn.close()
        # Return an 'error' message to be processed by app.py.
        return 'error'

    # Iterate through the absolute filepaths to the .vcf files.
    for path in variant_paths:

        # Take the file name from the filepath to annotate the flash messages and logs.
        file = path.split('/')[-1]

        # The patient's ID appears in the filepath, after the final directory, which ends in a '/', and before the
        # .vcf file extension.
        patient_name = path.split('/')[-1].split('.')[0]

        # Log the patient's name being added to the table.
        logger.debug(f'patient_variant_table: Parsing variants from {path}...')

        # Try to apply the variant_parser function to extract the variants listed in the files.
        try:
            variant_list = variant_parser(path)

            # Log how many variants were parsed and from which file.
            logger.info(f'patient_variant_table: {len(variant_list)} variants parsed from {path}')

            # Log which variants have been parsed.
            logger.debug(f'patient_variant_table: Parsed from {file}: {variant_list}')

        # If an exception arises, log the error using the exception output and notify the user. Then move to the next
        # variant file.
        except Exception as e:
            logger.error(
                f'patient_variant_table Error: variant_parser error while parsing variants from {path}: {e}')
            flash(
                f"❌ patient_variant_table Error: Could not parse variants from {file}. "
                f"Please check the file/variant format or path to 'temp' directory.")
            continue

        # If variant_parser does not parse any variants, log the filepath to the file which could not be parsed and
        # notify the user. Then move on to the next file.
        if not variant_list:
            logger.warning(f'patient_variant_table: No variants were parsed from {path}.')
            flash(f"⚠ No variants were parsed from {file}")
            continue

        else:
            # Log the file that variants were parsed from.
            logger.info(f'patient_variant_table: {len(variant_list)} variants parsed from {path}')
            # Log the list of variants that were parsed.
            logger.debug(f'patient_variant_table: Variant list: {variant_list}')

        # VariantValidator is queried through fetch_vv to retrieve the NC_ genomic description of each
        # variant in the variant_list, in HGVS nomenclature.
        for variant in variant_list:
            # Log the file and variant that is being queried on VariantValidator.
            logger.info(f"patient_variant_table: Querying VariantValidator for {file}: {variant}")

            # Check that the HGVS genomic description can be retrieved from VariantValidator.
            try:
                # Use the fetch_vv function to get the HGVS genomic description.
                variant_info = fetch_vv(variant)
                # The time module creates a 0.5s delay after each request to VariantValidator , so that VV is not
                # overloaded with requests.
                time.sleep(0.5)

            # Raise an exception if fetch_vv is not working.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(f'patient_variant_table: Failed to execute fetch_vv function: {file}: {variant}. {e}')
                # Notify the User that VariantValidator cannot be queried.
                flash(f'{file}: {variant}: ❌ patient_variant_table Error: Could not retrieve a response from '
                      f'VariantValidator. Variant not added to database.')
                continue

            # If a response was not received from VariantValidator, it is logged and communicated to the user.
            if not variant_info:
                logger.warning(f'patient_variant_table: {file}: {variant}: '
                               f'No response was received from VariantValidator. Variant not added to database.')
                flash(f'{file}: {variant}: ⚠ No response was received from VariantValidator. '
                      f'Variant not added to database.')
                continue

            # If the response received from fetch_vv is a string and not the tuple, log the error and notify the User
            # through the flask app. Then move onto the next varaiant.
            elif type(variant_info) == str:
                logger.warning(f'patient_variant_table: {file}: {variant_info}. Variant not added to {db_name}.db.')
                flash(f'{file}: {variant_info}')
                continue

            # Check if the response from VariantValidator is valid. 'variant_info' should be a tuple containing the
            # genomic description, transcript description and protein consequence all in HGVS nomenclature, followed by
            # the gene symbol and HGNC ID.
            else:
                # If the first variable in the response from fetch_vv is not the genomic description, an exception will
                # be raised where the VariantValidator error will be logged and shown to the user. Then process the next
                # variant in the list.
                if not variant_info[0].startswith('NC_'):
                    logger.error(
                        f'patient_variant_table: {file}: HGVS genomic description not retreived by fetch_vv: {e}.')
                    logger.debug(f'patient_variant_table: Output from fetch_vv: {variant_info}')
                    flash(f'{file}: {variant}: ❌ Could not retrieve HGVS description from VariantValidator.')
                    continue
                # Extract the genomic description in HGVS nomenclature from VariantValidator response.
                else:
                    logger.info(
                        f'patient_variant_table: {file}: {variant}: VariantValidator returned {variant_info[0]}.')

                # Check that the patient ID and corresponding variant can be added to the patient_variant table.
                try:
                    cursor.execute("INSERT OR IGNORE INTO patient_variant (patient_ID, variant) VALUES (?, ?)",
                                   (patient_name, variant_info[0]))

                    logger.info(f'{file}: {variant}: {patient_name} and {variant_info[0]} '
                                f'successfully added to patient_variant table.')

                # Error handler executed when exceptions related to sqlite3 are raised.
                except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
                    # sqlite_error function logs the errors appropriately.
                    sqlite_error(e, f'{db_name}.db')
                    logger.error(
                        f'patient_variant_table SQLite3 Error: '
                        f'Failed to enter {patient_name} and {variant_info[0]} into patient_variant table.')
                    flash(f'❌ patient_variant_table: SQLite3 Error: '
                          f'Could not add {patient_name} and {variant_info[0]} to {db_name}.db.')
                    # Continue to the next variant.
                    continue

                # Raise an exception if the patient ID and/or variant description cannot be added to the
                # patient_variant table.
                except Exception as e:
                    logger.error(f'patient_variant_table Error: Failed to enter {patient_name} and {variant_info[0]} '
                                 f'into patient_variant table: {e}')
                    # Notify the user of that there was an error while preparing the database.
                    flash(f'❌ patient_variant_table Error: '
                          f'Could not add {patient_name} and {variant_info[0]} to {db_name}.db.')
                    # Continue to the next variant.
                    continue

    # Save (commit) changes to the database.
    conn.commit()

    # Check if a variant has been added to the patient_variant table.
    try:
        # Query the patient_variant table for any entries.
        cursor.execute(f"SELECT COUNT(*) FROM patient_variant")
        row_count = cursor.fetchone()[0]

        # If nothing has been added to the table...
        if row_count == 0:
            # Log that the patient_variant table is empty.
            logger.warning(f"patient_variant table in {db_name}.db is empty. Deleting database file…")
            # Close the connection to the database.
            conn.close()
            # Delete the database.
            os.remove(db_path)
            # Notify the User that the patient_variant table is empty and that the database will be deleted.
            flash(f'⚠ {file} did not contain any variants that could be loaded into patient_variant table. {db_name}.db '
                  f'was deleted.')
            # Return an 'error' message to be processed by app.py.
            return 'error'
        else:
            # A message is logged and shown to the user to indicate that the database was successfully created or
            # updated.
            logger.info(f'Patient_variant table in {db_name}.db created/updated successfully!')
            # Close the connection to the database.
            conn.close()

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately.
        sqlite_error(e, f'{db_name}.db')
        logger.error(f'patient_variant_table SQLite3 Error: Failed to check patient_variant table in {db_name}.db.')
        flash(f'❌ patient_variant_table: SQLite3 Error: {db_name}.db may not have been processed correctly. '
              f'Data may be compromised.')
        # Close the connection to the database.
        conn.close()
        # Return an 'error' message to be processed by app.py.
        return 'error'

    # Raise an exception if the patient_variant table could not be checked.
    except Exception as e:
        # Log the error.
        logger.error(f'patient_variant_table Error: Failed to check patient_variant table in {db_name}.db: {e}')
        # Notify the User that there was an error while preparing the database.
        flash(f'❌ patient_variant_table Error: {db_name}.db may not have been processed correctly. '
              f'Data may be compromised.')
        # Close the connection to the database.
        conn.close()
        # Return an 'error' message to be processed by app.py.
        return 'error'


def variant_annotations_table(filepath, db_name):
    """
    This function creates a database, if it doesn't already exist.
    It then creates or updates a table in the database called 'variant_annotations', which is populated by variants
    extracted from variant files uploaded by the User through our Flask app, denoted as HGVS genomic descriptions from
    VariantValidator.
    Each variant is further annotated by the HGVS transcript description, HGVS protein description, gene symbol and
    HGNC ID, also from VariantValidator, as well as the cumulative variant classification, associated conditions,
    star-rating and review status, from ClinVar.

    :params: filepath: This leads to the subdirectory where the variant files uploaded by the user are stored.
                       The subdirectory is called 'temp' and is located in the base-directory of this software package.
                       The filepath is not hardcoded into the script because it is the absolute filepath within the
                       respective computer that this software package was loaded in.

                 E.g.: '/<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                         Software_Engineering_Assessment_2025_AR_RW_RS/temp/'

              db_name: The user-specified name of the database.

                 E.g.: 'my_database'

    :output: A database containing the variant_annotations table.
             The database will be saved at: '/<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                                              Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db'

             variant_annotations table: A table consisting of a unique index number, the HGVS genomic description, HGVS
                                        transcript description, HGVS protein description, gene symbol and HGNC ID, of
                                        the variants parsed from the respective patient's variant file. It also contains
                                        the variant classification, associated conditions, star-rating and review
                                        status, from ClinVar.

             E.g.:  patient_ID | variant_NC	   | variant_NM   | variant_NP	  | gene   | HGNC_ID | Classification | Conditions	| Stars | Review_status
                   ------------|---------------|--------------|---------------|--------|---------|----------------|-------------|-------|-------------------
                    Patient1   | NC_000019.10: | NM_152296.5: | NP_689509.1:  | ATP1A3 | 801     | Pathogenic     | Dystonia 12 | ★    | criteria provided,
                               | g.41968837C>G | c.2767G>C    | p.(Asp923His) |        |         |                |             | 	    | single submitter


    :command: filepath = '/<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                           Software_Engineering_Assessment_2025_AR_RW_RS/temp/'

              variantAnnotationsTable(filepath, 'my_database')

              To access database: sqlite3 /<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                                           Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db

              To view table: SELECT * FROM variant_annotations;
    """

    # Log the start of the function.
    logger.info('Preparing variant_annotations_table()...')
    # Log the absolute filepath to the 'temp' directory where the data is going to be pulled into the database from.
    # And the name of the database being updated/created by the user.
    logger.debug(
        f'variant_annotations_table: Filepath to variant files: {filepath}; database to be populated: {db_name}')
    # Create a list of the filepaths to all the variant files in the 'temp' subdirectory.
    vcf_paths = []

    # Iterate through the files in the filepath provided by the user and add the files with a .vcf or .csv extension to
    # the vcf_paths list.
    for file in os.listdir(filepath):
        if file.endswith('.vcf') or file.endswith('.csv'):
            vcf_paths.append(f'{filepath}/{file}')
        else:
            continue

    # If there aren't any variant files in the 'temp' folder, notify the user through a flash message and log the
    # warning.
    if len(vcf_paths) == 0:
        logger.warning(f"No VCF/CSV files detected in 'temp' directory: {filepath}")
        flash('⚠ variant_annotations_table: No data files have been uploaded. '
              'Please upload a .VCF or .CSV file or select a database to query.')
        # Return an 'error' message to be processed by app.py.
        return 'error'

    # Log the number of variant files in temp directory.
    logger.info(f'variant_annotations_table: {len(vcf_paths)} variant files in {filepath}.')

    # Log the variant file names that will be processed.
    for path in vcf_paths:
        logger.debug(f"variant_annotations_table: Variant files detected: {path.split('/')[-1]}")

    # Get the filepath to the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))  # RS

    # Absolute path to database
    db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'databases', f'{db_name}.db'))  # RS

    # Make the databases folder if it does not exist.
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        # Create a cursor to run SQL commands
        cursor = conn.cursor()
        # Log the filepath to the database.
        logger.debug(f'variant_annotations_table: Connected to database: {db_path}')

        # Create the variant_annotations table if it does not already exist. UNIQUE groups the variant_NC, variant_NM,
        # and variant_NP together to ensure that they can only appear once in the table together.
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
                                                                      Stars TEXT,
                                                                      Review_status TEXT NOT NULL,
                                                                      UNIQUE(variant_NC, variant_NM, variant_NP)
                       )
                   """)

        # Log that the variant_annotations table exists and can be populated.
        logger.info('variant_annotations_table: Successfully prepared variant_annotations table to be populated by '
                    'patients and their respective variants.')

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately and returns an error message which can be implemented
        # into a flash message, on the homepage page.
        error_message = sqlite_error(e, f'{db_name}.db')
        logger.error(f'variant_annotations_table SQLite3 Error: Failed to create/check variant_annotations table.')
        flash(f'❌ variant_annotations_table SQLite3 Error: {error_message}.')
        # Close the connection to the database.
        conn.close()
        # Return an 'error' message to be processed by app.py.
        return 'error'

    # Raise an exception if the headers cannot be created in variant_annotations table.
    except Exception as e:
        logger.error(
            f'variant_annotations_table Error: Failed to create/check headers in variant_annotations table: {e}')
        # Notify the user of that there was an error while preparing the database.
        flash(f'❌ variant_annotations_table Error occurred while preparing {db_name}.db.')
        # Close the connection to the database.
        conn.close()
        # Return an 'error' message to be processed by app.py.
        return 'error'

    # Iterate through the absolute filepaths to the .vcf files.
    for path in vcf_paths:

        # Take the file name from the filepath to annotate the flash messages and logs.
        file = path.split('/')[-1]

        # The patient's ID appears in the filepath, after the final directory, which ends in a '/', and before the
        # .vcf file extension.
        patient_name = path.split('/')[-1].split('.')[0]

        # Log the patient's name being added to the table.
        logger.info(f'variant_annotations_table: Processing variants from {patient_name}...')
        # Log the file path where the variants derive from.
        logger.debug(f'variant_annotations_table: Parsing variants from {path}...')

        try:
            # Apply the variant_parser function to extract the variants listed in the files.
            variant_list = variant_parser(path)

            # Log how many variants were parsed and from which file.
            logger.info(f'variant_annotations_table: {len(variant_list)} variants parsed from {file}')

            # Log which variants have been parsed.
            logger.debug(f'variant_annotations_table: Parsed from {file}: {variant_list}')

        # Raise an exception if variant_parser failed.
        except Exception as e:
            logger.error(f'variant_annotations_table: Failed to parse variants from {file}: {e}')
            # Notify the User f variants could not be parsed.
            flash(f"❌ Could not parse variants from {file}. Please check the file format or path to 'temp' directory.")
            continue

        # Data is then assigned to each header:

        # VariantValidator is queried through fetchVV to retrieve the NC_, NM_ and NP_ accession numbers of each
        # variant in the variant_list, in HGVS nomenclature.
        for variant in variant_list:

            # Log when VariantValidator is being queried.
            logger.info(f'variant_annotations_table: {file}: Querying VariantValidator for {variant}...')

            try:
                vv_response = fetch_vv(variant)
                # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not
                # overloaded with requests.
                time.sleep(0.5)

            # Raise an exception if fetch_vv is not working.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(f'variant_annotations_table: {file}: {variant}: Failed to execute fetch_vv function: {e}')
                # Notify the User that VariantValidator cannot be queried.
                flash(f'{file}: {variant}: ❌ Could not retrieve a response from VariantValidator. '
                      f'Variant not added to {db_name}.db.')
                continue

            # Try to accommodate for errors in the VariantValidator response.
            try:
                # If no response was received from fetch_vv, log the error and notify the User through the flask app.
                # Then move onto the next variant.
                if not vv_response:
                    logger.warning(
                        f'variant_annotations_table: {file}: {variant}: Failed to receive a response from fetch_vv.')
                    flash(
                        f'{file}: {variant}: ⚠ No response from VariantValidator. Variant not added to {db_name}.db.')
                    continue

                # If the response received from fetch_vv is a string and not the tuple, log the error and notify the
                # User through the flask app. Then move onto the next variant.
                elif type(vv_response) == str:
                    logger.warning(
                        f'variant_annotations_table: {file}: {vv_response}. Variant not added to {db_name}.db.')
                    flash(f'{file}: {vv_response}')
                    continue

                else:
                    # Allocate the different values from fetch_vv to corresponding variables.
                    nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id = vv_response
                    # Log the output from fetch_vv
                    logger.info(f'{file}: {variant}: fetch_vv produced this output: {vv_response}')

            # Raise an exception if an error is not caught within the try statement.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(f'variant_annotations_table: {file}: {variant}: '
                             f'Unable to process the response from fetch_vv function: {e}')
                # Notify the User that the variant cannot be queried through VariantValidator.
                flash(f'{file}: {variant}: ❌ Unable to query this variant through VariantValidator. '
                      f'Variant not added to {db_name}.db.')
                continue

            # clinvar.db is queried using clinvar_annotations() from clinvar_functions.py to retrieve the variant
            # classification, associated conditions, the star-ratings and the review statuses:

            # Log that clinvar.db is being queried.
            logger.info(f'variant_annotations_table: {file}: {variant}: Querying clinvar.db for {nc_variant}...')

            try:
                clinvar_response = clinvar_annotations(nc_variant, nm_variant)

            # Raise an exception if clinvar_annotations is not working.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(f'variant_annotations_table: {file}: '
                             f'{variant}: Failed to execute clinvar_annotations function: {e}')
                # Notify the User that a variant summary record cannot be retrieved from clinvar.db.
                flash(f'{file}: {variant}: ❌ Unable to query clinvar.db. Variant not added to {db_name}.db.')
                continue

            # Try to accommodate for errors in the clinvar_annotations response.
            try:
                # If no response was received from clinvar_annotations or the function returned a blank response, log
                # the error and notify the User through the flask app. Then move onto the next varaiant.
                if not clinvar_response or len(clinvar_response) == 0:
                    logger.warning(f'variant_annotations_table: {file}: {variant}: '
                                   f'Variant summary record for {nc_variant} not found in clinvar.db.')
                    flash(f'{file}: {variant}: ❌ Variant summary record could not be found in clinvar.db. '
                          f'Variant not added to {db_name}.db.')
                    continue

                # If the response received from fetch_vv is a string and not the tuple, log the error and notify the
                # User through the flask app. Then move onto the next varaiant.
                elif type(clinvar_response) == str:
                    logger.warning(f'variant_annotations_table: {file}: {clinvar_response}.')
                    flash(f'{file}: {clinvar_response}. Variant not added to {db_name}.db')
                    continue

                elif type(clinvar_response) == dict and len(clinvar_response) > 0:
                    classification = clinvar_response['classification']
                    conditions = clinvar_response['conditions']
                    stars = clinvar_response['stars']
                    review_status = clinvar_response['reviewstatus']

                    # The HGVS nomenclatures, gene symbol, HGNC ID and ClinVar annotations for each variant are added
                    # to the variant_annotations table. If the HGVS descriptions already exist in the table as a set,
                    # another entry will not be created in the table.
                    try:
                        cursor.execute("""
                                       INSERT INTO variant_annotations
                                       (variant_NC, variant_NM, variant_NP, gene, HGNC_ID, 
                                        classification, conditions, stars, review_status)
                                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                       ON CONFLICT(variant_NC, variant_NM, variant_NP)
                                       DO UPDATE SET
                                           gene = excluded.gene,
                                           HGNC_ID = excluded.HGNC_ID,
                                           classification = excluded.classification,
                                           conditions = excluded.conditions,
                                           stars = excluded.stars,
                                          review_status = excluded.review_status
                                       """, (
                                           nc_variant, nm_variant, np_variant,
                                           gene_symbol, hgnc_id,
                                           classification, conditions, stars, review_status
                        ))

                        # Log that the variant_annotations table exists and can be populated.
                        logger.info(f'{file}: {variant}: Successfully populated variant_annotations table with ClinVar '
                                    f'annotations.')

                    # Error handler executed when exceptions related to sqlite3 are raised.
                    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
                        # sqlite_error function logs the errors appropriately and returns an error message which can be
                        # implemented into a flash message, on the homepage page.
                        sqlite_error(e, db_name)
                        logger.error(f'variant_annotations_table SQLite3 Error: Failed to populate variant_annotations '
                                     f'table with {variant} from {patient_name} and {clinvar_response}: {e}')
                        flash(f'❌ variant_annotations_table SQLite3 Error: Variant annotations could be not be added '
                              f'to variant_annotations table. Variant not added to {db_name}.db.')
                        # Close the connection to the database.
                        conn.close()
                        continue

                    # Raise an exception if the patient name and variant could not be entered into the
                    # variant_annotations table.
                    except Exception as e:
                        logger.error(
                            f'variant_annotations_table Error: Failed to populate variant_annotations table with '
                            f'{variant} from {patient_name} and {clinvar_response}: {e}')
                        # Notify the user of that there was an error while preparing the database.
                        flash(f'❌ variant_annotations_table Error: Variant annotations could be not be added to '
                              f'variant_annotations table. Variant not added to {db_name}.db.')
                        # Close the connection to the database.
                        conn.close()
                        continue

            # Raise an exception if an error is not caught within the try statement.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(
                    f'variant_annotations_table: {file}: {variant}: Unable to process the response from '
                    f'clinvar_annotations() function: {e}')
                # Notify the User that the variant did not return a response from clinvar.db.
                flash(
                    f'{file}: {variant}: ❌ Unable to query clinvar.db for this variant. Variant not added to {db_name}.db.')
                continue

    # Save (commit) changes.
    conn.commit()

    # Check if a variant has been added to the variant_annotations table.
    try:
        # Query the variant_annotations table for any entries.
        cursor.execute(f"SELECT COUNT(*) FROM variant_annotations")
        row_count = cursor.fetchone()[0]

        # If nothing has been added to the table...
        if row_count == 0:
            # Log that the variant_annotations table is empty.
            logger.warning(f"variant_annotations table in {db_name}.db is empty. Deleting database file…")
            # Close the connection to the database.
            conn.close()
            # Delete the database.
            os.remove(db_path)
            # Notify the User that the variant_annotations table is empty and that the database will be deleted.
            flash(f'⚠ {file} did not contain any variants that could be loaded into variant_annotations table. '
                  f'{db_name}.db was deleted.')
            # Return an 'error' message to be processed by app.py.
            return 'error'

        else:
            # A message is logged and shown to the user to indicate that the database was successfully created or
            # updated.
            logger.info(f'variant_annotations table in {db_name}.db created/updated successfully!')
            # Close the connection to the database.
            conn.close()
            # Notify the User that the variant_annotations table and database was created/updated successfully.
            flash(f'{db_name}.db created/updated successfully!')

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately.
        sqlite_error(e, f'{db_name}.db')
        logger.error(
            f'variant_annotations_table SQLite3 Error: Failed to check variant_annotations table in {db_name}.db.')
        flash(f'❌ variant_annotations_table: SQLite3 Error: {db_name}.db may not have been processed correctly. '
              f'Data may be compromised.')
        # Close the connection to the database.
        conn.close()
        # Return an 'error' message to be processed by app.py.
        return 'error'

    # Raise an exception if the variant_annotations table could not be checked.
    except Exception as e:
        # Log the error.
        logger.error(f'variant_annotations_table Error: Failed to check variant_annotations table in {db_name}.db: {e}')
        # Notify the User that there was an error while preparing the database.
        flash(f'❌ variant_annotations_table Error: {db_name}.db may not have been processed correctly. '
              f'Data may be compromised.')
        # Close the connection to the database.
        conn.close()
        # Return an 'error' message to be processed by app.py.
        return 'error'


def validate_database(db_path):
    """
    This function checks that the databases uploaded by the User have the expected tables and headers so that they can
    be queried and viewed, using the other programs included in this software package.

    :params: db_path: Path to the database uploaded by the User, in this software package's 'databases' folder.
                E.g.: '/<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                         Software_Engineering_Assessment_2025_AR_RW_RS/databases/<uploaded_database>.db'

    :output: True: If the validation process has been passed, True will be returned to app.py, where this function has
                   been implemented. This will enable the uploaded database to be queried.

            False: If the validation process has not been passed, False will be returned to app.py, where this function
                   has been implemented. This will cause the uploaded database to be deleted from the 'database' folder.
    """

    db_name = db_path.split('/')[-1]
    logger.info(f'Checking that the {db_name} database uploaded by the User conforms with the expected schema...')

    # Define the headers to expect in the patient_variant and variant_annotations tables, in the uploaded database.
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

    # Check if the database specified in this function's argument can be connected to and queried using SQLite3.
    try:
        # The 'with' keyword opens a connection to the uploaded database and closes it automatically after the
        # validation check has been performed.
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            # Find the names of the tables in the database.
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            # Return the name of each table in the database.
            tables = {row[0] for row in cur.fetchall()}

            # Check that the uploaded database contains a table called 'patient_variant' and another called
            # 'variant_annotations'.
            if not EXPECTED_SCHEMA.keys() <= tables:
                # If it does not contain the expected tables, log that the database does not contain the required
                # tables.
                logger.warning(f'The tables in {db_name} are not as expected: {tables}')
                # Notify the User that the database does not have the right tables.
                flash(f'⚠ Inappropriate tables in {db_name} database.')
                # Return False. False will delete the uploaded database from this software package's 'databases'
                # folder, using a boolean in app.py.
                return False

            # Iterate through the expected tables (table) and respective headers in each table (expected_cols).
            for table, expected_cols in EXPECTED_SCHEMA.items():
                # Find the headers of the 'patient_variant' and 'variant_annotations' tables in the database.
                cur.execute(f"PRAGMA table_info({table});")
                # Return the name of each header in the aforementioned tables.
                cols = {row[1] for row in cur.fetchall()}
                # Check that the uploaded database contains the expected headers in its 'patient_variant' and
                # 'variant_annotations' tables.
                if not expected_cols <= cols:
                    # If it does not contain the expected headers, log that the database contains inappropriate headers.
                    logger.warning(f'The headers in {db_name} are not as expected: {cols}')
                    # Notify the User that the database does not have the right headers.
                    flash(f'⚠ Inappropriate headers in {db_name} database.')
                    # Return False. False will delete the uploaded database from this software package's 'databases'
                    # folder, using a boolean in app.py.
                    return False

        # If the uploaded database consists of the expected schema, return True. True will pass the validation check
        # and enable the database to be queried.
        return True

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
        # sqlite_error function logs the errors appropriately.
        sqlite_error(e, f'{db_name}.db')
        logger.error(
            f'Database Validation SQLite3 Error: Failed to check table and headers in {db_name}.db.')
        flash(f'❌ Database Validation: SQLite3 Error: {db_name}.db was not validated.')
        # Return False. False will delete the uploaded database from this software package's 'databases' folder, using
        # a boolean in app.py.
        return False

    # Raise an exception if the uploaded database could not be validated.
    except Exception as e:
        # Log the error.
        logger.error(f'Database Validation Error: Failed to check table and headers in {db_name}.db: {e}')
        # Notify the User that there was an error while preparing the database.
        flash(f'❌ Database Validation Error: Failed to check table and headers in {db_name}.db.')
        # Return False. False will delete the uploaded database from this software package's 'databases' folder, using
        # a boolean in app.py.
        return False


def query_db(db_path, query, args=(), one=False):
    """
    This function is applied on the query page of this software packages flask app (app.py).
    This function applies the SQLite3 query formulated by the User when they query their selected database on the flask
    app query page. The variants found in a specific patient, the number of times a variant occurs in the database, and
    which variants occur in a specified gene can all be queried individually.

    :params: db_path: Path to the database uploaded by the User, in this software package's 'databases' folder.
                E.g.: '/<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                         Software_Engineering_Assessment_2025_AR_RW_RS/databases/<uploaded_database>.db'

               query: The SQLite3 query used to return specific entries from the database to a table in the flask app's
                      user interface.
                E.g.: query = '''
                      SELECT
                          pv.patient_ID,
                          v.variant_NC,
                          v.variant_NM,
                          v.variant_NP,
                          v.gene,
                          v.HGNC_ID,
                          v.Classification,
                          v.Conditions,
                          v.Stars,
                         v.Review_status
                      FROM patient_variant pv
                      JOIN variant_annotations v
                        ON pv.variant = v.variant_NC
                      WHERE pv.patient_ID = ?
                      '''

                args: This parameter is set to an empty tuple by default. The empty tuple is replaced by the User's
                      search term, which is used to specify which entries from the database should be returned.
                E.g.: patient_ID = 'Patient1'
                      args = Patient_ID -> Variants identified in 'Patient1' will be returned.

                 one: This boolean flag indicates whether all the entries returned from the query will be returned by
                      this function. It is set to False by default.
                E.g.: False returns all the entries returned from the query.
                      True returns only the first row returned from the query or None. None type returns are error
                      handled in a particular, in app.py

    :output: rv: A list of sqlite3.Row objects. Each object represents a response from the query. Values held within the
                 object are in dictionary format, where the headers that they were stored under are assigned as the key
                 to the value.

       E.g.: [<sqlite3.Row object at 0x11000b2e0>, <sqlite3.Row object at 0x11000b340>,
              <sqlite3.Row object at 0x11000b3a0>, <sqlite3.Row object at 0x11000b400>,
              <sqlite3.Row object at 0x11000b460>, <sqlite3.Row object at 0x11000b4c0>,
              <sqlite3.Row object at 0x11000b520>, <sqlite3.Row object at 0x11000b580>]

             first_response = rv[0]
             first_response[patient_ID] = 'Patient1'
             first_response[Conditions] = 'Pathogenic'
    """

    # Assign the name of the database being queried to 'db_name'.
    db_name = db_path.split('/')[-1]
    # Log the SQLite3 query being applied and that database that it is being applied to.
    logger.info(f'Database: {db_name}')
    logger.info(f'Query: {query}')

    # Check that the SQLite3 query can be applied to the specified database.
    try:
        # The 'with' keyword opens a connection to the database being queried and closes it automatically after the
        # query has been applied.
        with sqlite3.connect(db_path) as conn:
            # Converts each row in the database into a dictionary type, where each value is assigned to a key named
            # after the respective header that it was under.
            conn.row_factory = sqlite3.Row
            # Apply the query to the database and return the entries returned by the query to the object 'cur'.
            # args inserts the search term entered by the User into the query.
            cur = conn.execute(query, args)
            # Fetch all the results returned by the query.
            rv = cur.fetchall()
            # 'one' is automatically set to False when query_db() starts.
            # If 'one' is False, query_db() will return all the rows returned by the query.
            # If 'one' is True, query_db() will return None if nothing was returned by the query, and only the first
            # row if something was.
            return (rv[0] if rv else None) if one else rv

    # Error handler executed when exceptions related to sqlite3 are raised.
    except (sqlite3.OperationalError, sqlite3.DatabaseError, sqlite3.ProgrammingError) as e:
    # sqlite_error function logs the errors appropriately.
        error_message = sqlite_error(e, db_name)
        logger.error(f"Database Query SQLite3 Error: Failed to apply the User's query to {db_name}")
        flash(f'❌ Database Query: SQLite3 Error: {db_name}.db could not be queried. {error_message}')
        # Return None. None type returns will be processed in a particular way in app.py.
        return None

    # Raise an exception if the SQLite3 query could not be applied.
    except Exception as e:
        # Log the error.
        logger.error(f"Database Query Error: Failed to apply the User's query to {db_name}: {e}")
        # Notify the User that there was an error while preparing the database.
        flash(f'❌ Database Query Error: Failed to query {db_name}')
        # Close the connection to the database.
        conn.close()
        # Return None. None type returns will be processed in a particular way in app.py.
        return None