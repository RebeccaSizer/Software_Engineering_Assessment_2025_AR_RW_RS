import os
import time
import sqlite3
from flask import flash
from .vv_functions import fetch_vv
from tools.utils.logger import logger
from ..utils.parser import variant_parser
from .clinvar_functions import clinvar_annotations

def patient_variant_table(filepath, db_name):
    """
    This function creates a database, if it doesn't already exist.
    It creates or updates a table in the database called 'patient_variant', which is populated by patients and their
    respective variants. The patients' IDs are taken from the name of the .vcf files uploaded by the user on our flask
    app, while the variants are extracted from each patient's .vcf file and validated through VariantValidator.

    :params: filepath: This leads to the 'temp' subdirectory where the .vcf files uploaded by the user are stored.
                       'temp''is located in the base-directory of this software package.The filepath is not hardcoded
                       into the script because it is the absolute filepath within the respective computer that this
                       software package was loaded in.

                 E.g.: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/temp/'

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

    :command: filepath = '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/temp/'
              patientVariantTable(filepath, 'my_database.db')

              To access database: sqlite3 /<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db

              To view table: SELECT * FROM patientVariantTable;
    """

    # Log the start of the function.
    logger.info('Preparing patient_variant_table()...')
    # Log the absolute filepath to the 'temp' directory where the data is going to be pulled into the database from.
    # And the name of the database being updated/created by the user.
    logger.debug(f'patient_variant_table: Filepath to data: {filepath}; database to be populated: {db_name}')

    # Create a list of the filepaths to all the variant files in the 'temp' subdirectory.
    vcf_paths = []

    # Iterate through the files in the filepath provided by the user and add the files with a .vcf or .csv extension to
    # the vcf_paths list.
    for file in os.listdir(filepath):
        if file.endswith('.vcf') or file.endswith('.csv'):
            vcf_paths.append(f'{filepath}/{file}')
        else:
            continue

    # If there aren't any variant files in the 'temp' folder (i.e. files that do not have a .vcf or .csv extension),
    # notify the user through a flash message and log the warning.
    if len(vcf_paths) == 0:
        flash(' ⚠ No varaint files have been uploaded. Please upload a .VCF or .CSV file or select a database to query.')
        logger.warning(f"patient_variant_table: No VCF/CSV files detected in 'temp' directory: {filepath}")

    # Log the number of variant files in temp directory.
    logger.info(f'{len(vcf_paths)} variant files in {filepath}.')

    # Log the variant file names that will be processed.
    for file in vcf_paths:
        logger.debug(f"patient_variant_table: Uploaded files: {file.split('/')[-1]}")

    # Create (or connect to) the database file:

    # Get the filepath to the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Build absolute path to the database
    db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'databases', f'{db_name}.db'))

    # Make the databases folder if it does not exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        # Create a cursor to run SQL commands
        cursor = conn.cursor()
        # Log the filepath to the database.
        logger.info(f'patient_variant_table: Connected to {db_name}.db: {db_path}')

    # Raise an error if the database cannot be connected to. This may happen if the databse is locked.
    except Exception as e:
        # Log the error using the exceptions output.
        logger.error(f'patient_variant_table: Could not connect to database: {db_path}. {e}', exc_info=True)
        # Notify the user that there was an issue creating/connectig to the databsae that they specified.
        flash(f'❌ {db_name}: Unable to connect to database.')

    # Create the patient_variant table if it does not already exist. UNIQUE groups the patient_ID and variant together
    # to ensure that they can only appear once in the table together.
    try:
        cursor.execute("""
                           CREATE TABLE IF NOT EXISTS patient_variant (
                                                                          No INTEGER PRIMARY KEY,
                                                                          patient_ID TEXT NOT NULL,
                                                                          variant TEXT NOT NULL,
                                                                          UNIQUE(patient_ID, variant)
                               )
                           """)

        # Log that the patient_table exists and can be populated.
        logger.info('patient_variant_table: Successfully prepared patient_variant table to be populated by patients and their respective variants.')

    # Raise an exception if the headers cannot be created.
    except Exception as e:
        logger.error(f'patient_variant_table: Failed to create/check patient_variant table: {e}', exc_info=True)
        # Notify the user of that there was an error while preparing the database.
        flash(f'❌ Error while preparing {db_name}.')
        conn.close()

    # Iterate through the absolute filepaths to the .vcf files.
    for path in vcf_paths:

        # Take the file name from the filepath to annotate the flash messages and logs.
        file = path.split('/')[-1]

        # The patient's ID appears in the filepath, after the final directory, which ends in a '/', and before the
        # .vcf file extension.
        patient_name = path.split('/')[-1].split('.')[0]

        # Log the patient's name being added to the table.
        logger.info(f'patient_variant_table: Processing variants from {patient_name}...')
        # Log the file path where the variants derive from.
        logger.debug(f'patient_variant_table: Parsing variants from {path}...')

        # Try to apply the variant_parser function to extract the variants listed in the files.
        try:
            variant_list = variant_parser(path)

            # Log how many variants were parsed and from which file.
            logger.info(f'patient_variant_table: {len(variant_list)} variants parsed from {file}')

            # Log which variants have been parsed.
            logger.debug(f'patient_variant_table: Parsed from {file}: {variant_list}')

        # If an exception arises, log the error using the exception output and notify the user. Then move to the next
        # variant file.
        except Exception as e:
            logger.error(f'patient_variant_table: variant_parser error while parsing variants in {path}: {e}', exc_info=True)
            flash(f" ❌ Could not parse variants in {path}. Please check the file format or path to 'temp' directory.")
            continue

        # If variant_parser does not parse any variants, log the filepath to the file which could not be parsed and
        # notify the user. Then move on to the next file.
        if not variant_list:
            logger.warning(f'patient_variant_table: No variants were parsed from {path}.')
            flash(f"No variants were parsed from {file}")
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

            try:
                # Use the fetch_vv function to get the HGVS genomic description.
                variant_info = fetch_vv(variant)
                # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not overloaded with requests.
                time.sleep(0.5)

            # Raise an exception if fetch_vv is not working.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(f'patient_variant_table: Failed to execute fetch_vv function: {file}: {variant}. {e}', exc_info=True)
                # Notify the User that VariantValidator cannot be queried.
                flash(f'{file}: {variant}: ❌ Could retrieve a response from VariatnValidator. Variant not added to database.')
                continue

            # If a response was not received from VariantValidator, it is logged and communicated to the user.
            if not variant_info:
                logger.warning(f'patient_variant_table: {file}: {variant}: No response was received from VariantValidator. Variant not added to database.')
                flash(f'{file}: {variant}: ❌ No response was received from VariantValidator. Variant not added to database.')
                continue

            # If the response received from fetch_vv is a string and not the tuple, log the error and notify the User
            # through the flask app. Then move onto the next varaiant.
            elif type(variant_info) == str:
                logger.error(f'patient_variant_table: {file}: {variant_info}. Variant not added to {db_name}.db.')
                flash(f'{file}: {variant_info}')
                continue

            else:
                # variant_info should be a tuple containing the genomic description, transcript description and protein
                # consequence all in HGVS nomenclature, followed by the gene symbol and HGNC ID.
                try:
                    # Try to extract the genomic description in HGVS nomenclature from VariantValidator response.
                    if variant_info[0].startswith('NC_') == True:
                        logger.info(f'patient_variant_table: {file}: {variant}: VariantValidator returned {variant_info[0]}.')

                # If the first variable in the response from fetch_vv is not the genomic description, an exception will
                # be raised where the VariantValidator error will be logged and shown to the user. Then process the next
                # variant in the list.
                except Exception as e:
                    logger.error(f'patient_variant_table: {file}: HGVS genomic description not retreived by fetch_vv: {e}.', exc_info=True)
                    logger.debug(f'patient_variant_table: Output from fetch_vv:\n{variant_info}')
                    flash(f'{file}: {variant}: ❌ Could not retrieve HGVS description from VariantValidator.')
                    continue

                try:
                    # Check that the patient ID and corresponding variant can be added to the patient_variant table.
                    cursor.execute("INSERT OR IGNORE INTO patient_variant (patient_ID, variant) VALUES (?, ?)",
                                   (patient_name, variant_info[0]))

                    logger.info(f'{file}: {variant}: {patient_name} and {variant_info[0]} successfully added to patient_variant table.')

                # Raise an exception if the patient name and variant could not be entered into the patient_variant
                # table.
                except Exception as e:
                    logger.error(f'Failed to enter {patient_name} and {variant_info[0]} into patient_variant table: {e}', exc_info=True)
                    flash(f'{file}: {variant}: ❌ Could not add {patient_name} and {variant_info[0]} to {db_name}.db.')
                    continue

    # Save (commit) changes to the database and close connection
    conn.commit()
    conn.close()

    # A message is logged and shown to the user to indicate that the database was successfully created or updated.
    logger.info(f'Patient_variant table in {db_name} created/updated successfully!')


