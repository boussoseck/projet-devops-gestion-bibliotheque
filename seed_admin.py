"""
Script de seed : crée un compte administrateur pré-défini directement en base.

A LANCER A L'INTERIEUR du conteneur "service-utilisateur", car c'est ce
conteneur qui a accès aux modules de l'application (models, database, auth)
et aux bonnes dépendances (passlib/bcrypt) pour générer un hash de mot de
passe compatible avec le service de login.

Utilisation (depuis la racine du projet, une fois `docker-compose up -d` lancé) :

    docker cp seed_admin.py service-utilisateur:/app/seed_admin.py
    docker-compose exec service-utilisateur python seed_admin.py

Identifiants créés par défaut (modifiables ci-dessous) :
    id_utilisateur : admin
    mot de passe   : Admin123!
"""

from app.database import SessionLocal, engine
from app import models, auth

# ---- Modifie ces valeurs si tu veux d'autres identifiants ----
ID_UTILISATEUR = "admin"
MOT_DE_PASSE = "Admin123!"
NOM = "Admin"
PRENOM = "Principal"
EMAIL = "admin@bibliotheque.local"
TELEPHONE = None
# ---------------------------------------------------------------

# S'assure que les tables existent (idempotent, sans effet si déjà créées)
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    existing = db.query(models.User).filter(
        models.User.id_utilisateur == ID_UTILISATEUR
    ).first()

    if existing:
        print(f"Un utilisateur avec l'identifiant '{ID_UTILISATEUR}' existe déjà. Rien à faire.")
    else:
        user = models.User(
            id_utilisateur=ID_UTILISATEUR,
            nom=NOM,
            prenom=PRENOM,
            email=EMAIL,
            telephone=TELEPHONE,
            type_utilisateur=models.TypeUtilisateur.personnel_administratif,
            mot_de_passe_hash=auth.hash_password(MOT_DE_PASSE),
            doit_changer_mot_de_passe=False,
        )
        db.add(user)
        db.commit()
        print("Compte administrateur créé avec succès :")
        print(f"  Identifiant  : {ID_UTILISATEUR}")
        print(f"  Mot de passe : {MOT_DE_PASSE}")
finally:
    db.close()
