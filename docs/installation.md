# Installation Guide

## Prerequisites

#### Operating System:
SEA_2025 has been developed on Ubuntu linux systems.<br>
We cannot guarantee it's compatibility with other operating systems.

#### Docker:
SEA_2025 is configured to run using a docker container, and thus it is necessary that docker is installed on your system as a prerequisite.
```bash
sudo apt update
sudo apt install docker.io
docker --version
```

## Installation

#### 1. Clone or download this repository:

   ```
   git clone https://github.com/RebeccaSizer/Software_Engineering_Assessment_2025_AR_RW_RS
   ```

#### 2. Build the docker image:
This can take a few minutes.

```
cd Software_Engineering_Assessment_2025_AR_RW_RS
docker build -t sea_app .
```
#### 3. Run the docker container:

```
docker run -p 5000:5000 sea_app
```

#### 4. Successful installation:

If Docker runs successfully, you will see the following printout in the terminal: 

   *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
   |                                                 |
   *   Welcome to the Variant Database Query Tool!   *
   |                                                 |
   *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

#### 6. Start using SEA_2025
Congratulations, SEA_2025 has been installed successfully and you can now start annotating vcfs with variant information from ClinVar.

Please refer to the [User Manual](user_manual.md) for instructions on how to use SEA_2025.