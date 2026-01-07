/**
 * Jenkinsfile
 *
 * This Jenkins pipeline defines a continuous integration (CI) workflow
 * for testing whether the current Git branch can successfully build
 * and run the project.
 *
 * The pipeline performs the following steps:
 * 1. Checks out the source code from the current branch
 * 2. Creates a Python virtual environment
 * 3. Installs project dependencies from pyproject.toml
 * 4. Runs the automated test suite using pytest
 *
 * If any step fails, the pipeline terminates and the build is marked as FAILED.
 * Jenkins will only attempt to build and run the project from branches that contain in
 * the root of the project a file that is called exactly "Jenkinsfile" 
 * with no file extensions.
 * This docstring and the inline comments were written with assistance from ChatGPT.
 */

pipeline {

    /**
     * Specifies where the pipeline should run.
     * 'any' allows Jenkins to run this job on any available agent.
     */
    agent any


    /*
     * Creat a directory for the virtual environment.
     */
    environment {
        VENV_DIR = ".venv"
    }

    /**
     * Stages represent logical steps in the CI process.
     * Each stage is displayed separately in the Jenkins UI.
     */
    stages {

        /**
         * Checkout stage
         *
         * Retrieves the source code from the Git repository.
         * Jenkins automatically checks out the branch that triggered the build.
         */
        stage('Checkout') {
            steps {
                // Uses the SCM configuration defined in the Jenkins job
                checkout scm
            }
        }

        /**
         * Set up Python environment stage
         *
         * Creates an isolated Python virtual environment and installs
         * all required dependencies defined in pyproject.toml.
         */
        stage('Set up Python env') {
            steps {
                sh '''
                    # Check the version of Python in use
                    python --version

                    # Create a Python virtual environment in the workspace
                    python -m venv ${VENV_DIR}

                    # Activate the virtual environment
                    . ${VENV_DIR}/bin/activate

                    # Upgrade pip to the latest version
                    pip install --upgrade pip setuptools wheel

                    # Install project dependencies
                    pip install .
                '''
            }
        }

        /**
         * Run tests stage
         *
         * Executes the automated test suite using pytest.
         * If any test fails, pytest returns a non-zero exit code,
         * causing the Jenkins build to fail.
         */
        stage('Run tests') {
            steps {
                sh '''
                    # Activate the virtual environment
                    . ${VENV_DIR}/bin/activate

                    # Run the test suite in quiet mode
                    pytest tests --cov=. --cov-report=xml
                '''
            }
        }
    }
    post {
        always {
            echo 'CI pipeline finished.'
        }
        success {
            echo 'All tests passed.'
        }
        failure {
            echo 'CI failed.'
        }
    }
}