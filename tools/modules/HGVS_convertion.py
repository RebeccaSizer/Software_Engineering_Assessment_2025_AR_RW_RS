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
    nc_list = []
    nm_list = []
    np_list = []
    clinvar_list = []

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
            print(data)

            if data['flag'] == 'empty_result':

                print(f'{var} returned an empty result from Variant Validator.')
                continue

            else:


                nm_variant = list(data.keys())[0]
                nc_variant = data[nm_variant]['primary_assembly_loci']['grch38']['hgvs_genomic_description']
                np_variant = data[nm_variant]['hgvs_predicted_protein_consequence']['tlr']
                clinvar_input = nm_variant.split(':')[0]

                print(nc_variant)
                print(nm_variant)
                print(np_variant)
                print(clinvar_input)


                '''
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
                    '''


                # Once both identifiers are found, add them to the output dictionary.
                # Example: {'NC_000017.11': 'NM_001377265.1'}
                if nm_variant and np_variant:

                    nc_list.append(nc_variant)
                    nm_list.append(nm_variant)
                    np_list.append(np_variant)
                    clinvar_list.append(clinvar_input)

                else:
                    # If either identifier is missing, print a message for debugging.
                    print(f"No HGVS identifiers found for {var}. Full response:\n{data}\n")

        # Catch any network or HTTP errors raised by 'requests'.
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {var}: {e}\n")

    print(len(nc_list))
    print(len(nm_list))
    print(len(np_list))
    print(len(clinvar_list))

    for i in range(0, len(nc_list)):
        print(nc_list[i])
        print(nm_list[i])
        print(np_list[i])
        print(clinvar_list[i])
    return nc_list, nm_list, np_list, clinvar_list



HGVS_converter(['17-45983420-G-T', '4-89822305-C-G', '17-44352531-G-A', '17-45987066-G-A', '17-44352387-C-T', '19-41968837-C-G', '17-45983694-C-T', '1-7984999-T-A', '1-7984929-G-A'])

# Example usage
#if __name__ == "__main__":
#    variant = ["17-45983420-G-T"]
#    output = HGVS_converter(variant)
#    print("Final Output:")
#    print(output)