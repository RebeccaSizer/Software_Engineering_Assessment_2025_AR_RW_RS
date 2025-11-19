# First install the requests module if you haven't already:
# pip install requests

import requests  # Import the 'requests' library to handle HTTP requests to the VariantValidator API
import time

def fetch_vv(variant: str):
    """
    Query the VariantValidator REST API to retrieve HGVS transcript (NM_) and genomic (NC_) identifiers 
    for a list of human variants in 'chrom-pos-ref-alt' format.

    Parameters
    ----------
    variant : str
        A list of variant strings formatted as 'chrom-pos-ref-alt', e.g. ['17-45983420-G-T'].

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
    """

    # Base URL for the VariantValidator API.
    # The endpoint specifies we’re working with the hg38 genome build.
    base_url_vv = "https://rest.variantvalidator.org/VariantValidator/variantvalidator/hg38/"

    # Construct the full API request URL for each variant.
    # The 'mane' flag requests MANE transcript data if available.
    # The 'content-type' query specifies JSON output.
    url_vv = f"{base_url_vv}{variant}/mane?content-type=application%2Fjson"

    try:
        # Send an HTTP GET request to the API.
        response = requests.get(url_vv)

        # Raise an exception if the HTTP status code is not 200 (OK).
        response.raise_for_status()

        # The time module creates a 0.5s delay after each request to Variant Validator (VV), so that VV is not overloaded with requests.
        time.sleep(0.5)

        # Parse the API response into a Python dictionary.
        data = response.json()
        #print(data)

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
            hgnc_id = data[nm_variant]['gene_ids']['hgnc_id'].split(':')[1]

            # Once both identifiers are found, add them to the output dictionary.
            # Example: {'NC_000017.11': 'NM_001377265.1'}
            if nc_variant and nm_variant and np_variant:

                return (nc_variant, nm_variant, np_variant, gene_symbol, hgnc_id)

            else:
                # If either identifier is missing, print a message for debugging.
                print(f"No HGVS identifiers found for {variant}. Full response:\n{data}\n")

    # Catch any network or HTTP errors raised by 'requests'.
    except requests.exceptions.RequestException as e:
        print(f"Request failed for {variant}: {e}\n")

#print(fetchVV('11-2164285-C-T'))

# Example usage
#if __name__ == "__main__":
#    variant = ["17-45983420-G-T"]
#    output = HGVS_converter(variant)
#    print("Final Output:")
#    print(output)