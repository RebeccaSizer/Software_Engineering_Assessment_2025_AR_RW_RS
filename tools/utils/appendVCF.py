def appendVCF(file, clinvar_output):

    patient_name = file.split('.')[0].split('/')[-1]

    file_content = open(file, 'r')
    lines = file_content.readlines()
    file_content.close()

    new_lines = []

    for line in lines:

        for key, value in clinvar_output.items():

            chromosome = key.split('.')[0][-2:].replace('0', '')
            position = key.split('.')[2][0:-3]
            ref = key.split('>')[0][-1]
            alt = key.split('>')[1]

            if (line.split('\t')[0].replace('chr', '') == chromosome and
                    line.split('\t')[1] == position and
                    line.split('\t')[3] == ref and
                    line.split('\t')[4].replace('\n', '') == alt):

                new_line = f'{patient_name}\t{line}'

                for feature in value:

                    new_line = new_line.replace('\n', f'\t{feature}\n')

                print(new_line)

                new_lines.append(new_line)

    with open(file, "w") as f:
        f.writelines(new_lines)


#appendVCF('/home/ubuntu/Desktop/Software_Engineering_Assessment_2025_AR_RW_RS/Patient1.vcf', {'NC_000017.11:g.45983420G>T': ['Pathogenic', 'Unknown', '★★', 'criteria provided, multiple submitters, no conflicts'], 'NC_000004.12:g.89822305C>G': ['Pathogenic', 'Unknown', '★★', 'criteria provided, multiple submitters, no conflicts'], 'NC_000017.11:g.44352531G>A': ['Pathogenic', 'Unknown', '0★', 'no assertion criteria provided'], 'NC_000017.11:g.45987066G>A': ['Pathogenic', 'Unknown', '★★', 'criteria provided, multiple submitters, no conflicts'], 'NC_000017.11:g.44352387C>T': ['Pathogenic', 'Unknown', '0★', 'no assertion criteria provided'], 'NC_000019.10:g.41968837C>G': ['Pathogenic', 'Unknown', '★★', 'criteria provided, multiple submitters, no conflicts'], 'NC_000017.11:g.45983694C>T': ['Pathogenic', 'Unknown', '★★', 'criteria provided, multiple submitters, no conflicts'], 'NC_000001.11:g.7984999T>A': ['Pathogenic', 'Unknown', '0★', 'no assertion criteria provided'], 'NC_000001.11:g.7984929G>A': ['Pathogenic', 'Unknown', '0★', 'no assertion criteria provided']})