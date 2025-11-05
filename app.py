from tools.utils.appendVCF import appendVCF
from tools.utils.parseVCF import parseVCF
from tools.modules.HGVS_convertion import HGVS_converter
from tools.modules.detailed_request import get_clinvar_full_info
import sys

if __name__ == '__main__':
    files = sys.argv[1:]

    for file in files:

        variant_list = parseVCF(file)

        vv_dict = HGVS_converter(variant_list)

        for key, value in vv_dict.items():

            clinvar_annotation = []

            clinVar_response = get_clinvar_full_info(value)

            clinvar_annotation.append(clinVar_response['classification'])
            clinvar_annotation.append(clinVar_response['conditions'])
            clinvar_annotation.append(clinVar_response['stars'])
            clinvar_annotation.append(clinVar_response['review_status'])

            vv_dict[key] = clinvar_annotation

        appendVCF(file, vv_dict)








