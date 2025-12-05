# First install the requests module if you haven't already:
# pip install requests

import re
import time
import json
import requests  # Import the 'requests' library to handle HTTP requests to the VariantValidator API
from flask import flash
from tools.utils.logger import logger
from tools.utils.error_handlers import request_status_codes, connection_error, remote_connection_error, json_decoder_error

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
    logger.info(f'{variant}: Retrieving genomic description, transcript description, protein description, gene symbol, HGNC ID from VariantValidator @ {url_vv}')

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
                logger.error(f'{variant}: Querying VariantValidator did not return a result.')

                # Return the description so that the functions in database_functions.py can attach the description to
                # the file name where the queried variant comes from. This will help the User.
                return f'{variant}: ❌ Querying VariantValidator did not return a response. Variant not added to database.'

            # VariantValidator returns this key, value combination when it cannot recognise the variant or it cannot
            # map it to a reference sequence.
            elif data.get('flag') == 'empty_result':

                # Log an error that VariantValidator returned an empty result.
                logger.error(f'{variant}: VariantValidator did not recognise variant or could not map it to a reference sequence.')

                # Return the description so that the functions in database_functions.py can attach the description to
                # the file name where the queried variant comes from. This will help the User.
                return f'{variant}: ❌ VariantValidator did not recognise variant or could not map it to a reference sequence.'

            # Report the warnings produced by VariantValidator.
            elif any(k.startswith("validation_warning_") for k in data):
                for key in data:

                    if key.startswith("validation_warning_"):
                        warning_block = data[key]
                        warnings = warning_block.get("validation_warnings", [])

                        if warnings:
                            return_warnings = '|'.join(warnings)

                            # Log the warnings produced by VariantValidator.
                            logger.debug(f'{variant}: ⚠ VariantValidator warning: {return_warnings}')

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
                    logger.error(f"{variant}: The {missing_key} key is missing from VariantValidator's JSON response. Variant info could not be parsed from response.")
                    # Return the description so that the functions in database_functions.py can attach the description
                    # to the file name where the queried variant comes from. This will help the User.
                    return f'{variant}: ❌ Awkward response received from VariantValidator.'

                # Raise an exception if an error occurs while extracting information from the response.
                except Exception as e:

                    # Log the error using the exception output message.
                    logger.error(f'{variant}: Awkward response received from VariantValidator: {e}')
                    # Log the response from VariantValidator to help with debugging.
                    logger.debug(f'{variant}: Full response from VariantValidator:\n{json.dumps(data, indent=4)}')

                    # Return the description so that the functions in database_functions.py can attach the description
                    # to the file name where the queried variant comes from. This will help the User.
                    return f'{variant}: ❌ Awkward response received from VariantValidator.'

                # Use Regex to detect if anything but the HGVS genomic description was returned.
                if not re.match('^NC_\d+.\d{1,2}:g[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]>[ACGT]|delins[ACGT]*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', nc_variant):

                    # Log the error if anything but the HGVS genomic description was returned.
                    logger.error(f'{variant}: Genomic variant description from VariantValidator is not in valid HGVS nomenclature. Variant not added to database.')
                    # Log what was extracted from the response to support debugging.
                    logger.debug(f'{variant}: Genomic variant description from VariantValidator: {nc_variant}')

                    # Return the description so that the functions in database_functions.py can attach the description to
                    # the file name where the queried variant comes from. This will help the User.
                    return f'{variant}: ❌ Genomic variant description from VariantValidator is not in valid HGVS nomenclature.'

                # Use Regex to detect if an anything but the HGVS transcript description was returned.
                elif not re.match('^NM_\d+.\d{1,2}:c[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]>[ACGT]|delins[ACGT]*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', nm_variant):

                    # Log the error if anything but the HGVS transcript description was returned.
                    logger.error(f'{variant}: Transcript variant description from VariantValidator is not in valid HGVS nomenclature.')
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
                    np_variant = 'Irregular response from VariantValidator'
                    break

                # ChatGPT says C20orf202 is the longest gene symbol, which is 9 characters long. As gene symbols can
                # consist of letters and numbers in different combinations, the length is the only way to scrutinise
                # this response.
                elif len(gene_symbol) not in range(1, 10):

                    # Log a warning if the length of the gene symbol is not between 1 to 10 characters long.
                    # A warning is logged because the gene symbol is not essential to this software package's
                    # functionality.
                    logger.warning(f'{variant}: Gene symbol from VariantValidator is {len(gene_symbol)} long.')

                    # Log what was extracted from the response to support debugging.
                    logger.debug(f'{variant}: Gene symbol response from VariantValidator: {gene_symbol}')

                    # Flash message sent to flask app UI to help the User understand the issue.
                    flash(f'{variant}: ⚠ Irregular gene symbol from VariantValidator.')

                    # This is what will be stored in the database, to help the User understand why the gene symbol
                    # is not there.
                    gene_symbol = 'Irregular response from VariantValidator'
                    break

                # The HGNC ID is a number but the response from VariantValidator is a string.
                # Use Regex to ensure that the response consists of only numbers.
                elif not re.match('^\d+', hgnc_id):

                    # Log a warning if the HGNC ID consists of anything but numbers.
                    # A warning is logged because the HGNC ID is not essential to this software package's functionality.
                    # However it is necessary when the User performs a gene query through the flask app.
                    logger.warning(f'{variant}: HGNC ID from VariantValidator is not a number. Variant will not be returned from gene query.')

                    # Log what was extracted from the response to support debugging.
                    logger.debug(f'{variant}: HGNC ID response from VariantValidator: {hgnc_id}')

                    # Flash message sent to flask app UI to help the User understand the irregularity.
                    flash(f'{variant}: ⚠ Irregular HGNC ID from VariantValidator. Variant will not be returned from gene query.')

                    # This is what will be stored in the database, to help the User understand why the HGNC ID
                    # is not there.
                    hgnc_id = 'Irregular response from VariantValidator'
                    break

                # If the response from VariantValidator is all as it should be, break from the loop an continue.
                else:
                    break

            # Raise an exception if an error occurs while querying VariantValidator.
            except Exception as e :

                # Log the error if it occurs, using the exception output message.
                logger.error(f'{variant}: Failed to query VariantValidator: {e}', exc_info=True)

                # Return the description so that the functions in database_functions.py can attach the attach the
                # description to the file name where the queried variant comes from. This will help the User.
                return f'{variant}: Failed to query VariantValidator.'

        # Log that the test was passed.
        logger.info(f'{variant}: Successfully retrieved variant information from VariantValidator')

        # Return the variant information to database_functions.py so that they can populate the clinvar.db
        # database.
        return (nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id)

    except:
        # Log an error if VariantValidator was unable to return a response after 5 attempts.
        logger.error(f'{variant}: VariantValidator failed after 5 attempts.')

        # Return the description so that the functions in database_functions.py can attach the description to the file
        # name where the queried variant comes from. This will help the User.
        return f'{variant}: ❌ VariantValidator unavailable. Try again later.'


