from tools.utils.parseVCF import parseVCF
from tools.modules.HGVS_convertion import HGVS_converter
import sys

def main():

    return sys.argv[2]

if __name__ == '__main__':
    file = main()
    variant_list = parseVCF(file)
    HGVS_converter(variant_list)





