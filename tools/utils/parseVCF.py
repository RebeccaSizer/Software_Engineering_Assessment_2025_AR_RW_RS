def parseVCF(filepath_filename):

    variant_list = []

    file = open(filepath_filename, 'r')

    for line in file:

        if line.startswith('#'):

            continue

        else:

            chromosome = line.split('\t')[0].replace('chr', '')
            position = line.split('\t')[1]
            ref = line.split('\t')[3]
            alt = line.split('\t')[4]

            variant = f'{chromosome}-{position}-{ref}-{alt}'

        variant_list.append(variant.split('\n')[0])

    return variant_list