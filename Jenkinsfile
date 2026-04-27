pipeline {
    agent any

    environment {
        DOCKER_BUILDKIT = "0"
        COMPOSE_PROJECT_NAME = "mon-projet-ia"
    }

    stages {

        stage('Clone Repo') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/xaveobeeron-dev/mon-projet-ia-agent.git',
                    credentialsId: 'github-token'
            }
        }

        stage('Check Docker & Compose') {
            steps {
                sh '''
                    echo "=== Docker Version ==="
                    docker --version
                    echo "=== Docker Compose Version ==="
                    docker compose version
                '''
            }
        }

        stage('Clean Previous Deployment') {
            steps {
                sh '''
                    echo "=== Stopping previous containers ==="
                    docker compose down || true
                '''
            }
        }

        stage('Build Images') {
            steps {
                sh '''
                    echo "=== Building Docker images ==="
                    docker compose build
                '''
            }
        }

        stage('Deploy Services') {
            steps {
                sh '''
                    echo "=== Starting services ==="
                    docker compose up -d
                '''
            }
        }

        stage('Check Running Services') {
            steps {
                sh '''
                    echo "=== Running containers ==="
                    docker compose ps
                '''
            }
        }
    }

    post {
        success {
            echo "🚀 Déploiement IA réussi !"
        }
        failure {
            echo "❌ Le pipeline a échoué. Vérifie les logs."
        }
    }
}

