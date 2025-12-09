# First install the requests module if you haven't already:
# pip install requests

import re
import time
import json
import requests  # Import the 'requests' library to handle HTTP requests to the VariantValidator API
from flask import flash
from tools.utils.logger import logger
from tools.utils.error_handlers import request_status_codes, connection_error, json_decoder_error, regex_error

def fetch_vv(variant: str):
    """
    Using a variant in VCF format, query the VariantValidator REST API to retrieve genomic (NC_), transcript (NM_) and
    protein (NP_) descriptions in HGVS nomenclature, as well as the gene symbol and HGNC ID. All information will be
    stored in the clinvar.db database.
    The genomic and transcript HGVS descriptions are used to find the corresponding ClinVar variant summary record to
    annotate the variant.
    The gene symbol is used to support gene queries made by the User through the flask app.
    Requests are made to the /variantvalidator endpoint with MANE transcript preference.
    Currently fixed to use the GRCh38 reference genome.

    :params: variant: A variant in VCF format: {chromosome}-{position}-{ref}-{alt}
                E.g.: '17-45983420-G-T'

    :output: (nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id)
             A tuple consisting of the variant's genomic (NC_) description, transcript (NM_) description, protein (NP_)
             description, gene symbol, HGNC ID

       E.g.: ('NC_000011.10:g.2164285C>T', 'NM_000360.4:c.1442G>A, 'NP_000351.2:p.(Gly481Asp)', 'TH', '11782')
    """

    # Base URL for the VariantValidator API.
    # The endpoint specifies we’re working with the GRCh38 genome build.
    base_url_vv = "https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/"

    # Construct the full API request URL for each variant.
    # The 'mane' flag requests MANE transcript data if available.
    # The 'content-type' query specifies JSON output.
    url_vv = f"{base_url_vv}{variant}/mane?content-type=application%2Fjson"

    # Log the start of the query and the url.
    logger.info(f'{variant}: Retrieving genomic description, transcript description, protein description, gene symbol, '
                f'HGNC ID from VariantValidator @ {url_vv}')

    try:
        # For loop enables 5 attempts to query VariantValidator API, in case 408 or 429 request errors occur.
        for attempt in range(5):

            # Test the query.
            try:
                # Send an HTTP GET request to the API.
                response = requests.get(url_vv)

                # Raise an exception if the HTTP status code is not 200 (OK).
                response.raise_for_status()

                # The time module creates a 0.5s delay after each request to VariantValidator (VV), so that
                # VariantValidator is not overloaded with requests.
                time.sleep(0.5)

                # Access the API response like its a Python dictionary.
                data = response.json()

            # Catch any network or HTTP errors raised by 'requests'.
            except requests.exceptions.HTTPError as e:

                # Handle HTTP errors that need to be tried again, through the attempt loop.
                if e.response.status_code in [408, 429]:
                    error_message = request_status_codes(e, variant, url_vv, 'VariantValidator', attempt)

                    # Once received, return any flash messages to the function in database_functions.py, so that it can
                    # be appended to the file name. This will help the User understand where along the API request
                    # process failed.
                    if error_message:
                        return error_message

                    continue

                # Handle HTTP errors that do not need to be tried again.
                else:
                    error_message = request_status_codes(e, variant, url_vv, 'VariantValidator', attempt)

                # Return any flash messages to the function in database_functions.py, so that it can be appended to
                # the file name. This will help the User understand where along the API request process failed.
                return error_message

            # Raise an exception if there is a problem with the connection to the remote server.
            except requests.exceptions.ConnectionError as e:
                error_message = connection_error(e, variant, 'VariantValidator', url_vv)
                # Return any flash messages to the function in database_functions.py, so that it can be appended to
                # the file name. This will help the User understand where along the API request process failed.
                return error_message

            # Raise an exception if the response is not a JSON data type.
            except ValueError as e:
                error_message = json_decoder_error(e, variant, 'VariantValidator', url_vv)
                # Return any flash messages to the function in database_functions.py, so that it can be appended to
                # the file name. This will help the User understand where along the API request process failed.
                return error_message

            # Raise an exception if any other errors occurred.
            except Exception as e:
                # Log the error using the exception output message.
                logger.error(f'{variant}: Failed to receive a valid response from VariantValidator: {url_vv}.\n{e}', exc_info=True)
                # Return a flash message to the function in database_functions.py, so that it can be appended to the
                # file name. This will help the User understand where along the API request process failed.
                return f'{variant}: ❌ Failed to receive a valid response from VariantValidator.'

            # Handle unexpected null responses from the VariantValidator API.
            if data is None:
                # Log an error that VariantValidator did not return a result.
                logger.error(f'{variant}: VariantValidator did not return a result.')
                # Return the description so that the functions in database_functions.py can attach the description to
                # the file name where the queried variant comes from. This will help the User.
                return f'{variant}: ❌ VariantValidator did not return a response.'

            elif not isinstance(data, dict):
                # Log an error that VariantValidator did not return a dictionary.
                logger.error(f'{variant}: VariantValidator did not return a dictionary.')
                # Return the description so that the functions in database_functions.py can attach the description to
                # the file name where the queried variant comes from. This will help the User.
                return f'{variant}: ❌ VariantValidator did not return a response.'


            # VariantValidator returns this key, value combination when it cannot recognise the variant or it cannot
            # map it to a reference sequence.
            elif data.get('flag') == 'empty_result':

                # Log an error that VariantValidator returned an 'empty result'.
                logger.error(f'{variant}: VariantValidator did not recognise variant or could not map it to a '
                             f'reference sequence.')

                # Return the description so that the functions in database_functions.py can attach the description to
                # the file name where the queried variant comes from. This will help the User.
                return (f'{variant}: ❌ VariantValidator did not recognise variant or could not map it to a '
                        f'reference sequence.')

            # Report the warnings produced by VariantValidator.
            elif any(k.startswith("validation_warning_") for k in data):
                for key in data:

                    if key.startswith("validation_warning_"):
                        warning_block = data[key]
                        warnings = warning_block.get("validation_warnings", [])

                        if warnings:
                            return_warnings = '|'.join(warnings)

                            # Log the warnings produced by VariantValidator.
                            logger.debug(f'{variant}: VariantValidator warning: {return_warnings}')

                            # Return the warnings so that the functions in database_functions.py can attach the
                            # description to the file name where the queried variant comes from. This will help the
                            # User.
                            return f'{variant}: ❌ {return_warnings}. Variant not added to database.'

            # If a result was returned and does not contain an empty result flag or any warning from VariantValidator,
            # the response should be parsable.
            else:

                # Test that the keys where the information is stored, exist in the response.
                try:

                    # Extract the information from the response.
                    first_key = list(data.keys())[0]
                    nm_variant = data[first_key]['hgvs_transcript_variant']
                    nc_variant = data[first_key]['primary_assembly_loci']['grch38']['hgvs_genomic_description']
                    np_variant = data[first_key]['hgvs_predicted_protein_consequence']['tlr']
                    gene_symbol  = data[first_key]['gene_symbol']
                    hgnc_id = data[first_key]['gene_ids']['hgnc_id'].split(':')[1]

                # Raise an exception if the keys in the response are not iterable (specific to 'first_key' variable).
                except IndexError:

                    # Log the IndexError.
                    logger.error(f'{variant}: VariantValidator API returned an empty JSON.')
                    # Return the description so that the functions in database_functions.py can attach the description
                    # to the file name where the queried variant comes from. This will help the User.
                    return f'{variant}: ❌ No response received from VariantValidator.'

                # Raise an exception if any of the keys in the response are missing.
                except KeyError as e:
                    # KeyError message contains the missing key (from ChatGPT).
                    missing_key = e.args[0]
                    # Log the KeyError.
                    logger.error(f"{variant}: The {missing_key} key is missing from VariantValidator's JSON response. "
                                 f"Variant info could not be parsed from response.")
                    # Return the description so that the functions in database_functions.py can attach the description
                    # to the file name where the queried variant comes from. This will help the User.
                    return f'{variant}: ❌ Irregular response received from VariantValidator.'

                # Raise an exception if an error occurs while extracting information from the response.
                except Exception as e:

                    # Log the error using the exception output message.
                    logger.error(f'{variant}: Irregular response received from VariantValidator: {e}')
                    # Log the response from VariantValidator to help with debugging.
                    logger.debug(f'{variant}: Full response from VariantValidator:\n{json.dumps(data, indent=4)}')

                    # Return the description so that the functions in database_functions.py can attach the description
                    # to the file name where the queried variant comes from. This will help the User.
                    return f'{variant}: ❌ Irregular response received from VariantValidator.'

                # Checking the values from the dictionary.
                try:
                    # Use Regex to detect if anything but the HGVS genomic description was returned.
                    if not re.match('^NC_\d+.\d{1,2}:g[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]+>[ACGT]+|delins[ACGT]*(>[ACGT]+)*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', nc_variant):

                        # Log the error if anything but the HGVS genomic description was returned.
                        logger.error(f'{variant}: Genomic variant description from VariantValidator is not in valid '
                                     f'HGVS nomenclature. Variant not added to database.')
                        # Log what was extracted from the response to support debugging.
                        logger.debug(f'{variant}: Genomic variant description from VariantValidator: {nc_variant}')

                        # Return the description so that the functions in database_functions.py can attach the description to
                        # the file name where the queried variant comes from. This will help the User.
                        return (f'{variant}: ❌ Genomic variant description from VariantValidator is not in valid '
                                f'HGVS nomenclature.')

                    # Use Regex to detect if an anything but the HGVS transcript description was returned.
                    elif not re.match('^NM_\d+.\d{1,2}:c[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]+>[ACGT]+|delins[ACGT]*(>[ACGT]+)*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', nm_variant):

                        # Log the error if anything but the HGVS transcript description was returned.
                        logger.error(
                            f'{variant}: Transcript variant description from VariantValidator is not in valid '
                            f'HGVS nomenclature.')
                        # Log what was extracted from the response to support debugging.
                        logger.debug(f'{variant}: Transcript variant description from VariantValidator: {nm_variant}')

                        # Return the description so that the functions in database_functions.py can attach the description to
                        # the file name where the queried variant comes from. This will help the User.
                        return f'{variant}: ❌ Transcript variant description from VariantValidator is not in valid HGVS nomenclature.'

                    # Use Regex to detect if an anything but the HGVS protein description was returned.
                    elif not re.match('^NP_\d+.\d{1,2}:p[.](\()*(0)*(\?)*[*]*[?]*(\d*[a-zA-Z]{3})*(\d+[a-zA-Z]{3}(fs)*[*]*(\d+)*|\d*_[a-zA-Z]{3}\d+(ins)*[a-zA-Z]*|\d*_[a-zA-Z]{3}\d+(delins)*[a-zA-Z]*|\d+=|\d+[*]|ext\d*)*(\))*', np_variant):

                        # Log the warning if anything but the HGVS protein description was returned.
                        # A warning is logged because the protein description is not essential to this software package's
                        # functionality.
                        logger.warning(f'{variant}: Protein consequence from VariantValidator is not in valid HGVS nomenclature.')
                        # Log what was extracted from the response to support debugging.
                        logger.debug(f'{variant}: Protein consequence from VariantValidator: {np_variant}')

                        # Flash message sent to flask app UI to help the User understand the issue.
                        flash(f'{variant}: ⚠ Irregular protein consequence from VariantValidator.')

                        # This is what will be stored in the database, to help the User understand why the protein description
                        # is not there.
                        np_variant = 'Irregular NP_ description from VariantValidator'
                        break

                    # ChatGPT says C20orf202 is the longest gene symbol, which is 9 characters long. As gene symbols can
                    # consist of letters and numbers in different combinations, the length is the only way to scrutinise
                    # this response.
                    elif not re.match(r'^[A-Za-z0-9]{1,9}$', gene_symbol):

                        # Log a warning if the length of the gene symbol is not between 1 to 9 characters long.
                        # A warning is logged because the gene symbol is not essential to this software package's
                        # functionality.
                        logger.warning(f'{variant}: Gene symbol from VariantValidator is {len(gene_symbol)} long.')

                        # Log what was extracted from the response to support debugging.
                        logger.debug(f'{variant}: Gene symbol response from VariantValidator: {gene_symbol}')

                        # Flash message sent to flask app UI to help the User understand the issue.
                        flash(f'{variant}: ⚠ Irregular gene symbol from VariantValidator.')

                        # This is what will be stored in the database, to help the User understand why the gene symbol
                        # is not there.
                        gene_symbol = 'Irregular gene symbol from VariantValidator'
                        break

                    # The HGNC ID is a number but the response from VariantValidator is a string.
                    # Use Regex to ensure that the response consists of only numbers.
                    elif not re.match('^\d+', hgnc_id):

                        # Log a warning if the HGNC ID consists of anything but numbers.
                        # A warning is logged because the HGNC ID is not essential to this software package's functionality.
                        # However it is necessary when the User performs a gene query through the flask app.
                        logger.warning(
                            f'{variant}: HGNC ID from VariantValidator is not a number. '
                            f'Variant will not be returned from gene query.')

                        # Log what was extracted from the response to support debugging.
                        logger.debug(f'{variant}: HGNC ID response from VariantValidator: {hgnc_id}')

                        # Flash message sent to flask app UI to help the User understand the irregularity.
                        flash(f'{variant}: ⚠ Irregular HGNC ID from VariantValidator. '
                              f'Variant will not be returned from gene query.')

                        # This is what will be stored in the database, to help the User understand why the HGNC ID
                        # is not there.
                        hgnc_id = 'Irregular HGNC ID from VariantValidator'
                        break

                    # If the response from VariantValidator is all as it should be, break from the loop an continue.
                    else:
                        break

                # Raise an exception if any of the values parsed from the response.JSON() is not a string, including
                # None data types.
                except TypeError:
                    # Log the error if it occurs, using the exception output message.
                    logger.error(
                        f'{variant}: Some of the variant information from VariantValidator JSON are not strings.')
                    # Log a debug message describing the data type of the value from the JSON.
                    logger.debug(
                        f'{variant}: nc_variant= {type(nc_variant)}, nm_variant= {type(nm_variant)}, '
                        f'np_variant= {type(np_variant)}, gene_symbol= {type(gene_symbol)}, hgnc_id= {type(hgnc_id)}')
                    # Return the description so that the functions in database_functions.py can attach the attach the
                    # description to the file name where the queried variant comes from. This will help the User.
                    return f'{variant}: ❌ Irregular response from VariantValidator.'

                # Raise an exception if the Regex pattern is invalid (from ChatGPT).
                except re.error as e:
                    error_message = regex_error(e, variant)
                    return error_message

                # Raise an exception if any other error issue arises with the nc_variant, nm_variant, np_variant,
                # gene_symbol, hgnc_id.
                except Exception as e:
                    # Log the error if it occurs, using the exception output message.
                    logger.error(f'{variant}: Failed to query VariantValidator: {e}', exc_info=True)
                    # Return the description so that the functions in database_functions.py can attach the attach the
                    # description to the file name where the queried variant comes from. This will help the User.
                    return f'{variant}: Irregular response received from VariantValidator.'

        # Log that the test was passed.
        logger.info(f'{variant}: Successfully retrieved variant information from VariantValidator: '
                    f'{nc_variant}, {nm_variant}, {np_variant}, {gene_symbol}, {hgnc_id}')

        # Return the variant information to database_functions.py so that they can populate the clinvar.db database.
        return (nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id)

    except:
        # Log an error if VariantValidator was unable to return a response after 5 attempts.
        logger.error(f'{variant}: VariantValidator failed after 5 attempts.')
        # Return the description so that the functions in database_functions.py can attach the description to the file
        # name where the queried variant comes from. This will help the User.
        return f'{variant}: ❌ VariantValidator unavailable. Try again later.'


