def parseVCF(file):

    patient_name = file.split('.')[0].split('/')[-1]

    variant_list = []

    file = open(file, 'r')

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

    return patient_name, variant_list