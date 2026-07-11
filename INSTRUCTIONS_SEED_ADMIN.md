# Créer un compte administrateur pré-défini

Un script `seed_admin.py` a été ajouté à la racine du projet pour créer
directement un compte administrateur en base de données, sans passer par
le formulaire d'inscription de l'application.

Identifiants créés par défaut (modifiables en haut du fichier `seed_admin.py`) :
- **Identifiant** : `admin`
- **Mot de passe** : `Admin123!`

## Marche à suivre

Depuis un terminal, à la racine du projet (là où se trouve `docker-compose.yml`) :

```bash
# 1. (Re)démarrer les conteneurs.
#    Si tu as déjà une base de données avec un ancien schéma qui pose problème
#    (erreur "column ... does not exist"), utilise d'abord :
#       docker-compose down -v
#    ATTENTION : cette commande supprime toutes les données existantes
#    (livres, emprunts, utilisateurs déjà créés).
docker-compose up -d

# 2. Copier le script dans le conteneur service-utilisateur
docker cp seed_admin.py service-utilisateur:/app/seed_admin.py

# 3. Exécuter le script
docker-compose exec service-utilisateur python seed_admin.py
```

Tu devrais voir :
```
Compte administrateur créé avec succès :
  Identifiant  : admin
  Mot de passe : Admin123!
```

Connecte-toi ensuite sur l'écran de login de l'application avec ces
identifiants. Le compte est créé avec `doit_changer_mot_de_passe = False`,
donc aucune bannière de changement de mot de passe ne s'affichera.

Le script est idempotent : si tu le relances, il ne recrée pas le compte
s'il existe déjà.
