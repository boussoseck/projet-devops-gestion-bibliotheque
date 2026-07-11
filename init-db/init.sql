-- Ce script est exécuté automatiquement au premier démarrage du conteneur PostgreSQL
-- Il crée une base de données dédiée pour chaque microservice (isolation des données)

CREATE DATABASE books_db;
CREATE DATABASE users_db;
CREATE DATABASE loans_db;

GRANT ALL PRIVILEGES ON DATABASE books_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE users_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE loans_db TO postgres;
