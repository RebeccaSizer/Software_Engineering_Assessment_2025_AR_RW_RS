pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Set up Python env') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip

                    # Install your package + dependencies from pyproject.toml
                    # If you defined [project.optional-dependencies].dev, use ".[dev]"
                    pip install ".[dev]" || pip install .
                '''
            }
        }

        stage('Run tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest -q
                '''
            }
        }
    }
}
