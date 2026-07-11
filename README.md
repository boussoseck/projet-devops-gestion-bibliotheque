# 📚 Bibliothèque Numérique — DIT (Dakar Institute of Technology)

Plateforme web de gestion de bibliothèque académique, basée sur une **architecture microservices**, développée dans le cadre de l'examen pratique DevOps — Master 1 Intelligence Artificielle.

## Stack technique

| Composant           | Technologie                     |
|---------------------|----------------------------------|
| Backend             | **FastAPI** (Python)             |
| Frontend            | **HTML / CSS / JavaScript** (vanilla) servi par Nginx |
| Base de données     | **PostgreSQL** (une base dédiée par microservice) |
| Conteneurisation    | **Docker** / **Docker Compose**  |
| CI/CD               | **Jenkins** (`Jenkinsfile`)      |
| Gestion de version  | **Git / GitHub**                 |

## Architecture

```
                        ┌──────────────────────────┐
                        │        Frontend            │
                        │   (HTML / CSS / JS - Nginx)│
                        │        port 8080           │
                        └─────────────┬──────────────┘
                                      │ REST / JSON
          ┌───────────────────┬──────┴────────────┬──────────────────┐
          ▼                   ▼                   ▼
 ┌─────────────────┐ ┌─────────────────────┐ ┌─────────────────┐
 │  Service-Livre   │ │ Service-Utilisateur  │ │ Service-Emprunt  │
 │   FastAPI        │ │   FastAPI            │ │   FastAPI        │
 │   port 8001      │ │   port 8002          │ │   port 8003      │
 └────────┬─────────┘ └──────────┬───────────┘ └────────┬─────────┘
          │                      │                       │ appelle en REST
          │                      │              ┌────────┴────────┐
          │                      │              │ Service-Livre    │
          │                      │              │ Service-Utilisateur│
          ▼                      ▼                       ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                      PostgreSQL (1 conteneur)                  │
 │        books_db          users_db          loans_db            │
 └──────────────────────────────────────────────────────────────┘
```

Chaque microservice possède **sa propre base de données** (isolation des données, principe microservices) et communique avec les autres **uniquement via API REST** :

- `Service-Emprunt` appelle `Service-Utilisateur` (`GET /users/{id}`) pour vérifier qu'un utilisateur existe.
- `Service-Emprunt` appelle `Service-Livre` (`GET /books/{id}` et `PATCH /books/{id}/availability`) pour vérifier et mettre à jour la disponibilité d'un livre lors d'un emprunt ou d'un retour.
- `Service-Emprunt` et `Service-Livre` appellent `Service-Utilisateur` (`GET /auth/me`) pour valider le jeton de session transmis par le frontend et connaître le rôle de l'utilisateur connecté.

## Authentification et rôles

L'accès à l'application nécessite désormais une connexion. Il n'y a **pas de JWT** : l'authentification repose sur une **session simple stockée en base** (table `sessions` dans `users_db`) — un jeton opaque (`X-Session-Token`) est renvoyé à la connexion et doit être transmis à chaque appel API. Il expire au bout de 12h ou lors de la déconnexion.

Trois rôles, trois portails dans la même interface web (l'affichage s'adapte automatiquement après connexion) :

| Rôle | Peut faire |
|------|-----------|
| **Étudiant** | Consulter le catalogue (recherche/filtre/disponibilité), consulter **ses propres emprunts** (statut, tri par date, jours restants avant retour), changer son mot de passe |
| **Professeur** | Mêmes droits que l'étudiant. *(La réservation de livres depuis le portail professeur est prévue dans une prochaine itération — non incluse dans cette version.)* |
| **Personnel administratif** | Tout ce que faisait l'interface d'origine : gestion complète des livres, des utilisateurs et des emprunts, historique global, **plus** : création de comptes (mot de passe initial = identifiant), auto-inscription (`/auth/register-admin`), consultation du journal des e-mails envoyés |

