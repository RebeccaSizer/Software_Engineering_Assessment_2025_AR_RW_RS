# First install the requests module if you haven't already:
# pip install requests

import requests  # Import the 'requests' library to handle HTTP requests to the VariantValidator API

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
    base_url_VV = "https://rest.variantvalidator.org/VariantValidator/variantvalidator/hg38/"

    # Initialize an empty dictionary to store NC_ → NM_ mappings.
    HGVS_dict = {}

    # Loop through each variant in the provided list.
    for var in variants:
        # Construct the full API request URL for each variant.
        # The 'mane' flag requests MANE transcript data if available.
        # The 'content-type' query specifies JSON output.
        url_vv = f"{base_url_VV}{var}/mane?content-type=application%2Fjson"

        try:
            # Send an HTTP GET request to the API.
            response = requests.get(url_vv)

            # Raise an exception if the HTTP status code is not 200 (OK).
            response.raise_for_status()

            # Parse the API response into a Python dictionary.
            data = response.json()

            # Initialize variables to store identifiers.
            nm = None  # Transcript-level identifier (RefSeq NM_ accession)
            nc = None  # Genomic-level identifier (RefSeq NC_ accession)

            # The API response is a nested JSON object, so we loop over its items.
            for k, v in data.items():

                # Extract NM_ identifier from the 'hgvs_transcript_variant' field, if present.
                # This field has values like: "NM_001377265.1:c.841G>T"
                if 'hgvs_transcript_variant' in v:
                    nm = v['hgvs_transcript_variant'].split(':')[0]  # Keep only "NM_..." part

                # Extract NC_ identifier from 'primary_assembly_loci', focusing on GRCh38 assembly.
                if 'primary_assembly_loci' in v:
                    # Get only the GRCh38 locus entry (ignore GRCh37, alt haplotypes, etc.)
                    build_info = v['primary_assembly_loci'].get('grch38', {})
                    # Retrieve the HGVS genomic description (e.g. "NC_000017.11:g.45983420G>T")
                    hgvs_desc = build_info.get('hgvs_genomic_description', '')
                    # Keep only accessions that start with "NC_"
                    if hgvs_desc.startswith('NC_'):
                        nc = hgvs_desc

            # Once both identifiers are found, add them to the output dictionary.
            # Example: {'NC_000017.11': 'NM_001377265.1'}
            if nc and nm:
                HGVS_dict[nc] = nm
            else:
                # If either identifier is missing, print a message for debugging.
                print(f"No HGVS identifiers found for {var}. Full response:\n{data}\n")

        # Catch any network or HTTP errors raised by 'requests'.
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {var}: {e}\n")

    # Return the final dictionary mapping genomic (NC_) → transcript (NM_) accessions.
    return HGVS_dict


# Example usage
if __name__ == "__main__":
    variant = ["17-45983420-G-T"]
    output = HGVS_converter(variant)
    print("Final Output:")
    print(output)