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
├── databases 
├── docs
|   |── images
|   |   └── SEA_logo.png
|   ├── index.md
|   ├── installation.md  
|   |── technical_manual.md
|   └── user_manual.md
├── logs
├── tests
|   |── tests_integrate
|   |   └── user_manual.md  
|   └── tests_unit
|       ├── test_clinvar.py  
|       |── test_db_tools.py
|       |── test_flask_app.py
|       |── test_parser.py
|       └── test_vv_search.py
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
├── LICENSE
├── main.py
├── mkdocs.yaml
├── pyproject.toml
├── README.md
└──  requirements.txt 
```
---

## 3. Key Components

### 3.1 Flask Application (`app/`)

- `app.py`  
  Defines Flask routes, request handling, and communication between the frontend and backend modules.

- `templates/`  
  HTML templates rendered by Flask to provide the user interface.

### 3.2 Backend Modules (`tools/`)

- `clinvar_functions.py`  
  Handles querying of the ClinVar API and processing of returned annotation data.

- `vv_functions.py`  
  Interfaces with the Variant Validator REST API to validate and normalise variant representations.

- `database_functions.py`  
  Manages SQLite database creation, updating, querying, and exporting.

### 3.3 Utilities (`tools/utils/`)

- `parser.py`  
  Parses uploaded VCF and CSV files into a standard internal format.

- `logger.py`  
  Centralised logging for application events and errors.

- `error_handlers.py`  
  Provides consistent error handling across the application.

- `timer.py`  
  Used to measure and log processing times for long-running operations.

---

## 4. Database Design

SEA_2025 uses a local **SQLite database** to store:

- Patient identifiers  
- Variant representations (NC, NM, NP)
- Gene symbols and HGNC IDs  
- ClinVar classification, conditions, review status, and star ratings

Databases can be created, updated, queried, and exported via the web interface.

---

## 5. External APIs

SEA_2025 integrates with two external APIs:

### 5.1 ClinVar API

- Used to retrieve clinical significance, conditions, review status, and star ratings for variants.
- Variants not present in ClinVar are flagged accordingly.

### 5.2 Variant Validator REST API

- Used to validate and normalise variant representations.
- Supports multiple formats including NC, NM, ENST, and gene-based nomenclature.

- REST API: https://rest.variantvalidator.org/  
- GitHub repository: https://github.com/openvar/rest_variantValidator

---

## 6. Running Tests

SEA_2025 includes a comprehensive suite of unit and integration tests to ensure reliability and correctness.

`pytest` is installed as part of the environment setup.

To run all tests:

```bash
pytest
```
SEA_2025 also uses Jenkins for continuous integration testing to check that a branch can:

- Be checked out from the repository

- Create a Python execution environment

- Install all required dependencies defined in pyproject.toml

- Execute the automated test suite

The Jenkins platform will run these CI tests on any branch that includes a Jenkinsfile (which must be so named) in its root.  A Jenkinsfile is included in the main branch of this repo.

To run Jenkins first download the Jenkin app from https://www.jenkins.io/ and navigate to the Jenkins GUI at http://<IP_ADDRESS>:8080.  Select "New Item" then "Multibranch Pipeline" Then under behaviours select 'add' then Discover branches
Strategy: Build all branches. Then click 'Save' and Jenkins will run - it will check all branches and if it finds one with a Jenkinsfile it will attempt to build it and report the outcome.

The success or failure of the CI attempt will be set out in the terminal.  Full details may be found in the Console Output.
---

## 7. Logging and Error Handling

- Application logs are written to the `logs/` directory.
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
