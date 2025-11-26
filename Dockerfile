# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/


#define the build argument for python version
ARG PYTHON_VERSION=3.13
#specify the base image
FROM python:${PYTHON_VERSION}-slim AS base
#Specify the port number the container will listen on
EXPOSE 5000

# Prevents Python from writing .pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Prevents Python from buffering stdout and stderr. This ensures that logs are outputted in real-time.
ENV PYTHONUNBUFFERED=1

# Set the working directory to the top level of the project
WORKDIR /Software_Engineering_Assessment_2025_AR_RW_RS

#25/11/2025
# Mount the current host directory to the container's /app directory
# This allows for easy development and testing without rebuilding the image.
#CHECK THIS IS CORRECT 
VOLUME /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser
RUN chown appuser:appuser -R /app
RUN chmod 777 -R /app

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt 


# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY . .

# Start the container by running a specific Python script. The "tail", "-f", "/dev/null" command allows the container to keep running in detached mode untill it it killed manually

# Set the working directory to /app
WORKDIR ./app

CMD ["python", "main.py", "tail", "-f", "/dev/null"]