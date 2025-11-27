import csv

def variantParser(file):
    '''
    This function  extracts and parses the variants from .vcf and .csv files. It then stores the variants in a
    list.
    The variant_list is returned.

    :params: file: This leads to the .csv or.vcf file uploaded by the user.
                   The files are stored in the 'data' subdirectory, located in the base-directory of this software
                   package. The filepath is not hardcoded into the script because it is the absolute filepath within
                   the respective computer that this software package was loaded in.

             E.g.: '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/<Patient ID>.<vcf or csv>'

    :output: variant_list: A list of the variants extracted from the input file. Variants are denoted as
                           {chromosome}-{position}-{ref}-{alt}

                     E.g.: ['17-45983420-G-T', '4-89822305-C-G', '1-7984999-T-A', '19-41968837-C-G']

    :command: file = '/<path>/<to>/<base>/<directory>/<of>/Software_Engineering_Assessment_2025_AR_RW_RS/data/Patient1.vcf'
              variantParser(file)
    '''

    # A list in which to store the variants extracted from the input file.
    variant_list = []

    # A counter to count the lines.
    line_number = 0

    # Checks if the input file is a .vcf file.
    if file.endswith('.vcf') or file.endswith('.VCF'):

        # Reads the content of the .vcf file.
        lines = open(file, 'r')

        # Iterates through each line in the .vcf file.
        for line in lines:

            # Identifies the line number of the line currently being processed through the loop.
            line_number = line_number + 1

            # Ignores lines that begin with '#'.
            if line.startswith('#'):

                continue

            # Identifies variant lines without at least CHROMOSOME; POSITION; ID; REF; ALT...
            elif len(line.split('\t')) <= 4:

                # ...and prints a message to help identify which line was skipped.
                print(f'Variant in line {line_number} from {file.split('/')[-1]} is irregular and was not parsed.')
                continue

            else:

                # Extracts the chromosome from the variant line.
                chromosome = line.split('\t')[0].replace('chr', '')

                # Extracts the position from the variant line.
                position = line.split('\t')[1]

                # Extracts the REF allele from the variant line.
                ref = line.split('\t')[3]

                # Extracts the ALT allele from the variant line.
                alt = line.split('\t')[4]

                # Combines the above values into a format that will support queries to Variant Validator.
                variant = f'{chromosome}-{position}-{ref}-{alt}'

            # Appends the variant to a list.
            variant_list.append(variant.split('\n')[0])


    # Checks if the input file is a .csv file.
    if file.endswith('.csv') or file.endswith('.CSV'):

        # Reads the content of the .csv file.
        csv_file = open(file, 'r')
        rows = csv.reader(csv_file)

        # Iterates through each row in the .csv file.
        for row in rows:

            # Identifies the row number of the line currently being processed through the loop.
            line_number = line_number + 1

            # Ignores row that begin with '#', usually the header.
            if row[0].startswith('#'):

                continue

            # Identifies variant rows without at least CHROMOSOME; POSITION; ID; REF; ALT...
            elif len(row) <= 4:

                # ...and prints a message to help identify which row was skipped.
                print(f'Variant in line {line_number} from {file.split('/')[-1]} is irregular and was not parsed.')
                continue

            # Ignores NoneType entities in the file.
            elif not row:

                continue

            else:

                # Extracts the chromosome from the variant row.
                chromosome = row[0].replace('chr', '')

                # Extracts the position from the variant row.
                position = row[1]

                # Extracts the REF allele from the variant row.
                ref = row[3]

                # Extracts the ALT allele from the variant row.
                alt = row[4]

                # Combines the above values into a format that will support queries to Variant Validator.
                variant = f'{chromosome}-{position}-{ref}-{alt}'

            # Appends the variant to a list.
            variant_list.append(variant)

    # Returns the patient ID and the list of variants from the input file.
    return variant_list

#print(variantParser('/home/ubuntu/Desktop/ParkVCF/Patient1.vcf'))