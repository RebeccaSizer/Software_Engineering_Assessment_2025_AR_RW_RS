# Software_Engineering_Assessment_2025_AR_RW_RS

# SEA_2025
<img src="assets/SEA_logo.png" width="200" height="227" />

**Notice: This piece of software is in development as a university project and as yet is not a fully functioning or tested product. Additionally, ongoing maintenance and contributions to this code by the original developers will cease after 08/01/2025. Use of this software is at your own risk.**

SEA is a webapp prototype tool for annotating germline variant data using information from ClinVar. It uses API queries to get up to date information regarding NGS panels for alzheimers disease. It is designed to support clinical researchers (not bioinformaticians) working with experimental variant data from the Parkinson’s disease panel.

## Overview of Features

- Upload single or multiple VCF files through the web app
- Extract all variants from the uploaded VCFs
- Send variants to the Variant Validator API to:
    - normalise the variant
    - generate the correct RefSeq NC_ accession numbers
    - Use the NC_ numbers to query ClinVar for:
    - clinical significance
    - associated conditions
    - review status and supporting evidence
- Annotate each variant with the returned ClinVar data
- Store all annotated variants in an SQL database
- Avoid re-querying ClinVar by checking if a variant already exists in the database
- Search the database by:
    - variant
    - patient/sample ID
    - gene symbol 
    - transcript
    - clinical significance
- View all matching variants and their annotations through the web interface

## Quick Start
1. [Index](https://SEA_2025.readthedocs.io/en/latest/)
2. [Installation Guide](https://SEA_2025.readthedocs.io/en/latest/installation/)
3. [User Manual](https://SEA_2025.readthedocs.io/en/latest/user_manual/)
4. [Technical Manual](https://SEA_2025.readthedocs.io/en/latest/technical_manual/)


## Continuous Integration
Automated unit and functional testing and continuous integration testing have been set up with GitHub Actions (see .github/workflows) and Jenkins CI (See Jenkinsfile).


## License
This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## Contributing
We welcome contributions to improve SEA_2025! Here's how you can get involved:

1. **Report Issues**
    - Found a bug or have a suggestion? Open an issue on our GitHub issues page. 
    - Add a label to describe the type of issue, e.g. bug, enhancement.
2. **Submit Changes**
    - Fork the repository and create a new branch for your changes.
    - Make your edits and a thorough suite of tests. Note that we make use of:
      - numpy style docstrings
      - `pylint` or `black` to ensure PEP-8 compliance
      - `coverage` to check test coverage
    - Submit a pull request with a clear description of your changes
3. **Provide Feedback or Ask Questions**
    - For questions or feedback, please email [Rebecca.Sizer@postgrad.manchester.ac.uk](mailto:Rebecca.Sizer@postgrad.manchester.ac.uk).