**Comptes étudiants/professeurs** : ils ne peuvent pas s'inscrire eux-mêmes. Ils sont créés exclusivement par le personnel administratif (`POST /users`), avec mot de passe initial = `id_utilisateur` (à changer à la première connexion — une bannière le rappelle dans l'interface).

**Comptes personnel administratif** : peuvent s'auto-inscrire via l'écran de connexion (« créer un compte »), avec un mot de passe de leur choix — ce qui permet aussi d'amorcer le tout premier compte admin sur une base vide.

**E-mails (simulation)** : aucun serveur SMTP n'est configuré. Chaque « envoi » (identifiants de connexion à la création d'un compte, etc.) est journalisé dans la table `email_logs`, affiché dans les logs du conteneur `service-utilisateur`, et consultable dans l'onglet **E-mails envoyés** du portail administratif.

> **Étape suivante (hors périmètre de cette version)** : import Excel/CSV en masse pour créer des comptes, module de statistiques pour le personnel administratif, réservations par les professeurs, notifications quotidiennes automatiques de rappel/retard.

## Description des microservices

### 1. Service-Livre (port 8001)
Gestion du catalogue de livres.

| Méthode | Route                          | Accès | Description                          |
|---------|---------------------------------|-------|---------------------------------------|
| POST    | `/books`                        | Admin | Ajouter un livre                     |
| GET     | `/books?q=&auteur=&editeur=&categorie=&statut=&sort_by=&order=` | Connecté (tous rôles) | Lister / rechercher / filtrer / trier |
| GET     | `/books/isbn/{isbn}`            | Interne | Détail d'un livre par ISBN (usage interne Service-Emprunt) |
| GET     | `/books/{id}`                   | Public/Interne | Détail d'un livre par ID (aussi utilisé en interne) |
| PUT     | `/books/{id}`                   | Admin | Modifier un livre                    |
| DELETE  | `/books/{id}`                   | Admin | Supprimer un livre                   |
| PATCH   | `/books/{id}/availability`      | Interne | Ajuster la disponibilité (usage interne) |
| GET     | `/health`                       | Public | Vérification de l'état du service    |

### 2. Service-Utilisateur (port 8002)
Gestion des utilisateurs, de l'authentification et des sessions (étudiants, professeurs, personnel administratif).

| Méthode | Route             | Accès | Description                        |
|---------|--------------------|-------|--------------------------------------|
| POST    | `/auth/login`      | Public | Connexion (`id_utilisateur` + mot de passe) → jeton de session |
| POST    | `/auth/logout`     | Connecté | Déconnexion (invalide le jeton) |
| GET     | `/auth/me`         | Connecté | Profil de l'utilisateur connecté (aussi utilisé en interne pour valider un jeton) |
| PUT     | `/auth/change-password` | Connecté | Changer son mot de passe |
| POST    | `/auth/register-admin` | Public | Auto-inscription réservée au personnel administratif |
| POST    | `/users`           | Admin | Créer un utilisateur (mot de passe initial auto-généré + e-mail simulé) |
| GET     | `/users?type_utilisateur=...` | Admin | Lister les utilisateurs (filtre optionnel) |
| GET     | `/users/{id}`      | Interne | Consulter le profil d'un utilisateur (usage interne) |
| PUT     | `/users/{id}`      | Admin | Modifier un utilisateur             |
| DELETE  | `/users/{id}`      | Admin | Supprimer un utilisateur            |
| GET     | `/emails?destinataire=` | Admin | Journal des e-mails simulés envoyés |
| GET     | `/health`          | Public | Vérification de l'état du service   |

### 3. Service-Emprunt (port 8003)
Gestion des emprunts de livres.

