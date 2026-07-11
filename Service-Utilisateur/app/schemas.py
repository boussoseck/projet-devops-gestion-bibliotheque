from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from .models import TypeUtilisateur


class UserBase(BaseModel):
    id_utilisateur: str = Field(..., min_length=1, max_length=50, description="Identifiant unique saisi par l'utilisateur (numéro étudiant, matricule employé, etc.)")
    nom: str = Field(..., min_length=1, max_length=150)
    prenom: str = Field(..., min_length=1, max_length=150)
    email: str = Field(..., min_length=3, max_length=255)
    telephone: Optional[str] = Field(default=None, max_length=30)
    type_utilisateur: TypeUtilisateur
    faculte: Optional[str] = Field(default=None, max_length=150)
    departement: Optional[str] = Field(default=None, max_length=150)
    classe: Optional[str] = Field(default=None, max_length=100)


class UserCreate(UserBase):
    """Créé par le personnel administratif. Le mot de passe n'est jamais saisi ici :
    il est généré automatiquement = id_utilisateur, puis communiqué par e-mail (simulé)."""
    pass


class UserUpdate(BaseModel):
    id_utilisateur: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = Field(default=None, min_length=3, max_length=255)
    telephone: Optional[str] = None
    type_utilisateur: Optional[TypeUtilisateur] = None
    faculte: Optional[str] = None
    departement: Optional[str] = None
    classe: Optional[str] = None


class UserOut(UserBase):
    id: int
    doit_changer_mot_de_passe: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ------------------------- Authentification -------------------------

class LoginRequest(BaseModel):
    id_utilisateur: str = Field(..., min_length=1)
    mot_de_passe: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class ChangePasswordRequest(BaseModel):
    ancien_mot_de_passe: str = Field(..., min_length=1)
    nouveau_mot_de_passe: str = Field(..., min_length=4, max_length=100)


class RegisterAdminRequest(BaseModel):
    """Auto-inscription réservée au personnel administratif."""
    id_utilisateur: str = Field(..., min_length=1, max_length=50)
    nom: str = Field(..., min_length=1, max_length=150)
    prenom: str = Field(..., min_length=1, max_length=150)
    email: str = Field(..., min_length=3, max_length=255)
    telephone: Optional[str] = Field(default=None, max_length=30)
    mot_de_passe: str = Field(..., min_length=4, max_length=100)


class EmailLogOut(BaseModel):
    id: int
    destinataire: str
    sujet: str
    corps: str
    created_at: datetime

    class Config:
        from_attributes = True
