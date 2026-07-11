from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class BookBase(BaseModel):
    titre: str = Field(..., min_length=1, max_length=255)
    auteur: str = Field(..., min_length=1, max_length=255)
    editeur: Optional[str] = Field(default=None, max_length=255)
    isbn: str = Field(..., min_length=1, max_length=50)
    date_edition: Optional[date] = None
    categorie: Optional[str] = None
    quantite_totale: int = Field(default=1, ge=1)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    titre: Optional[str] = None
    auteur: Optional[str] = None
    editeur: Optional[str] = None
    isbn: Optional[str] = None
    date_edition: Optional[date] = None
    categorie: Optional[str] = None
    quantite_totale: Optional[int] = None
    quantite_disponible: Optional[int] = None


class BookOut(BookBase):
    id: int
    quantite_disponible: int
    quantite_empruntee: int = 0
    statut: str
    stock_badge: str
    created_at: datetime

    class Config:
        from_attributes = True


class AvailabilityUpdate(BaseModel):
    delta: int  # +1 pour un retour, -1 pour un emprunt
