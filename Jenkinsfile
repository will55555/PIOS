// Dormant until a job is created on the shared Terra Jenkins box. Same checks as GitHub Actions.
pipeline {
    agent {
        docker { image 'python:3.15-slim' }
    }
    stages {
        stage('Install') {
            steps {
                sh 'python -m pip install -e ".[dev]"'
            }
        }
        stage('Check') {
            steps {
                sh 'bash scripts/check.sh'
            }
        }
    }
}
