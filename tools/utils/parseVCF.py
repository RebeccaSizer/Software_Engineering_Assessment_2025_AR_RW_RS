import csv

def parseVCF(file):

    patient_name = file.split('.')[0].split('/')[-1]

    variant_list = []

    line_number = 0

    if file.endswith('.vcf') or file.endswith('.VCF'):

        lines = open(file, 'r')

        for line in lines:

            line_number = line_number + 1

            if line.startswith('#'):

                print(f'Variant in line {line_number} from {file.split('/')[-1]} is irregular and was not parsed.')

                continue

            elif len(line.split('\t')) <= 4:

                continue

            else:

                chromosome = line.split('\t')[0].replace('chr', '')
                position = line.split('\t')[1]
                ref = line.split('\t')[3]
                alt = line.split('\t')[4]

                variant = f'{chromosome}-{position}-{ref}-{alt}'

            variant_list.append(variant.split('\n')[0])



    if file.endswith('.csv') or file.endswith('.CSV'):

        csv_file = open(file, 'r')
        lines = csv.reader(csv_file)

        for line in lines:

            line_number = line_number + 1

            if line[0].startswith('#'):

                continue

            elif len(line) <= 4:

                continue

            else:

                chromosome = line[0].replace('chr', '')
                position = line[1]
                ref = line[3]
                alt = line[4]

                variant = f'{chromosome}-{position}-{ref}-{alt}'

            variant_list.append(variant)

    return patient_name, variant_list

#print(parseVCF('/home/ubuntu/Desktop/ParkCSV/Patient1.csv'))