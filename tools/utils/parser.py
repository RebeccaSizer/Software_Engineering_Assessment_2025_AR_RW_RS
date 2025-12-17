import csv
from flask import flash
from tools.utils.logger import logger


def variant_parser(file):
    '''
    This function  extracts and parses the variants from .vcf and .csv files. It then stores the variants in a
    list.
    The variant_list is returned.

    :params: file: This is a filepath that leads to the .csv or.vcf file uploaded by the user.
                   The files are stored in the 'temp' subdirectory, located in the base-directory of this software
                   package. The filepath is not hardcoded into the script because it is the absolute filepath within
                   the respective system that this software package was loaded in.

             E.g.: '/<path>/<from>/<root>/<to>/<base>/<directory>/<of>/
                      Software_Engineering_Assessment_2025_AR_RW_RS/temp/<Patient ID>.<vcf or csv>'

    :output: variant_list: A list of the variants extracted from the input file. Variants are denoted as
                           {chromosome}-{position}-{ref}-{alt}

                     E.g.: ['17-45983420-G-T', '4-89822305-C-G', '1-7984999-T-A', '19-41968837-C-G']

    :command: file = '/<path>/<to>/<base>/<directory>/<of>/
                        Software_Engineering_Assessment_2025_AR_RW_RS/temp/Patient1.vcf'
              variant_parser(file)
    '''

    # A list in which to store the variants extracted from the input file.
    variant_list = []
    # A counter to count the lines.
    line_number = 0
    # A counter to count the lines that were skipped (recommended by ChatGPT).
    skip_number = 0
    # A counter to count the number of variants that were parsed (recommended by ChatGPT).
    parsed_number = 0
    # The filename of the variant file that variants are being parsed from, including the file extension.
    filename = file.split('/')[-1]

    # Check that the filepath at the end of the file path can be accessed.
    try:
        # Checks if the input file is a .vcf file.
        if file.endswith(('.vcf', '.VCF')):
            # Log which type of file variants are being parsed from.
            logger.info('Parsing variants from .VCF file.')
            # Reads the content of the .vcf file.
            lines = open(file, 'r')

            # Iterates through each line in the .vcf file.
            for line in lines:
                # Ignore lines that begin with '#'.
                if line.startswith('#'):
                    line_number = line_number + 1
                    continue

                # Identify variant lines without at least CHROMOSOME; POSITION; ID; REF; ALT values and skip them.
                elif len(line.split('\t')) < 5:
                    # Identify the line number of the line currently being processed through the loop.
                    line_number = line_number + 1
                    # Increase the counter for the number of lines that were skipped by 1.
                    skip_number = skip_number + 1
                    # Log a message to help identify which line was skipped.
                    logger.warning(
                        f"Variant Parser Warning: "
                        f"Variant in line {line_number} from {filename} is irregular and was not parsed.")
                    # Notify the User which variant was not parsed.
                    flash(f"⚠ Variant Parser Warning: Variant in line {line_number} from {filename} is "
                          f"irregular and was not parsed.")
                    continue

                else:
                    # Check that the values parsed from the variant file are as they should be.
                    try:
                        # Extracts the chromosome from the variant line.
                        chromosome = line.split('\t')[0].replace('chr', '')
                        # Extracts the position from the variant line and validates that it is an integer.
                        position = int(line.split('\t')[1])
                        # Extracts the REF allele from the variant line.
                        ref = line.split('\t')[3]
                        # Extracts the ALT allele from the variant line.
                        alt = line.split('\t')[4]
                        # Combines the above values into a format that will support queries to Variant Validator.
                        variant = f'{chromosome}-{position}-{ref}-{alt}'

                        # Identify the line number of the line currently being processed through the loop.
                        line_number = line_number + 1
                        # Log the variant that was parsed.
                        logger.info(f'Variant Parser: {variant} parsed from line {line_number} in {filename}.')
                        # Increase the counter that counts the number of variants that were parsed by 1.
                        parsed_number = parsed_number + 1

                    # Raise a ValueError exception if the values parsed from the variant file is irregular.
                    except ValueError as e:
                        # Increase the counter for the number of lines that were skipped by 1.
                        skip_number = skip_number + 1
                        # Log a message to help identify which line was skipped.
                        logger.error(
                            f"Variant Parser ValueError: Variant information in line {line_number} from "
                            f"{filename} is irregular and was not parsed: {e}")
                        # Notify the User which variant was not parsed.
                        flash(f"❌ Variant Parser Error: Variant in line {line_number} from {filename} is "
                              f"irregular and was not parsed.")
                        continue

                # Appends the variant to a list.
                variant_list.append(variant.split('\n')[0])


        # Checks if the input file is a .csv file.
        if file.endswith(('.csv', '.CSV')):
            # Log which type of file variants are being parsed from.
            logger.info('Parsing variants from .CSV file.')

            # Reads the content of the .csv file.
            csv_file = open(file, 'r')
            rows = csv.reader(csv_file)

            # Iterates through each row in the .csv file.
            for row in rows:

                # Identifies the row number of the line currently being processed through the loop.
                line_number = line_number + 1

                # Ignores row that begin with '#', usually the header.
                if row[0].startswith('#'):
                    line_number = line_number + 1
                    continue

                # Identifies variant lines without at least CHROMOSOME; POSITION; ID; REF; ALT values and skips them.
                elif len(row.split('\t')) < 5:
                    # Increase the counter for the number of lines that were skipped by 1.
                    skip_number = skip_number + 1
                    # Print a message to help identify which line was skipped.
                    logger.warning(
                        f"Variant Parser Warning: "
                        f"Variant in row {line_number} from {filename} is irregular and was not parsed.")
                    # Notify the User which variant was not parsed.
                    flash(f"⚠ Variant Parser Warning: Variant in row {line_number} from {filename} is "
                          f"irregular and was not parsed.")
                    continue

                # Ignores NoneType entities in the file.
                elif not row:
                    continue

                else:
                    try:
                        # Extracts the chromosome from the variant row.
                        chromosome = row[0].replace('chr', '')
                        # Extracts the position from the variant row and validates that it is an integer.
                        position = int(row[1])
                        # Extracts the REF allele from the variant row.
                        ref = row[3]
                        # Extracts the ALT allele from the variant row.
                        alt = row[4]
                        # Combines the above values into a format that will support queries to Variant Validator.
                        variant = f'{chromosome}-{position}-{ref}-{alt}'

                        # Log the variant that was parsed.
                        logger.info(f'Variant Parser: {variant} parsed from row {line_number} in {filename}.')
                        # Increase the counter that counts the number of variants that were parsed by 1.
                        parsed_number = parsed_number + 1

                    # Raise a ValueError exception if the values parsed from the variant file is irregular.
                    except ValueError as e:
                        # Increase the counter for the number of lines that were skipped by 1.
                        skip_number = skip_number + 1
                        # Log a message to help identify which line was skipped.
                        logger.error(
                            f"Variant Parser ValueError: Variant information in row {line_number} from "
                            f"{filename} is irregular and was not parsed: {e}")
                        # Notify the User which variant was not parsed.
                        flash(f"❌ Variant Parser Error: Variant in row {line_number} from {filename} is "
                              f"irregular and was not parsed.")
                        continue

                # Appends the variant to a list.
                variant_list.append(variant)

    # Raise an exception if the variant file could not be found.
    except FileNotFoundError as e:
        # Log the error.
        logger.error(f"Variant Parser Error: Uploaded variant file '{filename}' not found: {e}")
        # Notify the User.
        flash(f'❌ Variant Parser Error: {filename} could not be found. Please try again.')
        return

    # Raise an exception if the User does not have permission to access the variant file.
    except PermissionError as e:
        # Log the error.
        logger.error(f"Variant Parser Error: Permission denied from accessing uploaded variant file '{filename}': {e}")
        # Notify the User.
        flash(f'❌ Variant Parser Error: You do not have permission to access {filename}.')
        return

    if not variant_list or len(variant_list) == 0:
        # Log that no variants were parsed.
        logger.warning(f'Variant Parser: Nothing was parsed from {filename}.')
        # Notify the User.
        flash(f'⚠ Variant Parser: Nothing was parsed from {filename}.')
        return

    # Log the number of variants that were parsed and the number of variants that were skipped.
    logger.info(f'Variant Parser: {filename}: Parsed: {parsed_number}; Skipped: {skip_number}.')

    # Returns the patient ID and the list of variants from the input file.
    return variant_list




#print(variantParser('/home/ubuntu/Desktop/ParkVCF/Patient1.vcf'))