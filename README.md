# Software_Engineering_Assessment_2025_AR_RW_RS

# SEA_2025
<img src="assets/SEA_logo.png" width="200" height="227" />

**Notice: This software was developed as a part of a university project and is not currently a fully functioning and tested product. Additionally, ongoing maintenance and contributions to this code by the original developers will cease after 08/01/2026. This application was intended for research and educational purposes. Data Protection of patient sensitive information cannot be assured. User discretion is advised.**

SEA is a webapp prototype tool for annotating germline variants detected by Next-Generation Sequencing (NGS) with information from ClinVar variant summary records. Variants and annotations are stored in an SQLite3 variant database which can be viewed and queried through our flask app.  It is designed to support Clinical Scientists and Researchers (not Bioinformaticians) working with experimental variant data from the Parkinson’s disease panel from Genomics England's PanelApp. Variant summary records are downloaded from the most recently modified versions from ClinVar, upon initialisation of this software package. Updated variant summary records are released on the first Thursday of every month.

WARNING: Variants that are not annotated, are not added to the SQLite3 variant database.

## Overview of Features

- Upload single or multiple variant files in VCF or CSV format through the flask app on your local web browser.
- Parse and store variants into a User-defined SQLite3 variant database.
- Describe variants by their true HGVS nomenclature by querying the VariantValidator REST API.
  Note: - Gene symbols and HGNC IDs are also provided by VariantValidator.
        - Variants are mapped to the GRCh38 Human Genome Reference build. 
        - HGVS transcript descriptions are provided with regard to the RefSeq MANE select transcripts.
- Annotate each varaint with the following information from ClinVar:
    - Summated variant classification
    - Associated conditions
    - Star rating
    - Review status
- Upload SQLite3 variant databases that conform with with our schema.
- Search an SQLite3 variant database by ONE of the following criteria:
    - patient/sample ID
    - variant (using the gene symbol/RefSeq/Ensembl trasncripts)
    - gene symbol
- Count the number of times a variant appears in the database.
- View variant database content in a table through the web interface.
- Apply filters and 'sort by' values to the table.
- Export the table as it exists on the web interface, in CSV format, to your local machine.

## Quick Start
1. [Index](https://rebeccasizer.github.io/Software_Engineering_Assessment_2025_AR_RW_RS/)
2. [Installation Guide](https://rebeccasizer.github.io/Software_Engineering_Assessment_2025_AR_RW_RS/installation/)
3. [User Manual](https://rebeccasizer.github.io/Software_Engineering_Assessment_2025_AR_RW_RS/user_manual/)
4. [Technical Manual](https://rebeccasizer.github.io/Software_Engineering_Assessment_2025_AR_RW_RS/technical_manual/)


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
