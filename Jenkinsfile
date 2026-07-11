pipeline {
    agent any

    environment {
        DOCKER_COMPOSE_FILE = "docker-compose.yml"
        REGISTRY_NAMESPACE = "dit-bibliotheque"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    stages {
        stage('Récupération du code') {
            steps {
                echo "Clonage du dépôt depuis GitHub..."
                checkout scm
            }
        }

        stage('Vérification des outils') {
            steps {
                sh '''
                    echo "Vérification des outils nécessaires..."
                    git --version
                    python3 --version
                    pip3 --version
                    docker --version
                    docker-compose --version
                    curl --version
                '''
            }
        }

        stage('Vérification de la structure') {
            steps {
                sh '''
                    echo "Vérification des fichiers essentiels du projet..."
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
                        rm -rf venv
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install --no-cache-dir -r requirements.txt
                        python -m py_compile app/*.py
                    '''
                }
            }
        }

        stage('Installation & tests - Service-Utilisateur') {
            steps {
                dir('Service-Utilisateur') {
                    sh '''
                        rm -rf venv
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install --no-cache-dir -r requirements.txt
                        python -m py_compile app/*.py
                    '''
                }
            }
        }

        stage('Installation & tests - Service-Emprunt') {
            steps {
                dir('Service-Emprunt') {
                    sh '''
                        rm -rf venv
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install --no-cache-dir -r requirements.txt
                        python -m py_compile app/*.py
                    '''
                }
            }
        }

        stage('Construction des images Docker') {
            steps {
                sh '''
                    echo "Construction des images de l'application..."

                    docker-compose -f ${DOCKER_COMPOSE_FILE} build \
                        service-utilisateur \
                        service-livre \
                        service-emprunt \
                        frontend
                '''
            }
        }

        stage('Déploiement avec Docker Compose') {
            steps {
                sh '''
                    echo "Démarrage ou mise à jour des services..."

                    docker-compose -f ${DOCKER_COMPOSE_FILE} up -d \
                        postgres \
                        pgadmin \
                        service-utilisateur \
                        service-livre \
                        service-emprunt \
                        frontend

                    echo "Attente du démarrage des services..."
                    sleep 15
                '''
            }
        }

        stage('Vérification post-déploiement') {
            steps {
                sh '''
                    echo "Vérification des endpoints de santé..."

                    curl --fail --show-error \
                        --retry 10 --retry-delay 3 \
                        http://service-livre:8001/health

                    curl --fail --show-error \
                        --retry 10 --retry-delay 3 \
                        http://service-utilisateur:8002/health

                    curl --fail --show-error \
                        --retry 10 --retry-delay 3 \
                        http://service-emprunt:8003/health

                    curl --fail --show-error \
                        --retry 10 --retry-delay 3 \
                        http://bibliotheque-frontend/healthz
                '''
            }
        }
    }

    post {
        success {
            echo " Pipeline exécuté avec succès : Bibliothèque Numérique déployée."
        }

        failure {
            echo " Le pipeline a échoué. Consultez les logs ci-dessus."
        }

        always {
            sh '''
                docker-compose -f ${DOCKER_COMPOSE_FILE} ps || true
            '''
        }
    }
}