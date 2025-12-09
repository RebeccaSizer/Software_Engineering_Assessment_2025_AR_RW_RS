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
cd PanelPal
docker build -t SEA_2025 .
```
#### 3. Run the docker container:

```
docker run -it SEA_2025
```

#### 4. Test PanelPal is installed:

```
SEA_2025
```
This will provide you will the help message for SEA_2025 which explains the usage of each command.<br>
This message also tells you the version number of SEA_2025. E.g.:
```
SEA_2025: A webapp toolkit ClinVar annotation
version: 1.0.0 
...
```

#### 5. Start using SEA_2025
Congratulations, SEA_2025 has been installed successfully and you can now start implementing the National Test Directory for Rare Disease for your NGS Tests.

Please refer to the [User Manual](https://SEA_2025.readthedocs.io/en/latest/user_manual/) for instructions on how to use SEA_2025.