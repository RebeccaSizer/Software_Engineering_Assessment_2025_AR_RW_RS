# Installation Guide  
**SEA_2025 – Variant Database Query Tool**

---

## 1. Overview
SEA_2025 is a web application designed to annotate VCF files with ClinVar variant information.  
This guide explains how to install SEA_2025 using **Docker (recommended)** or **locally on your machine**.

### Operating System:
SEA_2025 has been developed on Ubuntu linux systems.<br>
We cannot guarantee it's compatibility with other operating systems.

---

## 2. Prerequisites

### Operating System
SEA_2025 has been developed and tested on **Ubuntu Linux** systems.  
Compatibility with other operating systems cannot be guaranteed.

### System Requirements
- Python **3.13**
- Git  
- Conda (for local installation)  
- Docker (optional but recommended)  
- Internet connection  

---

## 3. Repository Setup

Clone or download the SEA_2025 repository:

```bash
git clone https://github.com/RebeccaSizer/Software_Engineering_Assessment_2025_AR_RW_RS
cd Software_Engineering_Assessment_2025_AR_RW_RS
```
---

## 4. Installation using Docker
### 4.1 Install Docker:
SEA_2025 is configured to run using a docker container, and thus it is necessary that docker is installed on your system as a prerequisite. 
```bash
sudo apt update
sudo apt install docker.io
docker --version
```
If Docker prints a version number, installation was successful.

### 4.2 Build the docker image:
This can take a few minutes.

```
docker build -t sea_app .
```
Note on Docker permissions:
On some systems (particularly shared or managed machines), Docker commands may require
administrative privileges. If you encounter a "permission denied while trying to connect
to the Docker daemon" error, prefix Docker commands with `sudo`.

If you do not have permission to use `sudo`, please contact your system administrator.
### 4.3 Run the docker container:

```
docker run -p 5000:5000 sea_app
```

### 4.4 Successful installation:

If Docker runs successfully, you will see the following printout in the terminal: 
```
   *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
   |                                                 |
   *   Welcome to the Variant Database Query Tool!   *
   |                                                 |
   *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
```
The application will now be available at:
http://127.0.0.1:5000

### 4.5 Start using SEA_2025
Congratulations, SEA_2025 has been installed successfully and you can now start annotating vcfs with variant information from ClinVar.

Please refer to the [User Manual](user_manual.md) for instructions on how to use SEA_2025.

---

## 5. Local Installation (Conda)

SEA_2025 includes a pre-configured `environment.yml` file that sets up a dedicated
Conda environment for running the application locally.

### 5.1 Ensure Conda is installed

If you do not already have Conda on your system, install **Miniconda** or **Anaconda**:

(https://docs.conda.io/en/latest/)

### 5.2 Create the environment

From the root folder of the repository:

```bash
conda env create -f environment.yml
```

This will create an environment named:

```
sea_venv
```

### 5.3 Activate the environment

```bash
conda activate sea_venv
```

### 5.4 Install the SEA_2025 package

Once the environment is activated, install the application and its Python
dependencies using pip:

```bash
pip install .
```

*(This installs the local package defined by your `pyproject.toml`.)*

### 5.5 Run the application locally

```bash
python main.py
```

### 5.6 Access the web app

By default, the app will run on:

```
http://localhost:5000
```

You can now begin using SEA_2025 to annotate VCF files locally.

---