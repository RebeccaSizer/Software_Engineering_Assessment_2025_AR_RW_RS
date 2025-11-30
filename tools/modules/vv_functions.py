# First install the requests module if you haven't already:
# pip install requests

import re
import time
import json
import requests  # Import the 'requests' library to handle HTTP requests to the VariantValidator API
from flask import flash
from tools.utils.logger import logger

def fetch_vv(variant: str):
    '''
    Using a variant in VCF format, query the VariantValidator REST API to retrieve genomic (NC_), transcript (NM_) and
    protein (NP_) descriptions in HGVS nomenclature, as well as the gene symbol and HGNC ID. All identifiers will be
    stored in the clinvar.db database.
    The genomic and transcript HGVS descriptions are used to find the corresponding ClinVar variant summary record to
    annotate the variant.
    The gene symbol is used to support gene queries made by the user through the flask app.
    Requests are made to the /variantvalidator endpoint with MANE transcript preference.
    Currently fixed to use the GRCh38 reference genome.

    :params: variant: A variant in VCF format: {chromosome}-{position}-{ref}-{alt}
                E.g.: '17-45983420-G-T'

    :output: (nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id)
             A tuple consisting of the variant's genomic (NC_) description, transcript (NM_) description, protein (NP_)
             description, gene symbol, HGNC ID

       E.g.: ('NC_000011.10:g.2164285C>T', 'NM_000360.4:c.1442G>A, 'NP_000351.2:p.(Gly481Asp)', 'TH', '11782')
    '''

    # Base URL for the VariantValidator API.
    # The endpoint specifies we’re working with the GRCh38 genome build.
    base_url_vv = "https://rest.variantvalidator.org/VariantValidator/variantvalidator/GRCh38/"

    # Construct the full API request URL for each variant.
    # The 'mane' flag requests MANE transcript data if available.
    # The 'content-type' query specifies JSON output.
    url_vv = f"{base_url_vv}{variant}/mane?content-type=application%2Fjson"

    logger.info(f'Querying VariantValidator request for: {variant}...')

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
            print(data)

            if data['flag'] == 'empty_result':

                logger.warning(f'{variant} Querying VariantValidator returned an empty result.')
                return f'{variant}: ⚠ Querying VariantValidator returned an empty result.'

            elif data is None:

                logger.warning(f'{variant}: Querying VariantValidator did not return a result.')
                return f'{variant}: ⚠ Querying VariantValidator did not return a result.'

            else:
                try:
                    nm_variant = list(data.keys())[0]
                    nc_variant = data[nm_variant]['primary_assembly_loci']['grch38']['hgvs_genomic_description']
                    np_variant = data[nm_variant]['hgvs_predicted_protein_consequence']['tlr']
                    gene_symbol  = data[nm_variant]['gene_symbol']
                    hgnc_id = data[nm_variant]['gene_ids']['hgnc_id'].split(':')[1]

                except Exception as e:
                    logger.error(f'{variant}: Awkward response received from VariantValidator: {e}', exc_info=True)
                    logger.debug(f'{variant}: Full response from VariantValidator:\n{json.dumps(data, indent=4)}')
                    return f'{variant}: Awkward response received from VariantValidator.'

            if not re.match('^NC_\d+.\d{1,2}:g[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]>[ACGT]|delins[ACGT]*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', nc_variant):
                logger.error(f'{variant}: Genomic variant description from VariantValidator is not in valid HGVS nomenclature. Variant not added to database.')
                logger.debug(f'{variant}: Genomic variant description from VariantValidator: {nc_variant}')
                return f'{variant}: Genomic variant description from VariantValidator is not in valid HGVS nomenclature. Variant not added to database.'

            # Ensure that the input transcript variant is in the appropriate HGVS nomenclature.
            elif not re.match('^NM_\d+.\d{1,2}:c[.]([-]*\d+|[-]*\d+_[-]*\d+|[-]*\d+[+-]\d+)([ACGT]>[ACGT]|delins[ACGT]*|del[ACGT]*|ins[ACGT]*|dup[ACGT]*|inv[ACGT]*)', nm_variant):
                logger.error(f'{variant}: Transcript variant description from VariantValidator is not in valid HGVS nomenclature. Variant not added to database.')
                logger.debug(f'{variant}: Transcript variant description from VariantValidator: {nm_variant}')
                return f'{variant}: Transcript variant description from VariantValidator is not in valid HGVS nomenclature. Variant not added to database.'

            elif not re.match('^NP_\d+.\d{1,2}:p[.](\()*(0)*(\?)*[*]*[?]*(\d*[a-zA-Z]{3})*(\d+[a-zA-Z]{3}(fs)*[*]*(\d+)*|\d*_[a-zA-Z]{3}\d+(ins)*[a-zA-Z]*|\d*_[a-zA-Z]{3}\d+(delins)*[a-zA-Z]*|\d+=|\d+[*]|ext\d*)*(\))*', np_variant):
                logger.warning(f'{variant}: Protein consequence from VariantValidator is not in valid HGVS nomenclature.')
                logger.debug(f'{variant}: Protein consequence from VariantValidator: {np_variant}')
                flash(f'{variant}: Irregular protein consequence from VariantValidator.')
                np_variant = 'Irregular response from VariantValidator'

            # ChatGPT says C20orf202 is the longest gene symbol.
            elif len(gene_symbol) not in range(1, 10):
                logger.warning(f'{variant}: Gene symbol from VariantValidator is {len(gene_symbol)} long.')
                logger.debug(f'{variant}: Gene symbol response from VariantValidator: {gene_symbol}')
                flash(f'{variant}: Irregular gene symbol from VariantValidator.')
                gene_symbol = 'Irregular response from VariantValidator'

            elif not re.match('^\d+', hgnc_id):
                logger.warning(f'{variant}: HGNC ID from VariantValidator is not a number.')
                logger.debug(f'{variant}: HGNC ID response from VariantValidator: {hgnc_id}')
                flash(f'{variant}: Irregular HGNC ID from VariantValidator. Variant will not be returned from gene query.')
                hgnc_id = 'Irregular response from VariantValidator'

            logger.info(f'{variant}: Successfully retrieved variant identifiers from VariantValidator')
            return (nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id)


        # Catch any network or HTTP errors raised by 'requests'.
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                time.sleep(2 ** attempt)  # exponential backoff
                logger.warning(f'{variant}: {e}')
                logger.info(f'Querying VariantValidator again. Attempt: {attempt + 2}/5')
                continue

    logger.error(f'{variant}: VariantValidator failed after 5 attempts.')
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
    base_url_VV = "https://rest.variantvalidator.org/VariantValidator/"

    # Construct the full API request URL based on the type of search term.
    # first for ensenmbl transcript
    # ENST - VariantValidator/variantvalidator_ensembl end point
    if variant.startswith('ENST'):
        transcript, genetic_change = variant.split(':')

        if genetic_change.startswith('c.'):
            ENST_variant = variant.replace(':', '%3A').replace('>', '%3E')
            url_vv = f"{base_url_VV}variantvalidator_ensembl/GRCh38/{ENST_variant}/mane_select?content-type=application%2Fjson"  # ENST - transcript

        else:
            print(f"Error: ENST variant must use c. notation: {variant}")
            return 'error_enst_not_c' 

    # search by NM or LRG Ref Seq transcript - VariantValidator/variantvalidator end point
    elif variant.startswith(('NM_', 'LRG_', 'NC_', 'NG_')):
        transcript, genetic_change = variant.split(':')

        if genetic_change.startswith('c.') and variant.startswith(('NM_', 'LRG_', 'NG_')):
            refseq_variant = variant.replace(':', '%3A').replace('>', '%3E')
            url_vv = f"{base_url_VV}variantvalidator/GRCh38/{refseq_variant}/mane_select?content-type=application%2Fjson"  # RefSeq - transcript
        
        elif genetic_change.startswith('g.') and variant.startswith('NC_'):
            refseq_variant = variant.replace(':', '%3A').replace('>', '%3E')
            url_vv = f"{base_url_VV}variantvalidator/GRCh38/{refseq_variant}/mane_select?content-type=application%2Fjson"  # RefSeq - genomic
        
        else:
            print(f"Error: RefSeq variant must use c. notation: {variant}")
            return 'error_refseq_not_c'

    # search by gene symbol
    # Gene symbol - VariantValidator/tools/gene2transcripts_v2 end point
    elif re.match(r'^[A-Za-z0-9_-]+:', variant):
        gene_symbol, genetic_change = variant.split(':')
        url_vv = f"{base_url_VV}tools/gene2transcripts/{gene_symbol}?content-type=application%2Fjson"  # Gene symbol - gene

    else:
        print(f"Error: Unrecognized variant format: {variant}")
        return 'error_unrecognized_format'

    print(f"Requesting URL: {url_vv}")

    # ----- Make the API request and handle the response -----

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
            #print(data)

            if data.get('flag') == 'empty_result': #retrives the value for key 'flag'

                print(f'{variant} returned an empty result from VariantValidator.')
                return 'empty_result'

            elif data is None: #checks is data is empty 

                print(f"Warning: fetchVV returned None for variant: {variant}")
                return 'null'

            elif any(k.startswith("validation_warning_") for k in data): #print out any warnings that come up 
                for key in data:

                    if key.startswith("validation_warning_"):
                        warning_block = data[key]
                        warnings = warning_block.get("validation_warnings", [])

                        if warnings:
                            print(f"Validation warnings from {key}:")

                            for w in warnings:
                                print(f" - {w}")

            elif variant.startswith(('ENS', 'NM_', 'LRG_', 'NC_')):
                nm_variant = list(data.keys())[0]
                nc_variant = data[nm_variant]['primary_assembly_loci']['grch38']['hgvs_genomic_description']
                return nc_variant

            elif re.match(r'^[A-Za-z0-9_-]+:', variant):
                nc_number = None
                transcripts = []

                for tx in data["transcripts"]: #this loops through all the transcripts that are in the API output in trancripts 
                    if tx["annotations"].get("mane_select") is True:
                        if genetic_change.startswith("g."): #find the transcripts that have mane_select = true
                            transcripts.append(tx["genomic_spans"])
                            print(tx.keys()) #add the genomics_span dictionary from these transcripts into a list

                        # Pick NC number from the first MANE transcript
                            for tx in transcripts:
                                for nc_number in tx.keys():
                                    if nc_number.endswith(".11"):
                                        nc_number = nc_number 
                                        break           # breaks inner loop
                                    else:
                                    # inner loop didn't break → no .11 found in this tx
                                        continue            # go to next tx
                                    break

                            return f"{nc_number}:{genetic_change}"
                    
                        if genetic_change.startswith("c."):
                            nm_number = tx["reference"]

                            if nm_number:
                                variant_nm = f"{nm_number}:{genetic_change}"
                                nc_variant = get_mane_nc(variant_nm)
                                return nc_variant

                            else:
                                return f"No nm_number found"

            else:
                print(f"Error: Unrecognized variant format after data retrieval: {variant}")
                return 'error_unrecognized_format_after_retrieval'


        # Catch any network or HTTP errors raised by 'requests'.
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                time.sleep(2 ** attempt)  # exponential backoff
                print(e)
                print('Trying again...')
                print(f'Attempt: {attempt + 2}/5')
                continue

#print(fetchVV('11-2164285-C-T'))

#Example usage
if __name__ == "__main__":
    print(fetch_vv('11-2164285-C-T'))
    variant = "PARK7:c.515T>A"
    output = get_mane_nc(variant)
    print("Final Output:")
    print(output)

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

