import gzip
import csv
import urllib.request

def clinvarAnnotations(nc_variant, nm_variant):
    """
    Look up detailed ClinVar info by NM_ or NC_ HGVS from variant_summary.txt.gz.
    Returns condition(s), star rating (review status), cDNA + protein change, etc.
    """
    url = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
    print(f"Searching ClinVar summary file for {nc_variant} ...")

    # Tolerate transcript version differences
    vv_nc_accession = nc_variant.split(":")[0]
    #term_noversion = hgvs_term.split(":")[1] if ":" in hgvs_term else hgvs_term

    clinvar_output = {}

    with urllib.request.urlopen(url) as response:
        with gzip.open(response, "rt", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:

                dict_nc_accession = row['ChromosomeAccession']

                if row['Name'].startswith('NM'):

                    if '(' in row['Name']:
                        dict_nm_HGVS = f'{row['Name'].split('(')[0]}{row['Name'].split(')')[1].split(' ')[0]}'

                    else:
                        dict_nm_HGVS = row['Name']

                if (vv_nc_accession == dict_nc_accession) and (nm_variant == dict_nm_HGVS):

                    clinvar_output['classification'] = row['ClinicalSignificance']
                    clinvar_output['conditions'] = row['PhenotypeList'].replace('not provided', '')
                    clinvar_output['reviewstatus'] = row['ReviewStatus']

                    if 'practice guideline' in row['ReviewStatus']:

                        clinvar_output['stars'] = '★★★★'

                    elif 'reviewed by expert panel' in row['ReviewStatus']:

                        clinvar_output['stars'] = '★★★'

                    elif 'multiple submitters' in row['ReviewStatus']:

                        clinvar_output['stars'] = '★★'

                    elif 'single submitter' in row['ReviewStatus']:

                        clinvar_output['stars'] = '★'

                    else:

                        clinvar_output['stars'] = '0★'

                if len(clinvar_output) > 0:
                    break

    return clinvar_output

'''
# Example
if __name__ == "__main__":
    result = get_clinvar_full_info(('NC_000017.11:g.45983420G>T', 'NM_001377265.1:c.841G>T', 'NP_001364194.1:p.(Ala281Ser)', 'MAPT', '6893'))
    print(result)
'''

# print(get_clinvar_full_info('NC_000017.11:g.45983420G>T', 'NM_001377265.1:c.841G>T'))