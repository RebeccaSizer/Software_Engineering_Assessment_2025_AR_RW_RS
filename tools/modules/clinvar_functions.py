import sqlite3
import os
import gzip
import csv
import requests
from ..utils.timer import timer

@timer
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
    os.makedirs(os.path.abspath(os.path.join(script_dir, "..", "..", "app", "clinvar")), exist_ok=True)
    clinvar_file_path = os.path.abspath(os.path.join(script_dir, "..", "..", "app", "clinvar", "clinvar_db_summary.txt.gz"))
    clinvar_records = os.path.abspath(os.path.join(script_dir, "..", "..", "app", "clinvar", "clinvar.db"))

    # Save the variant summary records to a file (from ChatGPT).
    # Consider changing chunk_size to chunk_size=8192 is band-width is low.
    # Consider changing chunk_size to chunk_size=65536 is band-width is high.
    # or let the requests module decide by using: clinvar_db.iter_content(chunk_size=None)
    with open(clinvar_file_path, "wb") as f:
        for chunk in clinvar_db.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)

    # Print the date when the ClinVar variant_summary records were last modified.
    print("ClinVar database last modified:", requests.head(url).headers['Last-Modified'])

    conn = sqlite3.connect(clinvar_records)
    cur = conn.cursor()

    cur.execute("""
            CREATE TABLE IF NOT EXISTS clinvar (
                nc_accession TEXT,
                nm_hgvs TEXT,
                clinical_significance TEXT,
                conditions TEXT,
                stars TEXT,
                review_status TEXT             
            );
        """)

    cur.execute("DELETE FROM clinvar;")

    variant_info = []

    with gzip.open(clinvar_file_path, "rt") as gz:

        reader = csv.DictReader(gz, delimiter="\t")

        for record in reader:

            # Some records include the gene symbol and the consequence on the protein.
            # E.g. NM_000360.4(TH):c.1442G>A (Gly481Asp)
            # This removes the gene symbol and protein consequence from the nomenclature if a '(' exists in the
            # name.
            # Not all records are named after the RefSeq NM_ accession number so this specifies the ones that are.
            if record['Name'].startswith('NM'):

                if '(' in record['Name']:
                    record_nm_hgvs = f'{record['Name'].split('(')[0]}{record['Name'].split(')')[1].split(' ')[0]}'

                else:
                    record_nm_hgvs = record['Name']

                record_condition = record['PhenotypeList'].replace('not provided| ', '').replace('not specified| ', '').replace('not provided|', '').replace('not specified|', '').replace('not provided', '').replace('not specified', '').replace('|', '; ')

                if record_condition == '':

                    record_condition = 'None provided'

                if 'practice guideline' in record['ReviewStatus']:

                    stars = '★★★★'

                elif 'reviewed by expert panel' in record['ReviewStatus']:

                    stars = '★★★'

                elif 'multiple submitters' in record['ReviewStatus']:

                    stars = '★★'

                elif 'single submitter' in record['ReviewStatus']:

                    stars = '★'

                else:

                    stars = '0★'

                variant_info.append((record['ChromosomeAccession'],
                                record_nm_hgvs,
                                record['ClinicalSignificance'],
                                record_condition,
                                stars,
                                record['ReviewStatus']
                ))

    cur.executemany("""
            INSERT INTO clinvar VALUES (?, ?, ?, ?, ?, ?)
        """, variant_info)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_clinvar ON clinvar (nc_accession, nm_hgvs);")
    conn.commit()
    conn.close()



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
                                'stars': '0★',
                                'reviewstatus': 'criteria provided, conflicting classifications'
                             }

    :command: clinvarAnnotations('NC_000011.10:g.2164285C>T', 'NM_000360.4:c.1442G>A')
    '''

    # Isolate the NC_ accession number from the NC_ HGVS nomenclature used as input to search in the ClinVar database.
    vv_nc_accession = nc_variant.split(":")[0]

    # Creates a python dictionary to store the required information from ClinVar
    clinvar_output = {}

    script_dir = os.path.dirname(os.path.abspath(__file__))
    clinvar_db = os.path.abspath(os.path.join(script_dir, "..", "..", "app", "clinvar", "clinvar.db"))

    # Message to indicate that variant is being searched for in the downloaded ClinVar variant summary records.
    print(f'Searching ClinVar database for {nc_variant} ...')

    conn = sqlite3.connect(clinvar_db)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT clinical_significance, conditions, stars, review_status
                   FROM clinvar
                   WHERE nc_accession = ?
                     AND nm_hgvs LIKE ? 
                     LIMIT 1
                   """, (vv_nc_accession, nm_variant + '%'))

    record = cursor.fetchone()
    conn.close()

    # Message to indicate that variant is being searched for in the downloaded ClinVar variant summary records.
    if not record or len(record) == 0:
        print(f'Could not find {nc_variant} in ClinVar summary file!')

    else:

        clinical_significance, conditions, stars, review_status = record

        clinvar_output['classification'] = clinical_significance
        clinvar_output['conditions'] = conditions
        clinvar_output['stars'] = stars
        clinvar_output['reviewstatus'] = review_status

        # Returns the clinvar_output dictionary, even if length is 0.
        return clinvar_output
'''
# Example
if __name__ == "__main__":
    result = get_clinvar_full_info(('NC_000017.11:g.45983420G>T', 'NM_001377265.1:c.841G>T', 'NP_001364194.1:p.(Ala281Ser)', 'MAPT', '6893'))
    print(result)
'''

#print(clinvar_annotations('NC_000011.10:g.2164285C>T', 'NM_000360.4:c.1442G>A'))