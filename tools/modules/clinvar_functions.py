import gzip
import os
import csv
import requests
from ..utils.timer import timer

def clinvar_vs_download():
    '''
    This function retrieves the most recent ClinVar variant summary records from NCBI.

    :outputs: clinvar_db_summary.txt.gz: A compressed .txt file which contains the variant summaries from ClinVar.

              Last-Modified: When the ClinVar variant summaries database was last updated.
                       E.g.: "ClinVar database last modified: Sun, 16 Nov 2025 22:54:32 GMT

    :command: clinvar_vs_fetcher()
    '''

    # The url to the database where we can download the variant summary records.
    url =  'https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz'

    # Stream the download so we don't load the entire file into memory at once.
    clinvar_db = requests.get(url, stream=True)

    # Raise an error if download failed.
    clinvar_db.raise_for_status()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    clinvar_file_path = os.path.abspath(os.path.join(script_dir, "..", "flask_search_database", "clinvar_db_summary.txt.gz"))

    # Save the variant summary records to a file (from ChatGPT).
    # Consider changing chunk_size to chunk_size=8192 is band-width is low.
    # Consider changing chunk_size to chunk_size=65536 is band-width is high.
    # or let the requests module decide by using: clinvar_db.iter_content(chunk_size=None)
    with open(clinvar_file_path, "wb") as f:
        for chunk in clinvar_db.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)

    # Condition to retrieve the date when the ClinVar variant_summary records were last modified.
    if 'Last-Modified' in requests.head(url).headers:
        print("ClinVar database last modified:", requests.head(url).headers['Last-Modified'])
    else:
        print("No Last-Modified header present")


#/tools/flask_search_database/

@timer
def clinvar_annotations(nc_variant, nm_variant):
    '''
    This function retrieves variant information from the compressed ClinVar variant summary file. It takes a variant
    in NC_ and NM_ HGVS nomenclature as input and uses them to find the entry in ClinVar record that matches the
    NC_accession number and NM_ HGVS nomenclature. It then returns a dictionary containing the variant classification,
    associated conditions, star-rating and Review status from that record.

    :params: nc_variant: The variant described in HGVS nomenclature, using the RefSeq NC_ accession number
                   E.g.: 'NC_000011.10:g.2164285C>T'

             nm_variant: The variant described in HGVS nomenclature, using the RefSeq NM_ accession number
                   E.g.: 'NM_000360.4:c.1442G>A'

    :output: clinvar_output: A python dictionary containing the variant classification, associated conditions,
                             star-rating and Review status from that record.

                       E.g.: {
                                'classification': 'Conflicting classifications of pathogenicity',
                                'conditions': 'Autosomal recessive DOPA responsive dystonia|Inborn genetic diseases',
                                'reviewstatus': 'criteria provided, conflicting classifications',
                                'stars': '0★'
                             }

    :command: clinvarAnnotations('NC_000011.10:g.2164285C>T', 'NM_000360.4:c.1442G>A')
    '''

    # Isolate the NC_ accession number from the NC_ HGVS nomenclature used as input to search in the ClinVar database.
    vv_nc_accession = nc_variant.split(":")[0]

    # Creates a python dictionary to store the required information from ClinVar
    clinvar_output = {}

    # Message to indicate that variant is being searched for in the downloaded ClinVar variant summary records.
    print(f'Searching ClinVar summary file for {nc_variant} ...')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    clinvar_file_path = os.path.abspath(os.path.join(script_dir, "..", "flask_search_database", "clinvar_db_summary.txt.gz"))


    # Check file exists
    if not os.path.exists(clinvar_file_path):
        raise FileNotFoundError(f"ClinVar database file not found: {clinvar_file_path}")


    # Opens ClinVar variant_summary records to search for the record which contains the NC_ accession number and
    # NM_ HGVS nomenclature (ClinVar variant_summary records do not contain the NC_ HGVS nomenclature).
    with gzip.open(clinvar_file_path, "rt") as gz:
        reader = csv.DictReader(gz, delimiter="\t")
        for record in reader:

            # Extracts the NC_ accession number from the current ClinVar variant_summary record.
            dict_nc_accession = record['ChromosomeAccession']

            # Not all records are named after the RefSeq NM_ accession number so this specifies the ones that are.
            if record['Name'].startswith('NM'):

                # Some records include the gene symbol and the consequence on the protein.
                # E.g. NM_000360.4(TH):c.1442G>A (Gly481Asp)
                # This removes the gene symbol and protein consequence from the nomenclature if a '(' exists in the
                # name.
                if '(' in record['Name']:
                    dict_nm_hgvs = f'{record['Name'].split('(')[0]}{record['Name'].split(')')[1].split(' ')[0]}'

                else:
                    dict_nm_hgvs = record['Name']

            # When the input RefSeq NC_ accession number and NM_ HGVS nomenclature matches a record, the clinvar_output
            # dictionary is populated with the variant classification, associated conditions, star-rating and Review
            # status from that record.
            if (vv_nc_accession == dict_nc_accession) and (nm_variant == dict_nm_hgvs):

                clinvar_output['classification'] = record['ClinicalSignificance']
                clinvar_output['reviewstatus'] = record['ReviewStatus']
                clinvar_output['conditions'] = record['PhenotypeList'].replace('not provided', '').replace('|', '; ')

                # If statement stores message in database, notifying users that a Condition was not found for this
                # variant.
                if clinvar_output['conditions'] == '':
                    clinvar_output['conditions'] = 'No Conditions submitted on ClinVar'

                if 'practice guideline' in record['ReviewStatus']:

                    clinvar_output['stars'] = '★★★★'

                elif 'reviewed by expert panel' in record['ReviewStatus']:

                    clinvar_output['stars'] = '★★★'

                elif 'multiple submitters' in record['ReviewStatus']:

                    clinvar_output['stars'] = '★★'

                elif 'single submitter' in record['ReviewStatus']:

                    clinvar_output['stars'] = '★'

                else:

                    clinvar_output['stars'] = '0★'

    # Message to indicate that variant is being searched for in the downloaded ClinVar variant summary records.
    if len(clinvar_output) == 0:
        print(f'Could not find {nc_variant} in ClinVar summary file!')

    # Returns the clinvar_output dictionary, even if length is 0.
    return clinvar_output
'''
# Example
if __name__ == "__main__":
    result = get_clinvar_full_info(('NC_000017.11:g.45983420G>T', 'NM_001377265.1:c.841G>T', 'NP_001364194.1:p.(Ala281Ser)', 'MAPT', '6893'))
    print(result)
'''

#print(clinvar_annotations('NC_000011.10:g.2164285C>T', 'NM_000360.4:c.1442G>A'))