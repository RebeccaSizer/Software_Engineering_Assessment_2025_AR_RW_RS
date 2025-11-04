from Bio import Entrez
import xml.etree.ElementTree as ET

# Always provide your email to NCBI Entrez
Entrez.email = "your_email@example.com"

# 1. Search ClinVar for the HGVS variant
search_handle = Entrez.esearch(db='clinvar', term='NC_000001.11:g.156134838C>T')
search_results = Entrez.read(search_handle)
search_handle.close()

# Get the list of ClinVar IDs
clinvar_ids = search_results["IdList"]
if not clinvar_ids:
    print("No ClinVar entry found for this variant.")
    exit()

# 2. Fetch the ClinVar record in XML
fetch_handle = Entrez.efetch(db="clinvar", id=clinvar_ids[0], rettype="xml")
xml_data = fetch_handle.read()
fetch_handle.close()

# 3. Parse XML to extract consensus clinical significance
root = ET.fromstring(xml_data)
consensus = root.find(".//ClinicalSignificance/Description")