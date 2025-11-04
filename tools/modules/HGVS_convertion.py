#first install request module - pip install requests
#import the requests module 
import requests

def HGVS_converter(variants:list):

    #specify the base url to get information for variant validator
    base_url_LOVD = "https://rest.variantvalidator.org/LOVD/lovd/hg38/"
    base_url_VV = "https://rest.variantvalidator.org/VariantValidator/variantvalidator/hg38/"
    #make a base list for the addition of the new HGVS nomenclature
    HGVS_list = []
    #input of variants is in the format 'chrom-pos-ref-alt'

    for var in variants:
        #find the url for the variantvalidator end point. I have hard coded in the reference genome,
        #the mane (Mane and MANE select) - the outputs a json 
        #url_lovd = f"{base_url_LOVD}{var}/refseq/mane/tx/primary?content-type=application%2Fjson"
        url_vv = f"{base_url_VV}{var}/mane?content-type=application%2Fjson"

        #var_key = var.replace("-", ":") 

        try:
            response = requests.get(url_vv)
            response.raise_for_status()  # raises an error if status != 200
            
            data = response.json()

            for k in data:
                if k.startswith("NM_"):
                    first_key = k

            NM_no = data[first_key].get("reference_sequence_records", {}).get("transcript")

            # The structure of the JSON response can vary — inspect keys safely

            if NM_no:
                HGVS_list.append(NM_no)
            else:
                print(f"No HGVS found for {var_key}. Full response:\n{data}\n")

        except requests.exceptions.RequestException as e:
            print(f"Request failed for {var_key}: {e}\n")
        
        return  HGVS_list

if __name__=="__main__":
    variant = ["17-45983420-G-T"]
    output = HGVS_converter(variant)
    print(output)