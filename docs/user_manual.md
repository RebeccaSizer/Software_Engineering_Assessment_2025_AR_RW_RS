# User Manual
---

## 1. Introduction

### 1.1 What is SEA?
SEA (Software Engineering Assessment 2025) is a web-based application designed to annotate VCF files with variant information retrieved from ClinVar. 

The tool provides a simple interface for uploading variant files and generating annotated output.

### 1.2 Who is this manual for?
- Clinical scientists  
- Trainees using SEA_2025 as part of genomic data interpretation  
- Anyone installing or using the SEA_2025 application (Docker or local)

---

## 2. Key Features

- Upload VCF files through a web interface  
- Automated retrieval of ClinVar annotation  
- Download annotated outputs in .csv format
- Query and filter database of annotated variants 
- Runs via Docker or directly on a local machine  

---

## 3. System Requirements

- Python **3.13**
- Git  
- Conda (for local installation)  
- Docker (optional but recommended)  
- Internet connection 
---

## 4. Installation Options

SEA can be installed using one of two methods:

### 4.1 Option A: Docker Deployment (Recommended)
A pre-configured Docker image ensures SEA runs consistently across systems.

### 4.2 Option B: Local Installation via Conda
Best suited for developers or users who want to modify or extend the application.

Full installation instructions are provided in the [**Installation Guide**](installation.md).  

---

## 5. Starting the Application

### 5.1 Start SEA using Docker
Run the following:

```bash
docker run -p 5000:5000 sea_app
```
Application URL:
http://localhost:5000

### 5.2 Start SEA locally (Conda)
```bash
conda activate sea_venv
python main.py
```
Then visit:
http://localhost:5000

--- 

## 6. Using SEA

### 6.1 Home Page Overview

The Home Page provides access to all core SEA functionality. Users can create new databases, query existing databases, or upload a database for querying.

#### Create or Add to a Database
This option allows users to create a new database or add variants to an existing one.

> Note: This process creates a database with ClinVar annotations for the uploaded variants, making them available for filtering, searching, and querying within SEA.

- Click **Choose files** to select one or more local variant files (files must be in `.csv` or `.vcf` format, and include the following fields: CHROM, POS, REF, ALT).
- Enter a new database name or select an existing database from the dropdown menu.
- Click **Create database** to create a new database or update the selected database with the uploaded variants.
- While the database is being created or updated, a status message (**“Loading database. Please wait…”**) will be displayed. Processing time may vary depending on file size.
- If the upload is successful, a confirmation message (**`<database_name> created/updated successfully!`**) will appear.
- Any error messages will also be displayed if the upload fails.

#### Query an Existing Database
This option allows users to query a previously created database.

- Select a database from the **Database Selection** dropdown menu.
- Click **Open Selected Database** to open the filter and search pages.
- The selected database will be loaded, allowing you to filter and search variant annotations.

#### Upload a Database for Querying
This option allows users to upload an existing database file for use within SEA.

> Note: Uploaded databases can be queried within SEA and may already contain ClinVar annotations.

- Click **Choose File** to select a local database file (file must have a `.db` extension).
- Click **Upload Database** to upload the file and make the database available for querying.
- While the database is being uploaded, a status message (**“Uploading database. Please wait…”**) will be displayed.
- If the upload is successful, a confirmation message (**`<database_name> uploaded successfully!`**) will appear.
- Any error messages will also be displayed if the upload fails.

### 6.3 Viewing and Querying an Existing Database page 

Once an existing database has been selected, it is possible to query the database by patient ID, variant, or gene symbol.

- **Search by Patient ID:** Select the patient ID from the dropdown menu or type it into the patient ID search bar, then click **Run Query**.  
- **Search by Variant:** Select the variant from the dropdown menu or type it into the variant search bar. The variant can be in one of the following formats:  
  - `NC_number:g.`  
  - `NM_number:c.`  
  - `ENST_number:c.`  
  - `gene_symbol:g.`  
  - `gene_symbol:c.`  
  Then click **Run Query**.  
- **Search by Gene Symbol:** Select the gene symbol from the dropdown menu or type it into the gene symbol search bar, then click **Run Query**.  

- If the query runs successfully, a results table similar to the following will appear:
```
 E.g.:  patient_ID | variant_NC	   | variant_NM   | variant_NP	  | gene   | HGNC_ID | Classification | Conditions	| Stars | Review_status
       ------------|---------------|--------------|---------------|--------|---------|----------------|-------------|-------|-------------------
        Patient1   | NC_000019.10: | NM_152296.5: | NP_689509.1:  | ATP1A3 | 801     | Pathogenic     | Dystonia 12 | ★    | criteria provided,
                   | g.41968837C>G | c.2767G>C    | p.(Asp923His) |        |         |                |             | 	    | single submitter
```
- If the query does not run successfully, and error messge will appear. 
---

### 6.4 Filtering Existing Database page

After querying or selecting a database, you can filter and sort the results to focus on specific variants or patients.

- Click **Display Whole Database** on the **Viewing and Querying an Existing Database** page.  
  - This will display all entries in the database and provide sorting and filtering options.  

- **Filtering:**  
  - You can filter the database by any of the following columns by selecting the desired option from the dropdown menu:  
    - `Patient_ID`  
    - `variant_NC`  
    - `variant_NM`  
    - `variant_NP`  
    - `gene`  
    - `HGNC_ID`  
    - `Classification`  
    - `Conditions`  
    - `Stars`  
    - `Review_status`  
  - Once you select a column to filter by, the dropdown will auto-populate with the available values for that column, allowing you to select a specific value.  

- **Sorting:**  
  - After filtering, you can sort the results by any of the following columns using the sort dropdown:  
    - `Patient_ID`  
    - `variant_NC`  
    - `variant_NM`  
    - `variant_NP`  
    - `gene`  
    - `HGNC_ID`  
    - `Classification`  
    - `Conditions`  
    - `Stars`  
    - `Review_status`  
  - This allows you to view filtered results in ascending or descending order based on the selected column.


### 6.4 Downloading Annotated Output

Click **Export CSV** to   
Output saved as:
annotated_<timestamp>.xlsx

## 8. Troubleshooting

"File type not supported" → Ensure .vcf or .vcf.gz  
App not loading → Check Docker or activate conda environment  
No ClinVar results → Variant absent or VCF format issue  

## 9. FAQ

Does SEA modify my original VCF? → No  
Does SEA store uploaded files? → No  

## 10. Support
Insert contact email or GitHub issues link here.