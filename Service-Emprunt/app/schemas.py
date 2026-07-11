from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from .models import StatutEmprunt


class LoanCreate(BaseModel):
    user_id: int = Field(..., gt=0, description="ID interne de l'utilisateur (retourné par Service-Utilisateur)")
    isbn: str = Field(..., min_length=1, max_length=50, description="ISBN du livre à emprunter")
    duree_jours: int = Field(default=14, ge=1, le=90)


class LoanReturn(BaseModel):
    observations: Optional[str] = Field(
        default=None, max_length=255,
        description="État du livre au retour, ex: 'bon_etat', 'abime'"
    )


class LoanOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    isbn: str
    date_emprunt: datetime
    date_retour_prevue: datetime
    date_retour_reelle: Optional[datetime]
    statut: StatutEmprunt
    observations: Optional[str] = None

    class Config:
        from_attributes = True


class LoanEnriched(LoanOut):
    """Emprunt enrichi avec les infos du livre et de l'utilisateur."""
    livre: Optional[dict] = None
    utilisateur: Optional[dict] = None
