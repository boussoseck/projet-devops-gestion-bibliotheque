from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.sql import func
from .database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String(255), nullable=False, index=True)
    auteur = Column(String(255), nullable=False, index=True)
    editeur = Column(String(255), nullable=True, index=True)
    isbn = Column(String(50), unique=True, nullable=False, index=True)
    date_edition = Column(Date, nullable=True)
    categorie = Column(String(100), nullable=True, index=True)
    quantite_totale = Column(Integer, nullable=False, default=1)
    quantite_disponible = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def quantite_empruntee(self) -> int:
        return self.quantite_totale - self.quantite_disponible

    @property
    def statut(self) -> str:
        """disponible : au moins 1 exemplaire libre / emprunte : plus aucun exemplaire libre"""
        return "disponible" if self.quantite_disponible > 0 else "emprunte"

    @property
    def stock_badge(self) -> str:
        """Indicateur visuel du stock : ok (>2) / faible (1-2) / rupture (0)"""
        if self.quantite_disponible == 0:
            return "rupture"
        if self.quantite_disponible <= 2:
            return "faible"
        return "ok"