| Méthode | Route                    | Accès | Description                              |
|---------|---------------------------|-------|--------------------------------------------|
| POST    | `/loans`                  | Admin | Emprunter un livre (par `user_id` + `isbn`) |
| PUT     | `/loans/{id}/return`      | Admin | Retourner un livre (avec `observations` optionnelles) |
| GET     | `/loans?user_id=&statut=&sort_by=&order=` | Connecté | Étudiant/professeur : uniquement ses propres emprunts (le `user_id` demandé est ignoré). Admin : tous les emprunts. |
| GET     | `/loans/late`             | Admin | Détection des emprunts en retard          |
| GET     | `/loans/{id}`             | Connecté | Détail d'un emprunt (étudiant/professeur limité au sien)  |
| GET     | `/health`                 | Public | Vérification de l'état du service         |


## Structure du dépôt

```
bibliotheque-devops/
├── Service-Livre/            # Microservice FastAPI - Livres
│   ├── app/
│   │   ├── main.py           # Routes de l'API
│   │   ├── models.py         # Modèle SQLAlchemy
│   │   ├── schemas.py        # Schémas Pydantic
│   │   ├── crud.py           # Logique d'accès aux données
│   │   └── database.py       # Connexion PostgreSQL
│   ├── Dockerfile
│   └── requirements.txt
│
├── Service-Utilisateur/      # Microservice FastAPI - Utilisateurs & Authentification
│   ├── app/
│   │   ├── main.py           # Routes API (utilisateurs + /auth/*)
│   │   ├── models.py         # User, Session, EmailLog
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── auth.py           # Hash de mot de passe, sessions, simulation d'e-mails
│   │   └── database.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── Service-Emprunt/          # Microservice FastAPI - Emprunts
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── clients.py        # Appels REST vers les autres microservices (+ vérification de session)
│   │   └── database.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                 # Interface web (HTML/CSS/JS + Nginx)
│   ├── index.html
│   ├── css/style.css
│   ├── js/config.js          # URLs des microservices
│   ├── js/app.js             # Logique applicative (fetch API)
│   ├── js/auth.js            # Connexion, sessions, affichage par rôle
│   ├── nginx.conf
│   └── Dockerfile
│
├── init-db/
│   └── init.sql              # Création des 3 bases PostgreSQL au démarrage
│
├── docker-compose.yml        # Orchestration de tous les conteneurs
├── Jenkinsfile                # Pipeline CI/CD
├── .gitignore
└── README.md
```

## Installation et lancement

### Prérequis
- Docker
- Docker Compose (v2, commande `docker compose`)

### Étapes

1. **Cloner le dépôt**
   ```bash
   git clone <url-du-depot>
   cd bibliotheque-devops
   ```

2. **Lancer l'ensemble de la plateforme avec Docker Compose**
   ```bash
   docker compose up -d --build
   ```

   Cette commande va :
   - Démarrer un conteneur **PostgreSQL** et créer automatiquement les 3 bases (`books_db`, `users_db`, `loans_db`) via `init-db/init.sql`
   - Construire et démarrer les 3 microservices FastAPI
   - Construire et démarrer le frontend (Nginx)

3. **Accéder à l'application**

   | Composant             | URL                              |
   |------------------------|-----------------------------------|
   | Frontend (interface)  | http://localhost:8080             |
   | Service-Livre (docs)  | http://localhost:8001/docs        |
   | Service-Utilisateur (docs) | http://localhost:8002/docs   |
   | Service-Emprunt (docs)| http://localhost:8003/docs        |

   Chaque microservice FastAPI expose automatiquement une documentation interactive Swagger sur `/docs`.

4. **Arrêter l'application**
   ```bash
   docker compose down
   ```

   Pour supprimer également les données PostgreSQL persistées :
   ```bash
   docker compose down -v
   ```

### Lancer un microservice individuellement (développement)

