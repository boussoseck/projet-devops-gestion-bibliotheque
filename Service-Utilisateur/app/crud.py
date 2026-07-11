from typing import Optional
from sqlalchemy.orm import Session
from . import models, schemas, auth


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Le mot de passe initial = id_utilisateur (haché). L'utilisateur devra le changer."""
    data = user.dict()
    password_hash = auth.hash_password(data["id_utilisateur"])
    db_user = models.User(**data, mot_de_passe_hash=password_hash, doit_changer_mot_de_passe=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_admin_user(db: Session, data: schemas.RegisterAdminRequest) -> models.User:
    """Auto-inscription du personnel administratif : mot de passe choisi par l'utilisateur."""
    db_user = models.User(
        id_utilisateur=data.id_utilisateur,
        nom=data.nom,
        prenom=data.prenom,
        email=data.email,
        telephone=data.telephone,
        type_utilisateur=models.TypeUtilisateur.personnel_administratif,
        mot_de_passe_hash=auth.hash_password(data.mot_de_passe),
        doit_changer_mot_de_passe=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_id_utilisateur(db: Session, id_utilisateur: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id_utilisateur == id_utilisateur).first()


def normalize_type_utilisateur(value: Optional[str]):
    """Accepte les valeurs techniques et libellés affichés dans le frontend."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in {"tous", "all", "tous_les_types", "tous les types"}:
        return None
    normalized = raw.lower().replace("é", "e").replace("è", "e").replace("ê", "e")
    normalized = normalized.replace(" ", "_").replace("-", "_")
    aliases = {
        "etudiant": models.TypeUtilisateur.etudiant,
        "professeur": models.TypeUtilisateur.professeur,
        "personnel_administratif": models.TypeUtilisateur.personnel_administratif,
        "administratif": models.TypeUtilisateur.personnel_administratif,
        "personnel": models.TypeUtilisateur.personnel_administratif,
        "personneladministratif": models.TypeUtilisateur.personnel_administratif,
    }
    if normalized in aliases:
        return aliases[normalized]
    for item in models.TypeUtilisateur:
        if item.value == raw:
            return item
    return raw


SORTABLE_FIELDS = {
    "nom": models.User.nom,
    "prenom": models.User.prenom,
    "id_utilisateur": models.User.id_utilisateur,
    "email": models.User.email,
    "type_utilisateur": models.User.type_utilisateur,
    "faculte": models.User.faculte,
    "departement": models.User.departement,
    "classe": models.User.classe,
    "date": models.User.created_at,
    "id": models.User.id,
}


def list_users(
    db: Session,
    type_utilisateur: Optional[str] = None,
    sort_by: str = "nom",
    order: str = "asc",
):
    query = db.query(models.User)
    type_filter = normalize_type_utilisateur(type_utilisateur)
    if type_filter:
        query = query.filter(models.User.type_utilisateur == type_filter)

    column = SORTABLE_FIELDS.get(sort_by, models.User.nom)
    query = query.order_by(column.desc() if order == "desc" else column.asc())
    return query.all()


def update_user(db: Session, user_id: int, data: schemas.UserUpdate):
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    for field, value in data.dict(exclude_unset=True).items():
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    db.delete(db_user)
    db.commit()
    return True


def change_password(db: Session, user: models.User, ancien: str, nouveau: str) -> tuple[bool, str]:
    if not auth.verify_password(ancien, user.mot_de_passe_hash):
        return False, "Ancien mot de passe incorrect"
    user.mot_de_passe_hash = auth.hash_password(nouveau)
    user.doit_changer_mot_de_passe = False
    db.commit()
    return True, "ok"


def list_emails(db: Session, destinataire: Optional[str] = None):
    query = db.query(models.EmailLog)
    if destinataire:
        query = query.filter(models.EmailLog.destinataire == destinataire)
    return query.order_by(models.EmailLog.created_at.desc()).all()
