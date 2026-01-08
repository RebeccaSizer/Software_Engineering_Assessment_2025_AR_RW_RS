# Technical Manual

This document provides the technical manual for **SEA_2025 – Variant Database Query Tool**.  
The intended audience are **Clinical Scientists** and **Developers** who wish to understand, maintain, or extend the application.

---

## 1. GitHub Repository

The source code for SEA_2025 is available at:

- https://github.com/RebeccaSizer/Software_Engineering_Assessment_2025_AR_RW_RS.git

The repository contains the full application source code, tests, documentation, and configuration files required to run and develop SEA_2025.

---

## 2. Project Architecture

SEA_2025 is a Python-based web application built using Flask, with a modular backend architecture to support variant parsing, ClinVar annotation, database storage, and querying.

Some files have been omitted for readability.

```
Software_Engineering_Assessment_2025_AR_RW_RS 
├── app
│   ├── app.py
│   └── templates
|       ├── db_display_page.html
|       ├── db_query_page.html   
|       └── homepage.html 
├── docs
|   |── images
|   |   └── SEA_logo.png
|   ├── index.md
|   ├── installation.md  
|   |── technical_manual.md
|   └── user_manual.md
├── tests 
|   ├── test_app.py  
|   |── test_clinvar.py
|   |── test_database_functions.py
|   |── test_error_handlers.py
|   |── test_main.py
|   |── test_parser.py
|   |── test_stringify.py
|   └── test_vv_search.py
├── tools
|   |── modules
|   |   ├── clinvar_functions.py  
|   |   |── database_functions.py
|   |   └── vv_functions.py 
|   └── utils
|       ├── error_handlers.py 
|       |── logger.py
|       |── parser.py
|       |── stringify.py
|       └── timer.py
├── Dockerfile
├── environment.yml
├── Jenkins_output.txt
├── Jenkinsfile
├── LICENSE
├── main.py
├── mkdocs.yaml
├── pyproject.toml
├── README.md
└── requirements.txt 
```
---

## 3. Key Components

### 3.1 Flask Application (`app/`)

- `app.py`  
  Defines Flask routes, request handling, and communication between the frontend and backend modules.

- `templates/`  
  HTML templates rendered by Flask to provide the user interface.

### 3.2 Backend Modules (`tools/modules/`)

- `clinvar_functions.py`  
  Handles querying ClinVar Variant Summary Records and processing returned annotation data.

- `vv_functions.py`  
  Interfaces with the VariantValidator REST API to validate and normalise variant representations.

- `database_functions.py`  
  Manages SQLite database creation, updating, querying, and exporting.

### 3.3 Utilities (`tools/utils/`)

- `error_handlers.py`  
  Provides consistent error handling across the application.

- `logger.py`  
  Centralised logging for application events and errors.

- `parser.py`  
  Parses uploaded VCF and CSV files into a standard internal format.

- `stringify.py`  
  Converts data into strings for safe exportation in CSV files.

- `timer.py`  
  Used to measure and log processing times for long-running operations.

---

## 4. Database Design

### 4.1 ClinVar Variant Summary Records database (`app/clinvar/clinvar.db`)

```clinvar.db``` holds the Variant Summary Records (VSRs) from ClinVar in an **SQLite3 database**. 
Only records with 'NM_' at the beginning of their name are stored in ```clinvar.db```. 

The data stored in the following objects are parsed from each record for annotating variants:
- ChromosomeAccession
- Name
- ClinicalSignificance
- PhenotypeList
- ReviewStatus

**Note: Information from the ReviewStatus object is used to determine the star rating.**

Information from VSRs is stored in clinvar.db, in a table with the following headers:
- clinvar:
  - `nc_accession`  
  - `nm_hgvs`  
  - `clinical_significance`  
  - `conditions`  
  - `stars`  
  - `review_status`

Variant Summary Records are updated by ClinVar during the first Thursday of every month.
The date that the VSRs were last modified is stored in clinvar.db, in the following table and header:
- download
  - `last_updated`

### 4.2 Variant databases (`databases/<variant database>.db`)

SEA_2025 uses a local **SQLite3 database** to store:

- Patient identifiers  
- HGVS descriptions (NC_, NM_, NP_)
- Gene symbols and associated HGNC IDs  
- ClinVar variant annotations

SEA_2025 creates two tables in the variant databases that contain the following headers:
- patient_variant
  - `No`  
  - `patient_ID`  
  - `variant`