def variant_annotations_table(filepath, db_name):
    '''
    This function creates a database, if it doesn't already exist.
    It then creates or updates a table in the database called 'variant_annotations', which is populated by variants
    extracted from .vcf files uploaded by the user on our flask website, denoted as HGVS genomic descriptions from
    VariantValidator.
    It is further annotated by the HGVS transcript description, HGVS NP_ nomenclature, gene symbol and HGNC ID, also
    from VariantValidator, as well as the cumulative variant classification, associated conditions, star-rating and
    review status, from ClinVar.

    :params: filepath: This leads to the subdirectory where the variant files uploaded by the user are stored.
                       The subdirectory is called 'temp' and is located in the base-directory of this software package.
                       The filepath is not hardcoded into the script because it is the absolute filepath within the
                       respective computer that this software package was loaded in.

                 E.g.: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/temp/'

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

    :command: filepath = '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/temp/'
              variantAnnotationsTable(filepath, 'my_database')

              To access database: sqlite3 /<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/database/my_database.db

              To view table: SELECT * FROM variant_annotations;
    '''

    # Log the start of the function.
    logger.info('Preparing variant_annotations_table()...')
    # Log the absolute filepath to the 'temp' directory where the data is going to be pulled into the database from.
    # And the name of the database being updated/created by the user.
    logger.debug(f'variant_annotations_table: Filepath to data: {filepath}; database to be populated: {db_name}')

    # Create a list of the filepaths to all of the variant files in the 'temp' subdirectory.
    vcf_paths = []

    # Iterate through the files in the filepath provided by the user and add the files with a .vcf or .csv extension to the vcf_paths list.
    for file in os.listdir(filepath):
        if file.endswith('.vcf') or file.endswith('.csv'):
            vcf_paths.append(f'{filepath}/{file}')
        else:
            continue

    # If there aren't any variant files in the 'temp' folder, notify the user through a flash message and log the
    # warning.
    if len(vcf_paths) == 0:
        flash('No data files have been uploaded. Please upload a .VCF or .CSV file or select a database to query.')
        logger.warning(f"variant_annotations_table: No VCF/CSV files detected in 'temp' directory: {filepath}")
        return

    # Log the number of variant files in temp directory.
    logger.info(f'variant_annotations_table: {len(vcf_paths)} variant files in {filepath}.')

    # Log the variant file names that will be processed.
    for file in vcf_paths:
        logger.debug(f"variant_annotations_table: Variant files detected: {file.split('/')[-1]}")

    # Get the filepath to the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))  # RS

    # Absolute path to database
    db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'databases', f'{db_name}.db'))  # RS

    # Make the databases folder if it does not exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        # Create a cursor to run SQL commands
        cursor = conn.cursor()
        # Log the filepath to the database.
        logger.debug(f'variant_annotations_table: Connected to database: {db_path}')

    # Raise an error if the database cannot be connected to. This may happen if the databse is locked.
    except Exception as e:
        # Log the error using the exceptions output.
        logger.error(f'variant_annotations_table: Could not connect to database: {db_path}. {e}', exc_info=True)
        # Notify the user that there was an issue creating/connectig to the databsae that they specified.
        flash(f'❌ {db_name}.db: Unable to connect to database.')

    # Create the variant_annotations table if it does not already exist. UNIQUE groups the variant_NC, variant_NM,
    # and variant_NP together to ensure that they can only appear once in the table together.
    try:
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
        logger.info('variant_annotations_table: Successfully prepared variant_annotations table to be populated by patients and their respective variants.')

    # Raise an exeption if the headers cannot be created.
    except Exception as e:
        logger.error(f'variant_annotations_table: Failed to create/check variant_annotations table: {e}', exc_info=True)
        # Notify the user of that there was an error while preparing the database.
        flash(f'❌ Error while preparing {db_name}.db.')
        conn.close()

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
            logger.error(f'variant_annotations_table: Failed to parse variants from {file}: {e}', exc_info=True)
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
                # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not overloaded with requests.
                time.sleep(0.5)

            # Raise an exception if fetch_vv is not working.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(f'variant_annotations_table: {file}: {variant}: Failed to execute fetch_vv function: {e}', exc_info=True)
                # Notify the User that VariantValidator cannot be queried.
                flash(f'{file}: {variant}: ❌ Could retrieve a response from VariantValidator. Variant not added to {db_name}.db.')
                continue

            # Try to accommodate for errors in the VariantValidator response.
            try:
                # If no response was received from fetch_vv or the length of the tuple is less than 5, log the error
                # and notify the User through the flask app. Then move onto the next varaiant.
                if not vv_response or len(vv_response) != 5:
                    logger.error(f'variant_annotations_table: {file}: {variant}: Failed to receive a response from fetch_vv.')
                    flash(f'{file}: {variant}: ❌ Irregular response from VariantValidator. Variant not added to {db_name}.db.')
                    continue

                # If the response received from fetch_vv is a string and not the tuple, log the error
                # and notify the User through the flask app. Then move onto the next varaiant.
                elif type(vv_response) == str:
                    flash(f'{file}: {vv_response}')
                    logger.error(f'variant_annotations_table: {file}: {vv_response}. Variant not added to {db_name}.db.')
                    continue

                else:
                    # Allocate the different values from fetch_vv to corresponding variables.
                    nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id = vv_response
                    # Log the output from fetch_vv
                    logger.info(f'{file}: {variant}: fetch_vv produced this output: {vv_response}')

            # Raise an exception if an error is not caught within the try statement.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(f'variant_annotations_table: {file}: {variant}: Unable to process the response from fetch_vv function: {e}', exc_info=True)
                # Notify the User that the variant cannot be queried through VariantValidator.
                flash(f'{file}: {variant}: ❌ Unable to query this variant through VariantValidator. Variant not added to {db_name}.db.')
                continue

            # clinvar.db is queried using clinvar_annotations() to retrieve the variant classification, associated
            # conditions, the star-ratings and the review statuses:

            # Log that clinvar.db is being queried.
            logger.info(f'variant_annotations_table: {file}: {variant}: Querying clinvar.db for {nc_variant}...')

            try:
                clinvar_response = clinvar_annotations(nc_variant, nm_variant)

            # Raise an exception if clinvar_annotations is not working.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(f'variant_annotations_table: {file}: {variant}: Failed to execute clinvar_annotations function: {e}', exc_info=True)
                # Notify the User that a variant summary record cannot be retrieved from clinvar.db.
                flash(f'{file}: {variant}: ❌ Unable to query clinvar.db. Variant not added to {db_name}.db.')
                continue

            # Try to accommodate for errors in the clinvar_annotations response.
            try:
                # If no response was received from clinvar_annotations or the function returned a blank response, log
                # the error and notify the User through the flask app. Then move onto the next varaiant.
                if not clinvar_response or len(clinvar_response) == 0:
                    logger.error(f'variant_annotations_table: {file}: {variant}: Variant summary record for {nc_variant} not found in clinvar.db.')
                    flash(f'{file}: {variant}: ❌ Variant summary record could not be found in clinvar.db. Variant not added to {db_name}.db.')
                    continue

                # If the response received from fetch_vv is a string and not the tuple, log the error and notify the
                # User through the flask app. Then move onto the next varaiant.
                elif type(clinvar_response) == str:
                    logger.error(f'variant_annotations_table: {file}: {clinvar_response}.')
                    flash(f'{file}: {clinvar_response}. Variant not added to {db_name}.db')
                    continue

                elif type(clinvar_response) == dict and len(clinvar_response) > 0:
                    classification = clinvar_response['classification']
                    conditions = clinvar_response['conditions']
                    stars = clinvar_response['stars']
                    review_status = clinvar_response['reviewstatus']

                    # The HGVS nomenclatures, gene symbol, HGNC ID and ClinVar annotations for each variant are added to
                    # the variant_annotations table. If the HGVS nomenclatures already exist in the table as a set,
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
                        logger.info(f'{file}: {variant}: Successfully populated variant_annotations table with ClinVar annotations.')

                    # Raise an exception if the patient name and variant could not be entered into the patient_variant
                    # table.
                    except Exception as e:
                        logger.error(f'Failed to populate variant_annotations table with {variant} from {patient_name} and {clinvar_response}: {e}', exc_info=True)
                        flash(f'{file}: {variant}: ❌ Variant could not be annotated. Variant not added to {db_name}.db.')
                        continue

            # Raise an exception if an error is not caught within the try statement.
            except Exception as e:
                # Log the error using the output from the exception.
                logger.error(
                    f'variant_annotations_table: {file}: {variant}: Unable to process the response from clinvar_annotations function: {e}',
                    exc_info=True)
                # Notify the User that the variant cannot be queried through VariantValidator.
                flash(
                    f'{file}: {variant}: ❌ Unable to query clinvar.db for this variant. Variant not added to {db_name}.db.')
                continue

    # Save (commit) changes and close connection
    conn.commit()
    conn.close()

    # A message is logged and shown to the user to indicate that the database was successfully created or updated.
    logger.info(f'Variant_annotations table in {db_name}.db created/updated successfully!')
    flash(f'{db_name}.db created/updated successfully!')


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