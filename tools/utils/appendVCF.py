def appendVCF(file, clinvar_output):

    for key, value in clinvar_output.items():

        chromosome = key.split('.')[0][-2:].replace('0', '')
        position = key.split('.')[2][0:-3]
        ref = key.split('>')[0][-1]
        alt = key.split('>')[1]

        with open(file, 'r') as f:

            lines = f.readlines()

        for line in lines:

            if (line.split('\t')[0].replace('chr', '') == chromosome and
                line.split('\t')[1] == position and
                line.split('\t')[3] == ref and
                line.split('\t')[4] == alt):

                    line.replace('\n', f'\t{value}[0]\n'

        with open(file, "w") as file:
            file.writelines(lines)


