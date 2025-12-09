# Base image with slim Python
FROM continuumio/miniconda3:4.12.0

# Set environment variables - environment name is specified in the yml file.
ENV PYTHONUNBUFFERED=1 \
    PATH=/opt/conda/envs/sea_venv/bin:$PATH \ 
    CONDA_DEFAULT_ENV=sea_venv

# Set the working directory
WORKDIR /app

# Copy the project files into the container
COPY . /app

# Create the Conda environment
RUN conda env create -f environment.yml && \
    conda clean -a

# Create an entrypoint script
RUN echo '#!/bin/bash\n\
source /opt/conda/etc/profile.d/conda.sh\n\
conda activate sea_venv\n\
export PATH=/opt/conda/envs/sea_venv/bin:$PATH\n\
exec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Install the package in the specified environment
RUN /opt/conda/envs/sea_venv/bin/pip install --no-cache-dir -e .

# Use the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["/bin/bash"]