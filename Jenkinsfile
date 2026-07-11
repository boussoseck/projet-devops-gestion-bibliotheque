pipeline {
    agent any

    environment {
        DOCKER_COMPOSE_FILE = "docker-compose.yml"
        REGISTRY_NAMESPACE  = "dit-bibliotheque"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        stage('Récupération du code') {
            steps {
                echo "Clonage du dépôt depuis GitHub..."
                checkout scm
            }
        }

        stage('Vérification de la structure') {
            steps {
                sh '''
                    echo "Vérification des fichiers essentiels du projet"
                    test -f docker-compose.yml
                    test -f Service-Livre/Dockerfile
                    test -f Service-Utilisateur/Dockerfile
                    test -f Service-Emprunt/Dockerfile
                    test -f frontend/Dockerfile
                '''
            }
        }

        stage('Installation & tests - Service-Livre') {
            steps {
                dir('Service-Livre') {
                    sh '''
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install --no-cache-dir -r requirements.txt
                        python -m py_compile app/*.py
                        deactivate
                    '''
                }
            }
        }

        stage('Installation & tests - Service-Utilisateur') {
            steps {
                dir('Service-Utilisateur') {
                    sh '''
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install --no-cache-dir -r requirements.txt
                        python -m py_compile app/*.py
                        deactivate
                    '''
                }
            }
        }

        stage('Installation & tests - Service-Emprunt') {
            steps {
                dir('Service-Emprunt') {
                    sh '''
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install --no-cache-dir -r requirements.txt
                        python -m py_compile app/*.py
                        deactivate
                    '''
                }
            }
        }

        stage('Construction des images Docker') {
            steps {
                sh '''
                    echo "Construction de toutes les images via Docker Compose"
                    docker compose -f ${DOCKER_COMPOSE_FILE} build
                '''
            }
        }

        stage('Déploiement (Docker Compose)') {
            steps {
                sh '''
                    echo "Arrêt de l'ancien déploiement s'il existe"
                    docker compose -f ${DOCKER_COMPOSE_FILE} down || true

                    echo "Démarrage de la nouvelle version"
                    docker compose -f ${DOCKER_COMPOSE_FILE} up -d

                    echo "Attente du démarrage des services..."
                    sleep 15
                '''
            }
        }

        stage('Vérification post-déploiement') {
            steps {
                sh '''
                    echo "Vérification des endpoints /health de chaque microservice"
                    curl -sf http://localhost:8001/health
                    curl -sf http://localhost:8002/health
                    curl -sf http://localhost:8003/health
                    curl -sf http://localhost:8080/healthz
                '''
            }
        }
    }

    post {
        success {
            echo "✅ Pipeline exécuté avec succès : Bibliothèque Numérique déployée."
        }
        failure {
            echo "❌ Le pipeline a échoué. Consultez les logs ci-dessus."
        }
        always {
            sh 'docker compose -f ${DOCKER_COMPOSE_FILE} ps || true'
        }
    }
}
