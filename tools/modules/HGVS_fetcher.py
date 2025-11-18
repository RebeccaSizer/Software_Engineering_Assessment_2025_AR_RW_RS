# First install the requests module if you haven't already:
# pip install requests

import requests  # Import the 'requests' library to handle HTTP requests to the VariantValidator API
import time

def fetchVV(variant: str):
    """
    Query the VariantValidator REST API to retrieve HGVS transcript (NM_) and genomic (NC_) identifiers 
    for a list of human variants in 'chrom-pos-ref-alt' format.

    Parameters
    ----------
    variant : str
        A list of variant strings formatted as 'chrom-pos-ref-alt', e.g. ['17-45983420-G-T'].
        Or variant can be transcript variant like 'NM_12345:c.250A>G' or 'XM_12345:c.250A>G'.

    Returns
    -------
    HGVS_dict : dict
        A dictionary mapping each NC_ genomic accession (key) to its corresponding NM_ transcript accession (value).
        Example:
            {
                'NC_000017.11': 'NM_001377265.1'
            }

    Notes
    -----
    - Uses the VariantValidator public REST API (https://rest.variantvalidator.org/).
    - Currently fixed to use the hg38 reference genome.
    - Requests are made to the /variantvalidator endpoint with MANE transcript preference.
    - Allows conversion from None RefSeq transcript to MANE transcript when available.
    """

    # Base URL for the VariantValidator API.
    # The endpoint specifies we’re working with the hg38 genome build.
    base_url_VV = "https://rest.variantvalidator.org/VariantValidator/variantvalidator/hg38/"

    # Construct the full API request URL for each variant.
    # The 'mane' flag requests MANE transcript data if available.
    # The 'content-type' query specifies JSON output.
    #add this to determine if input is transcript or chrom-pos-ref-alt
    if variant.startswith(('NM_', 'XP_', 'XM_', 'ENST_')):
        url_vv = f"{base_url_VV}{variant}/mane?content-type=application%2Fjson" #transcript
    else:
        url_vv = f"{base_url_VV}{variant}/mane?content-type=application%2Fjson" #chrom-post-ref-alt

    try:
        # Send an HTTP GET request to the API.
        response = requests.get(url_vv)

        # Raise an exception if the HTTP status code is not 200 (OK).
        response.raise_for_status()

        # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not overloaded with requests.
        time.sleep(0.5)

        # Parse the API response into a Python dictionary.
        data = response.json()
        print(data)

        if data['flag'] == 'empty_result':

            print(f'{variant} returned an empty result from Variant Validator.')

            return 'empty_result'

        elif data is None:

            print(f"Warning: fetchVV returned None for variant: {variant}")

            return 'null'

        else:

            nm_variant = list(data.keys())[0]
            nc_variant = data[nm_variant]['primary_assembly_loci']['grch38']['hgvs_genomic_description']
            np_variant = data[nm_variant]['hgvs_predicted_protein_consequence']['tlr']
            gene_symbol  = data[nm_variant]['gene_symbol']
            HGNC_ID = data[nm_variant]['gene_ids']['hgnc_id'].split(':')[1]

            # Once both identifiers are found, add them to the output dictionary.
            # Example: {'NC_000017.11': 'NM_001377265.1'}
            if nc_variant and nm_variant and np_variant:

                return (nc_variant, nm_variant, np_variant, gene_symbol, HGNC_ID)

            else:
                # If either identifier is missing, print a message for debugging.
                print(f"No HGVS identifiers found for {variant}. Full response:\n{data}\n")

    # Catch any network or HTTP errors raised by 'requests'.
    except requests.exceptions.RequestException as e:
        print(f"Request failed for {variant}: {e}\n")

#print(fetchVV('17-45983420-G-T'))

# Example usage
if __name__ == "__main__":
    variant = "ENST00000549163.1:c.100A>G"
    output = fetchVV(variant)
    print("Final Output:")
    print(output)






"""

#edits so that searching by transcript that is not correct convers to NM and then searches 
def transcript_fetcher(transcript_variant: str):
    
    Query the VariantValidator REST API to retrieve the gene symbol and HGNC ID
    for a given NM_ transcript identifier.

    Parameters
    ----------
    transctip_variant : str
        An transcript identifier, e.g. 'XM_001377265.1'.

    Returns
    -------
    NM transcript variant : str
        An transcript identifier, e.g. 'NM_001377265.1'.
    
    # Base URL for the VariantValidator API.
    base_url_VV = "https://rest.variantvalidator.org/VariantValidator/variantvalidator/hg38/"

    # Construct the full API request URL for the transcript variant.
    url_vv = f"{base_url_VV}{transcript_variant}/mane?content-type=application%2Fjson"

    try:
        # Send an HTTP GET request to the API.
        response = requests.get(url_vv)
        # Raise an exception if the HTTP status code is not 200 (OK).
        response.raise_for_status()
        # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not overloaded with requests.
        time.sleep(0.5)

        # Parse the API response into a Python dictionary.
        data = response.json()
        print(data)

        if data['flag'] == 'empty_result':
            print(f'{transcript_variant} returned an empty result from Variant Validator.')
            return 'empty_result'

        elif data is None:
            print(f"Warning: transcript_fetcher returned None for variant: {transcript_variant}")
            return 'null'
        
        else:
            nm_variant = list(data.keys())[0]
            gene_symbol  = data[nm_variant]['gene_symbol']
            HGNC_ID = data[nm_variant]['gene_ids']['hgnc_id'].split(':')[1]

            if nm_variant:
                return (nm_variant, gene_symbol, HGNC_ID)
            else:
                print(f"No NM_ transcript found for {transcript_variant}. Full response:\n{data}\n")

"""                