def get_mane_nc(variant: str):
    """
    Convert a search term identifier to its corresponding NC_ identifier
    using the VariantValidator REST API.

    Parameters
    ----------
    ENSG genomic ID : str, e.g. 'ENSG00000130164:c.301G>A' #this doesn't work 
    ENST_transcript : str, e.g. 'ENST00000252444.10:c.301G>A' #does this need converting to g.
    Ref Seq transcript ID : str, e.g. 'NM_000527.3:c.301G>A' or 'NM_001406861.1:c.301G>A' or 'LDLR:c.301G>A'
    Gene symbol with change : str, e.g. 'LDLR:c.301G>A' 

    Returns
    -------
    NC_ genomic ID : str, e.g. 'NC_000019.10:g.11102774G>A'
    """

    # Base URL for the VariantValidator API.
    base_url_vv = "https://rest.variantvalidator.org/VariantValidator/"

    # Log the start of the query and the url.
    logger.info(f"User's variant query: {variant}. Querying VariantValidator for HGVS description...")

    try:
        # Get the transcript and genetic change from the input variant.
        transcript, genetic_change = variant.split(':')

        # Construct the full API request URL based on the type of search term.
        # first for ensenmbl transcript
        # ENST - VariantValidator/variantvalidator_ensembl end point
        if variant.startswith('ENST'):

            if genetic_change.startswith('c.'):
                ENST_variant = variant.replace(':', '%3A').replace('>', '%3E')
                url_vv = f"{base_url_vv}variantvalidator_ensembl/GRCh38/{ENST_variant}/mane_select?content-type=application%2Fjson"  # ENST - transcript

            else:
                flash(f"⚠ {transcript} must use c. notation. {variant} does not work.")
                logger.warning(f'ENST transcript entered without c. notation: {variant}')

        # search by NM or LRG Ref Seq transcript - VariantValidator/variantvalidator end point
        elif variant.startswith(('NM_', 'LRG_', 'NC_', 'NG_')):

            if transcript.startswith(('NM_', 'LRG_', 'NG_')) and not genetic_change.startswith('c.'):
                logger.warning(f"'{transcript[:3]}' accession number entered without c. notation: {variant}")
                flash(f"⚠ {transcript} must use c. notation. {variant} does not work.")

            elif transcript.startswith('NC_') and not genetic_change.startswith('g.'):
                logger.warning(f"'{variant[:3]}' accession number entered without g. notation: {variant}")
                flash(f"⚠ {transcript} must use g. notation. {variant} does not work.")

            else:
                refseq_variant = variant.replace(':', '%3A').replace('>', '%3E')
                url_vv = f"{base_url_vv}variantvalidator/GRCh38/{refseq_variant}/mane_select?content-type=application%2Fjson"

        # search by gene symbol
        # Gene symbol - VariantValidator/tools/gene2transcripts_v2 end point
        elif not transcript.startswith('ENST') and '_' not in transcript and len(transcript) < 10:
            gene_symbol, genetic_change = variant.split(':')
            url_vv = f"{base_url_vv}tools/gene2transcripts/{gene_symbol}?content-type=application%2Fjson"  # Gene symbol - gene

        else:
            logger.error(f'{variant}: Variant rejected because of invalid format.')
            flash(f"{variant}: ❌ Unrecognized variant format. Please describe variant using HGVS nomenclature.")

        logger.debug(f'{variant}: VariantValidator URL: {url_vv}')

    # Raise an exception if a URL could not be created.
    except Exception as e:
        # Log an error if a URL could not be made using the exception output message.
        logger.error(f'{variant}: Failed to construct a valid VariantValidator URL from {transcript}: {e}', exc_info=True)

    # ----- Make the API request and handle the response -----

    # For loop enables 5 attempts to query VariantValidator API, in case 408 or 429 request errors occur.
    for attempt in range(5):

        try:
            # Send an HTTP GET request to the API.
            response = requests.get(url_vv)

            # Raise an exception if the HTTP status code is not 200 (OK).
            response.raise_for_status()

            # The time module creates a 0.5s delay after each request to VariantValidator (VV), so that VV is not overloaded with requests.
            time.sleep(0.5)

            # Parse the API response into a Python dictionary.
            data = response.json()

        # Catch any network or HTTP errors raised by 'requests'.
        except requests.exceptions.HTTPError as e:

            # Handle HTTP errors that need to be tried again.
            if e.response.status_code in [408, 429]:
                error_message = request_status_codes(e, variant, url_vv, 'VariantValidator', attempt)

                # Once received, return any flash messages to the function in database_functions.py, so that it can
                # be appended to the file name. This will help the User understand where along the API request process
                # failed.
                if error_message:
                    return error_message

                continue

            # Handle HTTP errors that do not need to be tried again.
            else:
                error_message = request_status_codes(e, variant, url_vv, 'VariantValidator', attempt)

            # Return any flash messages to the function in database_functions.py, so that it can be appended to the
            # file name. This will help the User understand where along the API request process failed.
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
            logger.error(f'{variant}: Failed to receive a valid response from VariantValidator: {url_vv}. {e}')

            # Return a flash message to the function in database_functions.py, so that it can be appended to the
            # file name. This will help the User understand where along the API request process failed.
            return f'{variant}: ❌ Failed to receive a valid response from VariantValidator.'

        # Test the response from VariantValidator
        try:

            # VariantValidator returns this key, value combination when it cannot recognise the variant or it cannot
            # map it to a reference sequence.
            if data.get('flag') == 'empty_result':

                # Log an error that VariantValidator returned an empty result.
                logger.error(f'VariantValidator returned empty_result from querying {variant}')

                # Notify the User that there was an error while querying VariantValidator.
                flash(f'❌ {variant}: Error: VariantValidator did not recognise variant or could not map it to a reference sequence.')
                break

            # Handle unexpected null responses from the VariantValidator API.
            if data is None:

                # Log an error that VariantValidator did not return a result.
                logger.error(f'VariantValidator did not return a response from querying {variant}')

                # Notify the User that there was an error while querying VariantValidator.
                flash(f"❌ {variant}: Error: VariantValidator did not return a response.")
                break

            # Report the warnings produced by VariantValidator.
            elif any(k.startswith("validation_warning_") for k in data): #print out any warnings that come up
                for key in data:

                    if key.startswith("validation_warning_"):
                        warning_block = data[key]
                        warnings = warning_block.get("validation_warnings", [])

                        if warnings:
                            flash(f'⚠ {variant}: VariantValidator warnings:')

                            for warning in warnings:

                                # Display the warning from VariantValidator to the User
                                flash(f"\t-{warning}")
                                # Log the warnings produced by VariantValidator.
                                logger.debug(f'{variant}: VariantValidator warning: {warning}')
                break

            # If the variant started with 'ENST', 'NM_', 'LRG_' or 'NC_', parse the genomic description in HGVS
            # nomenclature from the response.
            elif variant.startswith(('ENST', 'NM_', 'LRG_', 'NC_')):
                first_key = list(data.keys())[0]
                nc_variant = data[first_key]['primary_assembly_loci']['grch38']['hgvs_genomic_description']

                # Log that the User's input result in the corresponding genomic description.
                logger.info(f'{variant}: HGVS genomic description retrieved from VariantValidator: {nc_variant}')
                # Return the genomic description.
                return nc_variant

            # Return the HGVS genomic description if the User provided a gene symbol.
            elif not transcript.startswith('ENST') and '_' not in transcript and len(transcript) < 11:

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

                                        if item.split('.')[-1] > genomic_ref.split('.')[-1]:
                                            genomic_ref = item

                        # Log the output from querying VariantValidator using the gene symbol entered by the User.
                        logger.info(f'{variant}: HGVS genomic description successfully retrieved from {transcript} gene symbol: {genomic_ref}:{genetic_change}')

                        # Return the genomic description in HGVS nomenclature.
                        return f'{genomic_ref}:{genetic_change}'

                    # Raise and exception if the genomic description could not be retrieved from the gene symbol.
                    except Exception as e:
                        # Log that the gene symbol failed to retrieve the genomic description.
                        logger.error(f'{variant}: Failed to retrieve genomic description from gene symbol: {transcript}: {e}', exc_info=True)
                        # Notify the User that the gene symbol is what failed to retrieve a response.
                        flash(f'❌ {variant}: Error: VariantValidator was unable to return a response using this gene symbol: {transcript}.')

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
                        logger.info(f'{variant}: HGVS genomic description successfully retrieved from {transcript} gene symbol: {genomic_ref}:{genetic_change}')
                        # Return the genomic description in HGVS nomenclature.
                        return nc_variant

                    # Raise and exception if the genomic description could not be retrieved from the gene symbol.
                    except Exception as e:
                        # Log that the gene symbol failed to retrieve the genomic description.
                        logger.error(f'{variant}: Failed to retrieve genomic description from MANE select of {transcript}: {e}', exc_info=True)
                        # Notify the User that the gene symbol is what failed to retrieve a response.
                        flash(f"❌ {variant}: VariantValidator was unable to return a response using {transcript}'s MANE select.")

                else:
                    # Log that there was an issue with the variant denotation.
                    logger.error(f'{variant}: User did not enter a c. or g. after the colon of their variant query.')
                    # Notify the User that there was an issue with the variant denotation.
                    flash(f'❌ {variant}: Error: Please enter a c. or g. number after the colon in your query.')
                    break

            else:
                # Log that there was an issue with the gene symbol or accession number.
                logger.error(f'{variant}: VariantValidator was unable to recognise the gene symbol or accession number in the variant query, entered by the User: {transcript}')
                # Notify the User that there was an issue with the gene symbol or accession number.
                flash(f"❌ {variant}: Error: VariantValidator was unable to recognise the gene symbol or accession number in your variant query: {transcript}")
                break

        # Raise an exception if there is an error in the response from VariantValidator.
        except Exception as e:
            # Log the error using the exception output message.
            logger.error(f'{variant}: Response from VariantValidator was problematic: {e}', exc_info=True)
            # Log the response from VariantValidator.
            logger.debug(f'{variant}: Response from VariantValidator:\n{json.dumps(data, indent=4)}')
            flash('❌ {variant}: Error: There was a problem with the response from VariantValidator.')

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

