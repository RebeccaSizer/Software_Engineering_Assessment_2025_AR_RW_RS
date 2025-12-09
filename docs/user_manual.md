# User Manual

### Installation
To install and set up SEA_2025, see the [Installation Guide](installation.md).

### Boot Up PanelPal's Docker Container
If SEA_2025 is already installed, then run the docker container.
```bash
docker run -it SEA_2025
```
# Functions
The main feature of SEA_2025 is a web-based application that annotates VCF files using information from ClinVar and uploads the results to an SQL database.

SEA_2025 retrieves variant information through the Variant Validator API and a local copy of the ClinVar database to ensure annotations are accurate and up-to-date. Consequently, SEA_2025 relies on the availability and maintenance of both ClinVar and Variant Validator; if either service is unavailable or its data is compromised, annotation functionality will be affected.

The application maintains an SQL database linking annotated variants, patient information, and metadata. On the first run, an empty database is automatically created to store annotations, and multiple databases can be generated to handle different sets of VCF files. 

