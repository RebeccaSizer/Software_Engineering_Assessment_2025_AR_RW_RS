# Technical Manual

This is the technical manual for Sea_2025 - Variant Database Query Tool. The intended audience is clincial scientists.

## GitHub
The source code for Sea_2025 can be found here: [(https://github.com/RebeccaSizer/Software_Engineering_Assessment_2025_AR_RW_RS.git)]


## Project Architecture
Some files have been omitted for readability.
# this needs edit
```
├── Software_Engineering_Assessment_2025_AR_RW_RS 
│   ├── 
│   │   ├── 
│   │   ├── 
│   │   └── 
│   ├── 
│   ├── 
│   ├── 
│   ├── 
│   ├── 
│   ├── 
│   ├── 
│   │   └── 
│   ├── 
│   └── 
├── 
│   ├── 
│   └── 
├── 
├── pyproject.toml
├── environment.yaml
├── Jenkinsfile
├── Dockerfile
├── 
├── README.md
├── 
├── LICENSE
├── mkdocs.yaml
├── docs
│   ├── images
│   │   ├── logo.jpg
│   ├── index.md
│   ├── installation.md
│   ├── technical_manual.md
│   └── user_manual.md
├── assets
│   └── logo.jpg
└── test
    ├── 
    │   └── 
    ├── 
    ├── 
    ├── 
    ├── 
    ├── 
    ├── 
    ├── 
    ├── 
    └── 
```
## Running Tests

For peace of mind after installation or modifying the code, you can check that the functional and unit tests all pass.

Pytest is installed as a requirement during installation for this purpose. Therefore, you can simply run the following command and observe if all tests pass:
```
pytest
```
#### Output: CHANGE FOR ACTUAL RESULTS
```
(base) root@37a505720376:/app# pytest
==================================== test session starts =======================================
platform linux -- Python 3.12.4, pytest-8.3.3, pluggy-1.5.0
rootdir: /app
configfile: pyproject.toml
collected 144 items                                                                                                                                                                                   

test/db_tests/test_db.py ...                                                              [  2%]
test/test_bedfile_functions.py .....................                                      [ 16%]
test/test_check_panel.py ...........                                                      [ 24%]
test/test_compare_bedfiles.py .....                                                       [ 27%]
test/test_compare_panel_versions.py ...............                                       [ 38%]
test/test_gene_to_panels.py ........................................                      [ 65%]
test/test_generate_bed.py ...............                                                 [ 76%]
test/test_panelapp.py .....................                                               [ 90%]
test/test_variantvalidator.py .............                                               [100%]

=============================== 144 passed in 75.38s (0:01:15) =================================
```
## API Usage in Sea_2025
The majority of Sea_2025 functions work by making use of two APIs. The [ClinVar API](INSERT LINK), and the [Variant Validator REST API](https://rest.variantvalidator.org/) developed by the University of Leeds and University of Manchester. 

If you wish to know more about either API and how they work, please refer to their individual documentation or repositories. 
- [Insert link for clinvar docs 
- [Variant Validator repository available here](https://github.com/openvar/rest_variantValidator)

We welcome contributions to improve [Sea_2025](https://github.com/RebeccaSizer/Software_Engineering_Assessment_2025_AR_RW_RS.git)! Here's how you can get involved:

1. **Report Issues** - 
    - Found a bug or have a suggestion? Open an issue on our GitHub issues page. 
    - Add a label to describe the type of issue, e.g. bug, enhancement.
    - State whether you will be contributing code to fix the issue
2. **Submit Changes**
    - Fork the repository and create a new branch for your changes.
    - Make your edits and a thorough suite of tests. Note that we make use of:
      - numpy style docstrings
      - `pylint` or `black` to ensure PEP-8 compliance
      - `coverage` to check test coverage, and a .coveragerc to pass over code not requiring tests. 
    - Push up to GitHub and check that automated tests with GitHub Actions still all pass OK.
    - Submit a pull request with a clear description of your changes, and check that JenkinsCI integration testing still all works OK. 
      - Please make use of the pull request template as appropriate. Minor code changes may not require the full checklist to be fulfilled.
3. **Provide Feedback or Ask Questions**
    - For questions or feedback, please email [rebecca.sizer@postgrad.manchester.ac.uk](mailto:rebecca.sizer@postgrad.manchester.ac.uk).