- variant_annotations
  - `No`  
  - `variant_NC`  
  - `variant_NM`  
  - `variant_NP`  
  - `gene`  
  - `HGNC_ID`  
  - `Classification`  
  - `Conditions`  
  - `Stars`  
  - `Review_status`

Databases can be created, updated, queried, and exported via the web interface.
Once created or uploaded, databases are stored in the **databases/** subdirectory.


**Note: Variants not found in clinvar.db are not added to the respective variant database.**

---

## 5. External APIs

SEA_2025 interacts with one external API:

### 5.1 VariantValidator REST API

- Used to validate and normalise variant representations.
- Supports multiple formats including VCF format and RefSeq/Ensembl/gene symbol-based nomenclature.

- REST API: https://rest.variantvalidator.org/  
- GitHub repository: https://github.com/openvar/rest_variantValidator

---

## 6. Running Tests

SEA_2025 includes a comprehensive suite of unit and integration tests to ensure reliability and correctness.

### 6.1 Pytest unit testing (`tests/`)

`pytest` and `pytest-cov` are installed as part of the environment setup. Pytest conducts unit tests while pytest-cov calculates the percentage of code that is being tested by the pytests.

To run all tests with coverage:

```bash
pytest tests --cov=.
```
### 6.2 Jenkins Continuous Integration testing (`Jenkinsfile`)

Jenkins performs continuous integration (CI) testing to check that our GitHub respository branches can:

- Be checked out from the repository
- Create a Python execution environment
- Install all required software and dependencies in pyproject.toml
- Execute the automated test suite

The Jenkins platform will run these CI tests on any branch that has a "**Jenkinsfile**" in the base directory. A Jenkinsfile is included in the main branch of this repo.

To run Jenkins first download the Jenkins app from: https://www.jenkins.io/download/

The installation guide can be found here: https://www.jenkins.io/doc/book/installing/

All integration tests were carried out through the Jenkins GUI at: http://localhost:8080

For more information on how to use Jenkins, please refer to their online User Handbook: https://www.jenkins.io/doc/book/using/

Jenkinsfile requires Python-3.13 to be installed locally. We installed Python-3.13 via Homebrew on Linux.

The Homebrew installation guide can be found here: https://docs.brew.sh/Installation

To install Python-3.13 via homebrew:

```bash
brew install python@3.13
```

Alternatively, you can change the filepath on line 33 of the Jenkinsfile to the location of Python-3.13 on your local machine. (Don't forget the quotation marks!!) 

**Note: The success or failure of the CI attempt will be described in the terminal stdout. Full details can be found in the console output.**

---

## 7. Logging and Error Handling

- All application logs are displayed in the terminal stdout.
- Errors and severer logs are also written to **SEA.log** files in the `logs/` directory.
- Errors are captured and presented to the user in a clear, user-friendly format within the web interface.
- Detailed stack traces and debugging information are retained in the log files to support troubleshooting and development.

---

## 8. Containerisation

SEA_2025 includes a `Dockerfile` to support reproducible and portable deployment.

- The Flask application is exposed on port **5000**.
- Containerisation ensures a consistent runtime environment across different systems and installations.

---

## 9. Development and Contribution Guidelines

Contributions to SEA_2025 are welcome and encouraged.

### 9.1 Reporting Issues

- Bugs, feature requests, or suggestions should be reported via the GitHub issue tracker.
- Issues should be labelled appropriately (e.g. `bug`, `enhancement`).
- Contributors are encouraged to indicate whether they intend to submit a fix.

### 9.2 Submitting Code Changes

1. Fork the repository and create a new feature branch.
2. Implement changes with appropriate unit and/or integration tests.
3. Follow the project coding standards:
   - NumPy-style docstrings
   - PEP8 compliance using `black` or `pylint`
   - Test coverage assessed using `coverage`
4. Ensure all automated tests pass successfully.
5. Submit a pull request with a clear and concise description of the changes.

### 9.3 Support and Contact

For questions, feedback, or support, please contact:

- **Email:** rebecca.sizer@postgrad.manchester.ac.uk  
- **GitHub Issues:** via the repository issue tracker

---

## 10. Intended Use and Limitations

SEA_2025 is intended for **research and educational purposes** only.  
It has not been validated for direct clinical reporting and should be used in accordance with local governance, validation, and quality management policies.