```bash
cd Service-Livre
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Fonctionnement du pipeline Jenkins

Le fichier `Jenkinsfile` définit un pipeline déclaratif avec les étapes suivantes :

1. **Récupération du code** — `checkout scm` récupère le code depuis GitHub.
2. **Vérification de la structure** — contrôle la présence des fichiers essentiels (Dockerfiles, docker-compose.yml).
3. **Installation & tests** — pour chaque microservice : création d'un environnement virtuel Python, installation des dépendances, compilation (`py_compile`) pour détecter les erreurs de syntaxe.
4. **Construction des images Docker** — `docker compose build` construit les images de tous les services.
5. **Déploiement automatique** — `docker compose down` puis `docker compose up -d` redéploie la dernière version de l'application.
6. **Vérification post-déploiement** — appelle l'endpoint `/health` de chaque service pour confirmer que le déploiement a réussi.

Pour configurer le job dans Jenkins :
1. Créer un nouveau **Pipeline** dans Jenkins.
2. Pointer vers le dépôt GitHub du projet (Pipeline script from SCM).
3. Indiquer le chemin du `Jenkinsfile` (à la racine du dépôt).
4. S'assurer que l'agent Jenkins dispose de Docker et Docker Compose installés.

## Modèle de données (résumé)

**Livre** : `titre`, `auteur`, `editeur`, `isbn`, `date_edition`, `categorie`, `quantite_totale`, `quantite_disponible` (+ `statut` et `stock_badge` calculés)

**Utilisateur** : `id_utilisateur` (identifiant saisi, ex. matricule), `nom`, `prenom`, `email`, `telephone`, `type_utilisateur` (`etudiant` / `professeur` / `personnel_administratif`), `faculte`, `departement`, `classe`, `mot_de_passe_hash` (bcrypt), `doit_changer_mot_de_passe`

**Session** (`users_db`) : `token`, `user_id`, `created_at`, `expires_at` — une ligne par connexion active (durée de vie : 12h)

**EmailLog** (`users_db`) : `destinataire`, `sujet`, `corps`, `created_at` — journal des e-mails simulés

**Emprunt** : `user_id` (id interne), `isbn`, `date_emprunt`, `date_retour_prevue`, `date_retour_reelle`, `statut` (`en_cours` / `retourne` / `en_retard`), `observations` (état du livre au retour : `bon_etat` / `abime`)

## Fonctionnalités de l'interface

- **Connexion par rôle** : écran de connexion unique, portail affiché selon le rôle (étudiant / professeur / personnel administratif). Bannière de rappel si le mot de passe par défaut n'a pas encore été changé.
- **Catalogue** : consultation par tous les rôles (recherche/filtre/tri), ajout/modification/suppression réservés au personnel administratif.
- **Mes emprunts** (étudiant/professeur) : liste de ses propres emprunts, filtrable par statut, triable par date, avec jours restants / jours de retard affichés.
- **Livres, Utilisateurs, Emprunts** (personnel administratif) : affichage en tableau ("dataframe"), colonnes triables (clic sur l'en-tête, alphabétique ou date), filtres dédiés (auteur, éditeur, catégorie, statut de disponibilité, type d'utilisateur, statut d'emprunt).
- **Gestion automatique du stock** : chaque emprunt décrémente `quantite_disponible`, chaque retour l'incrémente, sans jamais dépasser `quantite_totale`. Badges 🟢 disponible / 🟡 stock faible (≤2) / 🔴 rupture, mis à jour en temps réel (sans rechargement de page).
- **Historique détaillé** (onglet dédié, admin) : tableau interactif de tous les emprunts (en cours, retournés, en retard) avec recherche libre, filtres par période / utilisateur / livre / statut, tri (utilisateur, livre, dates), badges colorés, et export **CSV** et **PDF**.
- **E-mails envoyés** (onglet dédié, admin) : journal des e-mails simulés (identifiants de connexion, etc.).
- **Charte graphique DIT** : couleurs `#104953` (principal), `#3EC6DE` (accent), `#D3D3D3` (fond), police Poppins.

## Auteurs

Projet réalisé dans le cadre de l'examen pratique DevOps — Master 1 Intelligence Artificielle — Dakar Institute of Technology (DIT), Juin/Juillet 2026.
