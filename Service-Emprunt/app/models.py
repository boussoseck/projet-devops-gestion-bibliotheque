import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from .database import Base


class StatutEmprunt(str, enum.Enum):
    en_cours = "en_cours"
    retourne = "retourne"
    en_retard = "en_retard"


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)          # id interne Service-Utilisateur
    book_id = Column(Integer, nullable=False, index=True)          # id interne Service-Livre (résolu depuis l'ISBN)
    isbn = Column(String(50), nullable=False, index=True)          # ISBN saisi à l'emprunt (affichage/recherche)
    date_emprunt = Column(DateTime(timezone=True), server_default=func.now())
    date_retour_prevue = Column(DateTime(timezone=True), nullable=False)
    date_retour_reelle = Column(DateTime(timezone=True), nullable=True)
    statut = Column(Enum(StatutEmprunt), nullable=False, default=StatutEmprunt.en_cours)
    observations = Column(String(255), nullable=True)              # ex: "bon_etat", "abime", commentaire libre
