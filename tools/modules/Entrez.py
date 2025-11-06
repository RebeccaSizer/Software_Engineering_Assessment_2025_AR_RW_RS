from Bio import Entrez
from Bio import SeqIO
import json

class objectify:
    def __init__(self, record):
        for key, value in record.items():
            setattr(self, key, value)

def Entrez_fetch_transcript_record(email: str, accession_ID: str):

    Entrez.email = email

    with Entrez.efetch(db='nucleotide', rettype='gb', retmode='text', id=accession_ID) as handle:

        for seq_record in SeqIO.parse(handle, 'gb'):

            for feature in seq_record.features:

                if feature.type == 'CDS':

                    CDS_dict = {
                        'gene': feature.qualifiers['gene'],
                        'protein_id': feature.qualifiers['protein_id'],
                        'db_xref': feature.qualifiers['db_xref'],
                        'translation': feature.qualifiers['translation']
                    }

            record_dict = {
                'ID': seq_record.id,
                'Gene_symbol': CDS_dict['gene'][0],
                'HGNC_ID': CDS_dict['db_xref'][2].split(':')[2],
                'DNA_sequence': str(seq_record.seq),
                'RNA_sequence': str(seq_record.seq.replace("T", "U")),
                'Protein_sequence': CDS_dict['translation'][0],
                'Protein_ID': CDS_dict['protein_id'][0]
            }

    #print(json.dumps(record_dict, indent=4))

    return record_dict
#record = objectify(Entrez_fetch_transcript_record('A.N.Other@example.com', 'NM_000527.5'))