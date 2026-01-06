# SEA_2025 – Variant Database Query Tool

<img src="images/SEA_logo.png" width="200" height="227" />

Notice: This software was developed as a part of a university project and is not currently a fully functioning and tested product. Additionally, ongoing maintenance and contributions to this code by the original developers will cease after 08/01/2026. This application was intended for clinical use. Data Protection of patient sensitive information cannot be assured. User discretion is advised.

SEA is a webapp prototype tool for annotating germline variants detected by Next-Generation Sequencing (NGS) with information from ClinVar variant summary records. Variants and annotations are stored in an SQLite3 variant database which can be viewed and queried through our flask app. It is designed to support Clinical Researchers (not Bioinformaticians) working with experimental variant data from the Parkinson’s disease panel from Genomics England's PanelApp. Variant summary records are downloaded from the most recently modified versions from ClinVar, upon initialisation of this software package. Updated variant summary records are released on the first Thursday of every month.

WARNING: Variants that are not annotated, are not added to the SQLite3 variant database.

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
- View all matching variants and their annotations through the web interface

## Getting Started
### Installation
To install and set up SEA_2025, see the [Installation Guide](https://rebeccasizer.github.io/Software_Engineering_Assessment_2025_AR_RW_RS/installation/).

### User Guide
To learn how to run each function in SEA_2025, please see the [User Manual](https://rebeccasizer.github.io/Software_Engineering_Assessment_2025_AR_RW_RS/user_manual/).

### Technical Manual
For bioinformaticians and other software developers looking to learn more about, or contribute to SEA_2025, please refer to the [Technical Manual](https://rebeccasizer.github.io/Software_Engineering_Assessment_2025_AR_RW_RS/technical_manual/)

## Continuous Integration
Automated unit and functional testing and continuous integration testing have been set up with GitHub Actions (see .github/workflows) and Jenkins CI (See Jenkinsfile).

## License
This project is licensed under the MIT License.

## Developers
- Arjun Ryatt - Trainee Bioinformatician, Oxford University Hospitals NHS Foundations Trust, NHS England
- Rebecca Sizer - Trainee Bioinformatician, North Bristol NHS Trust, NHS England
- Rachel Wellman - Trainee Bioinformatician, Royal Devon University Healthcare NHS Foundations Trust, NHS England
