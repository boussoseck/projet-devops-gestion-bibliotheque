import os
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, crud, auth
from .database import engine, get_db, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Service-Utilisateur",
    description="Microservice de gestion des utilisateurs et de l'authentification - Bibliothèque Numérique DIT",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Compte administrateur par défaut
# ============================================================

@app.on_event("startup")
def seed_default_admin():
    """Crée automatiquement le compte personnel administratif par défaut si absent.

    Cela évite de bloquer le démarrage de l'application lorsqu'aucun compte
    administratif n'a encore pu être créé depuis l'écran de connexion.
    """
    if os.getenv("SEED_DEFAULT_ADMIN", "true").lower() not in {"1", "true", "yes", "oui"}:
        return

    admin_id = os.getenv("DEFAULT_ADMIN_ID", "admin")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin123!")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@bibliotheque.com")

    db = SessionLocal()
    try:
        existing_admin = crud.get_user_by_id_utilisateur(db, admin_id)
        if existing_admin:
            # Version stable v2 : le compte admin par défaut doit toujours permettre la connexion.
            # On corrige aussi les anciennes bases qui contenaient admin@bibliotheque.local.
            existing_admin.email = admin_email
            existing_admin.type_utilisateur = models.TypeUtilisateur.personnel_administratif
            existing_admin.mot_de_passe_hash = auth.hash_password(admin_password)
            existing_admin.doit_changer_mot_de_passe = False
            db.commit()
            print(f"[SEED] Compte personnel administratif par défaut vérifié : {admin_id}")
            return
        existing_email = db.query(models.User).filter(models.User.email == admin_email).first()
        if existing_email:
            existing_email.id_utilisateur = admin_id
            existing_email.type_utilisateur = models.TypeUtilisateur.personnel_administratif
            existing_email.mot_de_passe_hash = auth.hash_password(admin_password)
            existing_email.doit_changer_mot_de_passe = False
            db.commit()
            print(f"[SEED] Compte personnel administratif par défaut récupéré par email : {admin_id}")
            return
        user = models.User(
            id_utilisateur=admin_id,
            nom=os.getenv("DEFAULT_ADMIN_NOM", "Admin"),
            prenom=os.getenv("DEFAULT_ADMIN_PRENOM", "Principal"),
            email=admin_email,
            telephone=os.getenv("DEFAULT_ADMIN_TELEPHONE") or None,
            type_utilisateur=models.TypeUtilisateur.personnel_administratif,
            mot_de_passe_hash=auth.hash_password(admin_password),
            doit_changer_mot_de_passe=False,
        )
        db.add(user)
        db.commit()
        print(f"[SEED] Compte personnel administratif par défaut créé : {admin_id}")
    finally:
        db.close()


# ============================================================
# Dépendances d'authentification / autorisation
# ============================================================

def get_current_user(
    x_session_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    user = auth.get_user_from_token(db, x_session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée, veuillez vous reconnecter")
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.type_utilisateur != models.TypeUtilisateur.personnel_administratif:
        raise HTTPException(status_code=403, detail="Réservé au personnel administratif")
    return current_user


@app.get("/health")
def health():
    return {"status": "ok", "service": "Service-Utilisateur"}


# ============================================================
# Authentification
# ============================================================

@app.post("/auth/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_id_utilisateur(db, payload.id_utilisateur)
    if not user or not auth.verify_password(payload.mot_de_passe, user.mot_de_passe_hash):
        raise HTTPException(status_code=401, detail="Identifiant ou mot de passe incorrect")
    session = auth.create_session(db, user)
    return {"token": session.token, "user": user}


@app.post("/auth/logout", status_code=204)
def logout(x_session_token: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    auth.delete_session(db, x_session_token)
    return None


@app.get("/auth/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.put("/auth/change-password", response_model=schemas.UserOut)
def change_password(
    payload: schemas.ChangePasswordRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok, message = crud.change_password(db, current_user, payload.ancien_mot_de_passe, payload.nouveau_mot_de_passe)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return current_user


@app.post("/auth/register-admin", response_model=schemas.LoginResponse, status_code=201)
def register_admin(payload: schemas.RegisterAdminRequest, db: Session = Depends(get_db)):
    """Auto-inscription réservée au personnel administratif (étudiants/professeurs ne peuvent pas s'inscrire eux-mêmes)."""
    if crud.get_user_by_id_utilisateur(db, payload.id_utilisateur):
        raise HTTPException(status_code=400, detail="Cet identifiant utilisateur est déjà utilisé")
    existing_email = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Un utilisateur avec cet email existe déjà")
    user = crud.create_admin_user(db, payload)
    session = auth.create_session(db, user)
    return {"token": session.token, "user": user}


# ============================================================
# Gestion des utilisateurs (réservée au personnel administratif)
# ============================================================

@app.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    existing_email = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Un utilisateur avec cet email existe déjà")
    existing_id_utilisateur = db.query(models.User).filter(models.User.id_utilisateur == user.id_utilisateur).first()
    if existing_id_utilisateur:
        raise HTTPException(status_code=400, detail="Cet identifiant utilisateur (id_utilisateur) est déjà utilisé")
    db_user = crud.create_user(db, user)

    # Envoi (simulé) de l'e-mail de bienvenue avec les identifiants de connexion
    auth.log_email(
        db,
        destinataire=db_user.email,
        sujet="Vos accès à la Bibliothèque Numérique — DIT",
        corps=(
            f"Bonjour {db_user.prenom} {db_user.nom},\n\n"
            f"Un compte a été créé pour vous sur la plateforme de la Bibliothèque Numérique DIT.\n"
            f"Nom du compte : {db_user.id_utilisateur}\n"
            f"Mot de passe par défaut : {db_user.id_utilisateur}\n\n"
            f"Merci de vous connecter et de changer votre mot de passe dès que possible."
        ),
    )
    return db_user


@app.get("/users", response_model=list[schemas.UserOut])
def list_users(
    type_utilisateur: Optional[str] = Query(default=None, description="Filtre: etudiant | professeur | personnel_administratif | vide/tous"),
    sort_by: str = "nom",
    order: str = "asc",
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    """
    sort_by: nom | prenom | id_utilisateur | email | type_utilisateur | faculte | departement | classe | date | id
    order: asc | desc
    """
    return crud.list_users(db, type_utilisateur, sort_by, order)


@app.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    """Consultation du profil utilisateur (usage interne : appelé par Service-Emprunt/Service-Livre sans session)."""
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return db_user


@app.put("/users/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, data: schemas.UserUpdate, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    db_user = crud.update_user(db, user_id, data)
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return db_user


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    if not crud.delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")


# ============================================================
# Journal des e-mails simulés (réservé au personnel administratif)
# ============================================================

@app.get("/emails", response_model=list[schemas.EmailLogOut])
def list_emails(destinataire: Optional[str] = None, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)):
    return crud.list_emails(db, destinataire)
