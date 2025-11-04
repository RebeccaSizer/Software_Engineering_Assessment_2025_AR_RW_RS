from tools.utils.parseVCF import parseVCF
from tools.modules.HGVS_convertion import HGVS_converter
import sys

if __name__ == '__main__':
    file = sys.argv[1]
    variant_list = parseVCF(file)
    print(HGVS_converter(variant_list))





