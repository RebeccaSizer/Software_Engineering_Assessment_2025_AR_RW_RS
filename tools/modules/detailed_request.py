import gzip
import csv
import urllib.request

def get_clinvar_full_info(hgvs_term, local_file=None):
    """
    Look up detailed ClinVar info by NM_ or NC_ HGVS from variant_summary.txt.gz.
    Returns condition(s), star rating (review status), cDNA + protein change, etc.
    """
    url = local_file or "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
    print(f"Searching ClinVar summary file for {hgvs_term} ...")

    # Tolerate transcript version differences
    term_base = hgvs_term.split(".")[0]      # e.g. NM_170707
    term_noversion = hgvs_term.split(":")[1] if ":" in hgvs_term else hgvs_term

    with (open(url, "rb") if local_file else urllib.request.urlopen(url)) as response:
        with gzip.open(response, "rt", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                name_field = row.get("Name", "")
                if (
                    term_base in name_field
                    and term_noversion.split(">")[0] in name_field
                ):
                    # Collect detailed fields
                    conditions = row.get("ConditionList") or row.get("Condition(s)") or "Unknown"
                    classification = row.get("ClinicalSignificance", "Unknown")
                    review = row.get("ReviewStatus", "Unknown")
                    protein = row.get("ProteinChange", "Unknown")
                    gene = row.get("GeneSymbol", "Unknown")
                    variation_id = row.get("VariationID", "Unknown")

                    # Derive star rating
                    stars = (
                        "★★★★" if "practice guideline" in review.lower()
                        else "★★★" if "reviewed by expert panel" in review.lower()
                        else "★★" if "multiple submitters" in review.lower()
                        else "★" if "single submitter" in review.lower()
                        else "0★"
                    )

                    return {
                        "hgvs": hgvs_term,
                        "gene": gene,
                        "classification": classification,
                        "conditions": conditions,
                        "review_status": review,
                        "stars": stars,
                        "cdna_change": name_field,
                        "protein_change": protein,
                        "source_url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{variation_id}/",
                        "source": "variant_summary.txt.gz"
                    }

    return {"hgvs": hgvs_term, "classification": "Not found", "source": "variant_summary.txt.gz"}


# Example
if __name__ == "__main__":
    result = get_clinvar_full_info("NM_170707.4:c.673C>T")
    print(result)