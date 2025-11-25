import requests 
import time
import re

def get_mane_nc(search_term: str):
    """
    Convert a search term identifier to its corresponding NC_ identifier
    using the VariantValidator REST API.

    Parameters
    ----------
    ENSG genomic ID : str, e.g. 'ENSG00000130164:c.301G>A'
    ENST_transcript : str, e.g. 'ENST00000252444.10:c.301G>A' #needs converting to g.
    Ref Seq transcript ID : str, e.g. 'NM_000527.3:c.301G>A' or 'NM_001406861.1:c.301G>A' or 'LDLR:c.301G>A'
    Gene symbol with change : str, e.g. 'LDLR:c.301G>A'

    Returns 
    ------- 
    NC_ genomic ID : str, e.g. 'NC_000019.10:g.11102774G>A'
    """

    # Base URL for the VariantValidator API.
    base_url_VV = "https://rest.variantvalidator.org/VariantValidator/"

    # Construct the full API request URL based on the type of search term.
    #first for ensenmbl transcript
    if variant.startswith('ENST'):
        ENST_variant = variant.replace(':', '%3A').replace('>', '%3E')
        url_vv = f"{base_url_VV}variantvalidator_ensembl/GRCh38/{variant}/mane_select?content-type=application%2Fjson" #ENST - transcript  

    #search by NM or LRG Ref Seq transcript
    elif variant.startswith(('NM_', 'LRG_', 'NC_')):
        url_vv = f"{base_url_VV}variantvalidator/hg38/{variant}/mane_select?content-type=application%2Fjson" #RefSeq - transcript

    #search by gene symbol
    elif re.match(r'^[A-Za-z0-9_-]+:', variant):
        gene_symbol, genetic_change = variant.split(':')
        url_vv = f"{base_url_VV}tools/gene2transcripts/{gene_symbol}?content-type=application%2Fjson" #ENSG - gene

    else:
        print(f"Error: Unrecognized variant format: {variant}")
        return 'error_unrecognized_format' 
    
    print(f"Requesting URL: {url_vv}")

    # ----- Make the API request and handle the response -----

    try:
        # Send an HTTP GET request to the API.
        response = requests.get(url_vv)

        # Raise an exception if the HTTP status code is not 200 (OK).
        response.raise_for_status()

        # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not overloaded with requests.
        time.sleep(0.5)

        # Parse the API response into a Python dictionary.
        data = response.json()

        if data.get('flag') == 'empty_result':

            print(f'{variant} returned an empty result from Variant Validator.')
            return 'empty_result'

        elif data is None:

            print(f"Warning: fetchVV returned None for variant: {variant}")
            return 'null'

        elif "validation_warning_1" in data:
            warning_block = data["validation_warning_1"]

            warnings = warning_block.get("validation_warnings", [])

            if warnings:
                print("Validation warnings:")
                for w in warnings:
                    print(f" - {w}")
        
        elif variant.startswith(('ENS', 'NM_', 'LRG_', 'NC_')):
            nm_variant = list(data.keys())[0]
            nc_variant = data[nm_variant]['primary_assembly_loci']['grch38']['hgvs_genomic_description']
            return nc_variant

        elif re.match(r'^[A-Za-z0-9_-]+:', variant):
            transcripts = data["transcripts"][0]["genomic_spans"]

            if not transcripts:
                print(f"Warning: No transcripts found for variant {variant}")
                return 'empty_result'
            
            nc_number = [k for k in transcripts.keys() if k.endswith(".11")][0]
            return f"{nc_number}:{genetic_change}"

        else:
            print(f"Error: Unrecognized variant format after data retrieval: {variant}")
            return 'error_unrecognized_format_after_retrieval'

    except requests.exceptions.RequestException as e:
        print(f"Request failed for {variant}: {e}\n")


#example use case
if __name__ == "__main__":
    variant = "ENST00000558518:c.301G>A"
    output = get_mane_nc(variant)
    print("Final Output:")
    print(output)

"""
I have created 2 functions, the first takes transcript variants (ENST, NM_, LRG_) and converts them to NC_ genomic variants using the VariantValidator API.
The second function takes gene symbols (e.g. LDLR) and retrieves the MANE Select NM_ transcript variant using the VariantValidator API.

Script works with the following inputs:
ENST00000252444.10:c.301G>A
COL1A1:c.301G>A
NM_000527.3:c.301G>A
"""