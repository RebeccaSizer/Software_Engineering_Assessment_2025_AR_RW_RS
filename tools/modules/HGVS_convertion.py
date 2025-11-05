# First install the requests module if you haven't already:
# pip install requests

import requests

def HGVS_converter(variants: list):
    """
    Query the VariantValidator REST API to retrieve HGVS transcript (NM_) and genomic (NC_) identifiers 
    for a list of human variants in 'chrom-pos-ref-alt' format.

    Parameters
    ----------
    variants : list
        A list of variant strings formatted as 'chrom-pos-ref-alt', e.g. ['17-45983420-G-T'].

    Returns
    -------
    HGVS_list : list
        A list containing extracted HGVS identifiers for each variant.
        Each entry includes a pair of lists: [list_of_NC_numbers, list_of_NM_numbers].
        Example:
            [
                [['NC_000017.10', 'NC_000017.11'], ['NM_001377265.1']]
            ]

    Notes
    -----
    - Uses the VariantValidator public REST API (https://rest.variantvalidator.org/).
    - Currently fixed to use the hg38 reference genome.
    - Requests are made to the /variantvalidator endpoint with MANE transcript preference.
    """

    # Define the VariantValidator API base URL for the hg38 genome
    base_url_VV = "https://rest.variantvalidator.org/VariantValidator/variantvalidator/hg38/"

    # Initialize a list to store HGVS IDs for all variants
    HGVS_list = []

    # Loop over each variant in the provided list
    for var in variants:
        # Construct the full request URL for each variant
        # The 'mane' flag requests MANE-select transcripts if available
        url_vv = f"{base_url_VV}{var}/mane?content-type=application%2Fjson"

        try:
            # Send a GET request to the VariantValidator API
            response = requests.get(url_vv)
            response.raise_for_status()  # Raise an exception if the request fails (status != 200)
            
            # Parse the returned JSON data
            data = response.json()
            nm_numbers = []  # Store NM_ identifiers (RefSeq transcript accessions)
            nc_numbers = []  # Store NC_ identifiers (RefSeq genomic accessions)
            
            # Iterate through the JSON structure (it contains nested variant entries)
            for k, v in data.items():
                # Extract NM_ number from the transcript variant field
                if 'hgvs_transcript_variant' in v:
                    nm = v['hgvs_transcript_variant'].split(':')[0]
                    nm_numbers.append(nm)

                # Extract NC_ numbers from the primary assembly loci section
                if 'primary_assembly_loci' in v:
                    for build, info in v['primary_assembly_loci'].items():
                        hgvs_desc = info.get('hgvs_genomic_description', '')
                        if hgvs_desc.startswith('NC_'):
                            nc = hgvs_desc.split(':')[0]
                            if nc not in nc_numbers:
                                nc_numbers.append(nc)

            # Append results to the main list if found
            if nm_numbers or nc_numbers:
                HGVS_list.append([nc_numbers, nm_numbers])
            else:
                print(f"No HGVS identifiers found for {var}. Full response:\n{data}\n")

        except requests.exceptions.RequestException as e:
            # Handle any errors raised by the request (e.g., connection issues, 404s)
            print(f"Request failed for {var}: {e}\n")
        
    # Return all collected HGVS IDs
    return HGVS_list


# Example usage
if __name__ == "__main__":
    variant = ["17-45983420-G-T"]
    output = HGVS_converter(variant)
    print("Final Output:")
    print(output)