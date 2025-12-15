# SEA User Manual  
Variant Database Query Tool

---

## 1. Introduction

### What is SEA?
SEA (Software Engineering Assessment 2025) is a web-based application designed to annotate VCF files with variant information retrieved from ClinVar.  
The tool provides a simple interface for uploading variant files and generating annotated output.

### Who is this manual for?
- Clinical scientists  
- Bioinformaticians  
- Trainees using SEA as part of genomic data interpretation  
- Anyone installing or using the SEA application (Docker or local)

---

## 2. Key Features

- Upload VCF files through a clean web interface  
- Automated retrieval of ClinVar annotation  
- Download annotated outputs in spreadsheet format  
- Runs via Docker or directly on a local machine  
- Lightweight and fast interface suitable for clinical environments

---

## 3. System Requirements

- Ubuntu Linux recommended  
- Conda (for local installation)  
- Docker (optional, for containerised deployment)  
- Python 3.13 (installed automatically via Conda)

---

## 4. Installation Options

SEA can be installed using one of two methods:

### Option A: Docker Deployment (Recommended)
A pre-configured Docker image ensures SEA runs consistently across systems.

### Option B: Local Installation via Conda
Best suited for developers or users who want to modify or extend the application.

Full installation instructions are provided in the [**Installation Guide**](installation.md).  
(Insert link or filename when available.)

---

## 5. Starting the Application

### Start SEA using Docker
Run the following:

```bash
docker run -p 5000:5000 sea_app
```
Application URL:
http://localhost:5000

### Start SEA locally (Conda)
```bash
conda activate sea_venv
python app/app.py
```
Then visit:
http://localhost:5000

## 6. Using SEA

### 6.1 Home Page Overview

- Create or Add to a Database
    - Select Variant File button (Choose File)
    - Option to enter or select a database name
- Query an Existing Database
- Upload a Database for Querying

### 6.2 Uploading a VCF File

Step 1 — Press the 'choose files' button

Step 2 - Selet your file/s
Choose a .vcf or .cvs file.

Step 3 — Choose or enter a database name. 
Choosing an existing databse name will amend the variants onto that database.
Entering a new database name will generate a new database. 

SEA will parse the VCF, query ClinVar, annotate variants, and generate results.

### 6.3 Viewing Annotation Results

Results page includes:
- Variant summary  
- ClinVar annotation table  
- Download button  

Output formats:
- .xlsx  
- .csv (optional)

### 6.4 Downloading Annotated Output

Click 'Download Results'.  
Output saved as:
annotated_<timestamp>.xlsx

## 7. File Requirements

Accepted Formats:
- .vcf  
- .csv

Required VCF Fields:
CHROM, POS, REF, ALT.

## 8. Troubleshooting

"File type not supported" → Ensure .vcf or .vcf.gz  
App not loading → Check Docker or activate conda environment  
No ClinVar results → Variant absent or VCF format issue  

## 9. FAQ

Does SEA modify my original VCF? → No  
Does SEA store uploaded files? → No  
Multi-allelic variants supported? → Yes

## 10. Support
Insert contact email or GitHub issues link here.
