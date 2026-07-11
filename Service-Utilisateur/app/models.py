import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class TypeUtilisateur(str, enum.Enum):
    etudiant = "etudiant"
    professeur = "professeur"
    personnel_administratif = "personnel_administratif"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    id_utilisateur = Column(String(50), unique=True, nullable=False, index=True)
    nom = Column(String(150), nullable=False, index=True)
    prenom = Column(String(150), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    telephone = Column(String(30), nullable=True)
    type_utilisateur = Column(Enum(TypeUtilisateur), nullable=False)
    faculte = Column(String(150), nullable=True)
    departement = Column(String(150), nullable=True)
    classe = Column(String(100), nullable=True)
    mot_de_passe_hash = Column(String(255), nullable=False)
    doit_changer_mot_de_passe = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """Session simple stockée en base (pas de JWT) : un token = une ligne."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="sessions")


class EmailLog(Base):
    """Simulation d'envoi d'e-mails (pas de vrai SMTP) : journal consultable par l'administration."""
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    destinataire = Column(String(255), nullable=False, index=True)
    sujet = Column(String(255), nullable=False)
    corps = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