def get_mane_nc(variant: str):
    """
    Convert a variant search term in the flask app into its corresponding HGVS genomic description using the
    VariantValidator REST API. If the User provides a gene symbol this function recursively finds the HGVS genomic
    description. All c. variant queries are contextualised within the MANE select transcript before providing the
    genomic description.

    :params: variant: A variant described by the gene it is located in followed by the variant, in HGVS nomenclature.
                      The User can describe the gene using a RefSeq accession number, Ensemble transcript ID or gene
                      symbol.

                      ENST_transcript: Enembl transcript, consisting of 11 digits and a version number.
                                 E.g.: ENST00000252444.10:c.301G>A

                      RefSeq accession number: A chromosome or transcript accession number, prefixed by 'NC_' or NM_'.
                                         E.g.: NC_000019.10:g.11102774G>A
                                               NM_000527.3:c.301G>A
                                               NM_001406861.1:c.301G>A

                      Gene symbol: A sequence of letters and numbers that represent a gene. Some genes are represented
                                   by multiple gene symbols.
                                   E.g. LDLR:c.301G>A

    :output: nc_variant: The HGVS genomic description
                   E.g.: NC_000019.10:g.11102774G>A

    :command: variant = 'NC_000019.10:g.11102774G>A'
              get_mane_nc(variant)
    """

    # Base URL for the VariantValidator API.
    base_url_vv = "https://rest.variantvalidator.org/VariantValidator/"

    # Log the start of the query and the url.
    logger.info(f"User's variant query: {variant}. Querying VariantValidator for HGVS description...")

    # Check if a colon is in the variant description.
    if ':' not in variant:
        # Log the variant input that didn't contain a colon.
        logger.warning(f'Variant Query Error: User did not use a colon in their variant description: {variant}')
        # Show the User a message that will help them search for the variant.
        flash(f"⚠ Variant Query Error: ':' missing from variant query. {variant} does not work.")
        return

    try:
        # Get the transcript and genetic change from the input variant. Allow only one split.
        transcript, genetic_change = variant.split(':', 1)
        transcript = transcript.strip()
        genetic_change = genetic_change.strip()

        # Construct the full API request URL based on the type of search term.
        # first for Ensenmbl transcript
        # ENST - VariantValidator/variantvalidator_ensembl end point
        if transcript.startswith('ENST'):

            # If an Ensembl accession number was entered, check that the version number was provided.
            if '.' not in transcript:
                # Log that a version number was not provided.
                logger.warning(f"Variant Query Error: User did not provide a version number after the "
                               f"Ensembl accession number: {transcript}")
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: Please provide a version number after the Ensembl accession number. "
                      f"{transcript} does not work.")
                return

            # If an Ensembl accession number was entered, check that the version number is in fact a number.
            elif not re.match('^\d{1,3}$', transcript.split('.')[1]):
                # Log that a version number was not provided.
                logger.warning(f"Variant Query Error: User did not provide a valid version number after the "
                               f"Ensembl accession number: {transcript}")
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: Please provide a valid version number after the "
                      f"Ensembl accession number. {transcript} does not work.")
                return

            # If an Ensembl transcript was entered, make sure that it starts with 'ENST', followed by 11 digits and the
            # version number.
            elif not re.match(r'^ENST\d{11}.\d{1,3}', transcript):
                # Log the ensembl number that didn't work.
                logger.warning(f"Variant Query Error: User tried to search for a variant using an Ensembl transcript "
                               f"but there was something wrong with it: {transcript}")
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: Irregular ensembl transcript. {transcript} does not work.")
                return

            # ENST transcripts require a variant described with c. notation.
            elif not genetic_change.startswith('c.'):
                # Log the variant if it does not start with c. notation.
                logger.warning(f'Variant Query Error: ENST transcript entered without c. notation: {genetic_change}')
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ {transcript} must use c. notation. {genetic_change} does not work.")
                return

            # Variant must follow the pattern captured by this Regex code in order to find a corresponding variant in
            # the database.
            elif not re.match('^c[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]+>[ACGT]+|delins[ACGT]*(>[ACGT]+)*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', genetic_change):
                # Log the error if it does not conform with the Regex pattern.
                logger.warning(f'Variant Query Error: Irregular variant nomenclature: {genetic_change}')
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: Irregular variant nomenclature. {genetic_change} does not work.")
                return

            # If all of the conditions have been met, VariantValidator's Ensembl endpoint can be sent a request.
            else:
                ENST_variant = variant.replace(':', '%3A').replace('>', '%3E')
                url_vv = f"{base_url_vv}variantvalidator_ensembl/GRCh38/{ENST_variant}/mane_select?content-type=application%2Fjson"  # ENST - transcript


        # search by NM or LRG Ref Seq transcript - VariantValidator/variantvalidator end point
        elif transcript.startswith(('NM_', 'LRG_', 'NC_', 'NG_')):

            # If a RefSeq accession number was entered, check that the version number was provided.
            if not transcript.startswith('LRG_') and '.' not in transcript:
                # Log that a version number was not provided.
                logger.warning(f"Variant Query Error: User did not provide a version number after the "
                               f"RefSeq accession number: {variant}")
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: Please provide a version number after the RefSeq accession number. "
                      f"{transcript} does not work.")
                return

            # If a RefSeq accession number was entered, check that the version number is in fact a number.
            elif not transcript.startswith('LRG_') and not re.match(r'^\d{1,2}$', transcript.split('.')[1]):
                # Log that a version number was not provided.
                logger.warning(
                    f"Variant Query Error: User did not provide a valid version number after the "
                    f"RefSeq accession number: {transcript}")
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: Please provide a valid version number after the RefSeq accession number."
                      f" {transcript} does not work.")
                return

            # If a RefSeq accession number was entered, make sure that it starts with 'NM_', 'NC_' or 'NG_', followed
            # by an accession number and version number.
            elif not transcript.startswith('LRG_') and not re.match('^N[CMG]_\d+.\d{1,2}', transcript):
                # Log the RefSeq number that didn't work.
                logger.warning(
                    f"Variant Query Error: User tried to search for a variant using a RefSeq number but there was "
                    f"something wrong with it: {transcript}")
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: Irregular RefSeq transcript. {transcript} does not work.")
                return

            # 'NM', 'NG' and 'LRG' transcripts must be followed by variants denoted with c.
            elif transcript.startswith(('NM_', 'LRG_', 'NG_')) and not genetic_change.startswith('c.'):
                # Log the variant if it does not start with c. notation.
                logger.warning(
                    f"Variant Query Error: '{transcript}' accession number entered without c. notation: {variant}")
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: {transcript} must use c. notation. {genetic_change} does not work.")
                return

            # 'NC_' transcripts must be followed by variants denoted with g.
            elif transcript.startswith('NC_') and not genetic_change.startswith('g.'):
                # Log the variant if it does not start with g. notation.
                logger.warning(
                    f"Variant Query Error: '{transcript}' accession number entered without g. notation: {variant}")
                # Show the User a message that will help them search for the variant.
                flash(f"⚠ Variant Query Error: {transcript} must use g. notation. {variant} does not work.")
                return

            # Variant must follow the pattern captured by this Regex code in order to find a corresponding variant in
            # the database.
            elif not re.match('^[cg][.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]+>[ACGT]+|delins[ACGT]*(>[ACGT]+)*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', genetic_change):
                # Log the error if it does not conform with the Regex pattern.
                logger.warning(f'Irregular variant nomenclature: {variant}')
                # Show the User a message that will help them search for the variant.
                flash(f'⚠ Variant Query Error: Irregular variant nomenclature. {genetic_change} does not work.')
                return

            # If all of the conditions have been met, VariantValidator's variant description endpoint can be sent a
            # request.
            else:
                refseq_variant = variant.replace(':', '%3A').replace('>', '%3E')
                url_vv = f"{base_url_vv}variantvalidator/GRCh38/{refseq_variant}/mane_select?content-type=application%2Fjson"

        # search by gene symbol
        # Gene symbol - VariantValidator/tools/gene2transcripts_v2 end point
        elif not transcript.startswith('ENST') and '_' not in transcript and re.match(r'^[A-Za-z0-9]{1,10}$', transcript):
            gene_symbol, genetic_change = variant.split(':')
            url_vv = f"{base_url_vv}tools/gene2transcripts/{gene_symbol}?content-type=application%2Fjson"  # Gene symbol - gene

        # If the variant query input has not met any of the previous criteria, log a warning and notify the User.
        else:
            logger.warning(f'Variant Query Error: {variant}: Variant rejected because of invalid format.')
            flash(f"{variant}: ⚠ Variant Query Error: Unrecognized variant format. "
                  f"Please describe variant using HGVS nomenclature.")
            return

    # Raise an exception if the Regex pattern is invalid (from ChatGPT).
    except re.error as e:
        error_message = regex_error(e, variant)
        flash(f'Variant Query Error: {error_message}')
        return

    # Raise an exception if a URL could not be created.
    except Exception as e:
        # Log an error if a URL could not be made using the exception output message.
        logger.error(f'{variant}: Variant Query Error: Failed to construct a valid VariantValidator URL from {variant}: {e}')
        flash(f"{variant}: ❌ Variant Query Error: Unrecognized variant format. Please describe variant using HGVS nomenclature.")
        return

    # If the URL in the request sent to VariantValidator has not changed from a None data type, log a warning
    # and notify the User.
    if not url_vv:
        logger.error(f'{variant}: Variant Query Error: Variant rejected because of invalid format.')
        flash(f"{variant}: ⚠ Variant Query Error: Unrecognized variant format. Please describe variant using HGVS nomenclature.")
        return

    # Log the URL request sent to VariantValidator.
    else:
        logger.debug(f'{variant}: VariantValidator URL: {url_vv}')


    # ----- Make the API request and handle the response -----

    # For loop enables 5 attempts to query VariantValidator API, in case 408 or 429 request errors occur.
    for attempt in range(5):

        try:
            # Send an HTTP GET request to the API.
            response = requests.get(url_vv)

            # Raise an exception if the HTTP status code is not 200 (OK).
            response.raise_for_status()

            # The time module creates a 0.5s delay after each request to VariantValidator (VV), so that VV is not
            # overloaded with requests.
            time.sleep(0.5)

            # Parse the API response into a Python dictionary.
            data = response.json()

        # Catch any network or HTTP errors raised by 'requests'.
        except requests.exceptions.HTTPError as e:

            # Handle HTTP errors that need to be tried again.
            if e.response.status_code in [408, 429]:
                error_message = request_status_codes(e, variant, url_vv, 'VariantValidator', attempt)

                # Once received, display a flash message to the User that will help them understand why the API request
                # process failed.
                if error_message:
                    flash(f'Variant Query Error: {error_message}')
                    return

                continue

            # Handle HTTP errors that do not need to be tried again.
            else:
                error_message = request_status_codes(e, variant, url_vv, 'VariantValidator', attempt)

            # Display a flash message to the User that will help them understand why the API request process failed.
            flash(f'Variant Query Error: {error_message}')
            return

        # Raise an exception if there is a problem with the connection to the remote server.
        except requests.exceptions.ConnectionError as e:
            error_message = connection_error(e, variant, 'VariantValidator', url_vv)
            # Display a flash message to the User that will help them understand why the API request process failed.
            flash(f'Variant Query Error: {error_message}')
            return

        # Raise an exception if the response is not a JSON data type.
        except ValueError as e:
            error_message = json_decoder_error(e, variant, 'VariantValidator', url_vv)
            # Display a flash message to the User that will help them understand why the API request process failed.
            flash(f'Variant Query Error: {error_message}')
            return

        # Raise an exception if any other errors occurred.
        except Exception as e:
            # Log the error using the exception output message.
            logger.error(f'{variant}: Variant Query Error: Failed to receive a valid response from VariantValidator: {url_vv}. {e}')
            # Display a flash message to the User that will help them understand why the API request process failed.
            flash(f'{variant}: ❌ Variant Query Error: Failed to receive a valid response from VariantValidator.')
            return

        # Test the response from VariantValidator
        try:
            # Handle unexpected null responses from the VariantValidator API.
            if data is None:
                # Log an error that VariantValidator did not return a result.
                logger.error(f'{variant}: Variant Query Error: VariantValidator did not return a result.')
                # Display a flash message to the User that will help them understand why the API request process failed.
                flash(f'{variant}: ❌ Variant Query Error: VariantValidator did not return a response.')
                return

            elif not isinstance(data, dict):
                # Log an error that VariantValidator did not return a dictionary.
                logger.error(f'{variant}: Variant Query Error: VariantValidator did not return a dictionary.')
                # Display a flash message to the User that will help them understand why the API request process failed.
                flash(f'{variant}: ❌ Variant Query Error: VariantValidator did not return a response.')
                return

            # VariantValidator returns this key, value combination when it cannot recognise the variant or it cannot
            # map it to a reference sequence.
            elif data.get('flag') == 'empty_result':
                # Log an error that VariantValidator returned an 'empty result'.
                logger.error(
                    f'{variant}: Variant Query Error: VariantValidator did not recognise variant or '
                    f'could not map it to a reference sequence.')
                # Display a flash message to the User that will help them understand why the API request process failed.
                flash(
                    f'{variant}: ❌ Variant Query Error: VariantValidator did not recognise variant or '
                    f'could not map it to a reference sequence.')
                return

            # Report the warnings produced by VariantValidator.
            elif any(k.startswith("validation_warning_") for k in data): #print out any warnings that come up
                for key in data:

                    if key.startswith("validation_warning_"):
                        warning_block = data[key]
                        warnings = warning_block.get("validation_warnings", [])

                        if warnings:
                            flash(f'{variant}: ⚠ VariantValidator warnings:')

                            for warning in warnings:
                                # Log the warnings produced by VariantValidator.
                                logger.warnings(f'{variant}: ⚠ VariantValidator warning: {warning}')
                                # Relay the VariantValidator warnings to the User that will help them understand why
                                # the API request process failed.
                                flash(f"\t\t-{warning}")
                        return

            # If the variant started with 'ENST', 'NM_', 'LRG_' or 'NC_', parse the genomic description in HGVS
            # nomenclature from the response.
            elif variant.startswith(('ENST', 'NM_', 'LRG_', 'NC_')):
                try:
                    first_key = list(data.keys())[0]
                    nc_variant = data[first_key]['primary_assembly_loci']['grch38']['hgvs_genomic_description']

                    # Log that the User's input result in the corresponding genomic description.
                    logger.info(f'{variant}: Variant Query: HGVS genomic description retrieved from VariantValidator: '
                                f'{nc_variant}')
                    # Return the genomic description.
                    return nc_variant

                # Raise an exception if the keys in the response are not iterable (specific to 'first_key' variable).
                except IndexError:

                    # Log the IndexError.
                    logger.error(f'{variant}: Variant Query Error: VariantValidator API returned an empty dictionary.')
                    # Log the response from VariantValidator.
                    logger.debug(f'{variant}: Response from VariantValidator:\n{json.dumps(data, indent=4)}')
                    # Display a flash message to the User that will help them understand why the API request process
                    # failed.
                    flash(f'{variant}: ❌ Variant Query Error: No response received from VariantValidator.')
                    return

                # Raise an exception if any of the keys in the response are missing.
                except KeyError as e:
                    # KeyError message contains the missing key (from ChatGPT).
                    missing_key = e.args[0]
                    # Log the KeyError.
                    logger.error(f"{variant}: Variant Query Error: The {missing_key} key is missing from "
                                 f"VariantValidator's JSON response. Variant info could not be parsed from response.")
                    # Log the response from VariantValidator.
                    logger.debug(f'{variant}: Response from VariantValidator:\n{json.dumps(data, indent=4)}')
                    # Display a flash message to the User that will help them understand why the API request process
                    # failed.
                    flash(f'{variant}: ❌ Variant Query Error: Irregular response received from VariantValidator.')
                    return

                # Raise an exception if an error occurs while extracting information from the response.
                except Exception as e:

                    # Log the error using the exception output message.
                    logger.error(f'{variant}: Variant Query Error: Irregular response received from VariantValidator: '
                                 f'{e}')
                    # Log the response from VariantValidator to help with debugging.
                    logger.debug(f'{variant}: Variant Query Error: Full response from VariantValidator:'
                                 f'\n{json.dumps(data, indent=4)}')
                    # Display a flash message to the User that will help them understand why the API request process
                    # failed.
                    flash(f'{variant}: ❌ Variant Query Error: Irregular response received from VariantValidator.')
                    return

            # Return the HGVS genomic description if the User provided a gene symbol.
            elif not transcript.startswith('ENST') and '_' not in transcript and re.match(r'^[A-Za-z0-9]{1,10}$', transcript):

                # This method returns the NC_ accession number with the latest version if the User used a g. number.
                genomic_ref = ''

                if genetic_change.startswith("g."):

                    try:
                        # Find the MANE select transcript.
                        for transcript_record in data["transcripts"]:
                            if transcript_record["annotations"]["mane_select"]:

                                # Extract the NC_ accession number.
                                for item in transcript_record["genomic_spans"].keys():

                                    if item.startswith("NC_") and genomic_ref == '':

                                        genomic_ref = item

                                    # The 'genomic_ref' variable is changed to the NC_ accession number with the highest
                                    # version number.
                                    elif item.split('.')[0] == genomic_ref.split('.')[0]:

                                        if int(item.split('.')[-1]) > int(genomic_ref.split('.')[-1]):
                                            genomic_ref = item

                        # Log the output from querying VariantValidator using the gene symbol entered by the User.
                        logger.info(f'{variant}: HGVS genomic description successfully retrieved from {transcript} gene symbol: {genomic_ref}:{genetic_change}')

                        # Return the genomic description in HGVS nomenclature.
                        nc_variant = f'{genomic_ref}:{genetic_change}'
                        return nc_variant

                    # Raise an exception if any of the keys in the response are missing.
                    except KeyError as e:
                        # KeyError message contains the missing key (from ChatGPT).
                        missing_key = e.args[0]
                        # Log the KeyError.
                        logger.error(
                            f"{variant}: Variant Query Error: The {missing_key} key is missing from "
                            f"VariantValidator's JSON response. Variant info could not be parsed from response.")
                        # Log the response from VariantValidator.
                        logger.debug(f'{variant}: Response from VariantValidator:\n{json.dumps(data, indent=4)}')
                        # Display a flash message to the User that will help them understand why the API request process
                        # failed.
                        flash(f'{variant}: ❌ Variant Query Error: Irregular response received from VariantValidator.')
                        return

                    # Raise and exception if the genomic description could not be retrieved from the gene symbol.
                    except Exception as e:
                        # Log that the gene symbol failed to retrieve the genomic description.
                        logger.error(f'{variant}: Failed to retrieve genomic description: {transcript}: {e}')
                        # Log the response from VariantValidator.
                        logger.debug(f'{variant}: Response from VariantValidator:\n{json.dumps(data, indent=4)}')
                        # Notify the User that the gene symbol is what failed to retrieve a response.
                        flash(f'❌ {variant}: Variant Query Error: VariantValidator was unable to return a response '
                              f'using this gene symbol: {transcript}.')
                        return

                # This method recursively uses get_mane_nc to retrieve the genomic description by feeding it the MANE
                # select transcript along with the variant, if the variant was described using a c. number.
                elif genetic_change.startswith("c."):

                    try:
                        # Find the MANE select transcript.
                        for transcript_record in data["transcripts"]:
                            if transcript_record["annotations"]["mane_select"]:

                                # Extract the NM_ number of the MANE select transcript.
                                transcript_ref = transcript_record["reference"]

                        # Feed the MANE select and c. variant back into get_mane_nc
                        gs_variant = f'{transcript_ref}:{genetic_change}'
                        nc_variant = get_mane_nc(gs_variant)

                        # Log the output from querying VariantValidator using the gene symbol entered by the User.
                        logger.info(
                            f'{variant}: Variant Query: HGVS genomic description successfully retrieved from '
                            f'{transcript} gene symbol: {genomic_ref}:{genetic_change}')
                        # Return the genomic description in HGVS nomenclature.
                        return nc_variant

                    # Raise an exception if any of the keys in the response are missing.
                    except KeyError as e:
                        # KeyError message contains the missing key (from ChatGPT).
                        missing_key = e.args[0]
                        # Log the KeyError.
                        logger.error(
                            f"{variant}: Variant Query Error: The {missing_key} key is missing from "
                            f"VariantValidator's JSON response. Variant info could not be parsed from response.")
                        # Log the response from VariantValidator.
                        logger.debug(f'{variant}: Response from VariantValidator:\n{json.dumps(data, indent=4)}')
                        # Display a flash message to the User that will help them understand why the API request process
                        # failed.
                        flash(f'{variant}: ❌ Variant Query Error: Irregular response received from VariantValidator.')
                        return

                    # Raise and exception if the genomic description could not be retrieved from the gene symbol.
                    except Exception as e:
                        # Log that the gene symbol failed to retrieve the genomic description.
                        logger.error(f'{variant}: Failed to retrieve genomic description: {transcript}: {e}')
                        # Log the response from VariantValidator.
                        logger.debug(f'{variant}: Response from VariantValidator:\n{json.dumps(data, indent=4)}')
                        # Notify the User that the gene symbol is what failed to retrieve a response.
                        flash(
                            f'❌ {variant}: Variant Query Error: VariantValidator was unable to return a response using '
                            f'this gene symbol: {transcript}.')
                        return

            else:
                # Log that there was an issue with the gene symbol or accession number.
                logger.error(f'{variant}: VariantValidator was unable to recognise the gene symbol or accession number '
                             f'in the variant query, entered by the User: {transcript}')
                # Notify the User that there was an issue with the gene symbol or accession number.
                flash(f"❌ {variant}: Variant Query Error: VariantValidator was unable to recognise the gene symbol or "
                      f"accession number in your variant query: {transcript}")
                return

        # Raise an exception if there is an error in the response from VariantValidator.
        except Exception as e:
            # Log the error using the exception output message.
            logger.error(f'{variant}: There was something wrong with the response from VariantValidator: {e}')
            # Log the response from VariantValidator.
            logger.debug(f'{variant}: Response from VariantValidator:\n{json.dumps(data, indent=4)}')
            flash('❌ {variant}: Error: There was a problem with the response from VariantValidator.')
            return

#print(fetchVV('11-2164285-C-T'))

#Example usage
#if __name__ == "__main__":
 #   print(fetch_vv('11-2164285-C-T'))
  #  variant = "PARK7:c.515T>A"
   # output = get_mane_nc(variant)
    #print("Final Output:")
    #print(output)

#######
#tests:
# - NM_007262.5:c.515T>A
# - PARK7:g.7984999T>A (worked in script)
# - PARK:c.515T>A 
# -  "ENST00000338639.10:c.515T>A" - output: NC_000001.11:g.7984999T>A (correct) 
# ENST does not work with g. 
# - NC_000001.11:g.7984999T>A - output: NC_000001.11:g.7984999T>A
# - NM_007262.5:c.515T>A - output: NC_000001.11:g.7984999T>A
# NM does not work with g. 
# PARK7:c.515T>A - output: NM_007262.5:c.515T>A
# PARK7:g.7984999T>A - NC_000001.11:g.7984999T>A

