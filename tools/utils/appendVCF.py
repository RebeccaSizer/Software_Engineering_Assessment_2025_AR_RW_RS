def appendVCF(file, clinvar_output):

    hgvs = clinvar_output['hgvs']

    chromosome = hgvs.split('.')[0][-2:].replace('0', '')
    position = hgvs.split('.')[2][0:-3]
    ref = hgvs.split('>')[0][-1]
    alt = hgvs.split('>')[1]

    with open(file, 'r') as f:

        lines = f.readlines()

    for line in lines:

        if (line.split('\t')[0].replace('chr', '') == chromosome and
            line.split('\t')[1] == position and
            line.split('\t')[3] == ref and
            line.split('\t')[4] == alt):

                line.replace('\n', '\t.....\n'


