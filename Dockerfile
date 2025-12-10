# Base image with Miniconda
FROM continuumio/miniconda3:25.3.1-1

# Set working directory
WORKDIR /app

# Copy dependency files first (for caching)
COPY . /app

# Create the Conda environment and install dependencies
RUN conda env create -f environment.yml && \
    conda clean -a

# Make sure conda environment is activated and pip installs your package
RUN /opt/conda/bin/conda run -n sea_venv pip install --no-cache-dir -r requirements.txt

# Set environment variables for the conda environment
ENV PATH=/opt/conda/envs/sea_venv/bin:$PATH
ENV CONDA_DEFAULT_ENV=sea_venv
ENV PYTHONUNBUFFERED=1

# Optional entrypoint to activate environment
RUN echo "#!/bin/bash\n\
source /opt/conda/etc/profile.d/conda.sh\n\
conda activate sea_venv\n\ 
&& exec bash"

EXPOSE 5000

# Default command
CMD ["python", "main.py"]