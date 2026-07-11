from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from . import models


def create_loan(db: Session, user_id: int, book_id: int, isbn: str, duree_jours: int) -> models.Loan:
    date_retour_prevue = datetime.now(timezone.utc) + timedelta(days=duree_jours)
    db_loan = models.Loan(
        user_id=user_id,
        book_id=book_id,
        isbn=isbn,
        date_retour_prevue=date_retour_prevue,
        statut=models.StatutEmprunt.en_cours,
    )
    db.add(db_loan)
    db.commit()
    db.refresh(db_loan)
    return db_loan


def get_loan(db: Session, loan_id: int) -> Optional[models.Loan]:
    return db.query(models.Loan).filter(models.Loan.id == loan_id).first()


SORTABLE_FIELDS = {
    "date": models.Loan.date_emprunt,
    "date_retour_prevue": models.Loan.date_retour_prevue,
    "statut": models.Loan.statut,
    "user_id": models.Loan.user_id,
    "book_id": models.Loan.book_id,
    "isbn": models.Loan.isbn,
    "id": models.Loan.id,
}


def list_loans(
    db: Session,
    user_id: Optional[int] = None,
    statut: Optional[str] = None,
    sort_by: str = "date",
    order: str = "desc",
):
    query = db.query(models.Loan)
    if user_id:
        query = query.filter(models.Loan.user_id == user_id)
    if statut:
        query = query.filter(models.Loan.statut == statut)
    column = SORTABLE_FIELDS.get(sort_by, models.Loan.date_emprunt)
    query = query.order_by(column.desc() if order == "desc" else column.asc())
    return query.all()


def return_loan(db: Session, loan_id: int, observations: Optional[str] = None) -> Optional[models.Loan]:
    db_loan = get_loan(db, loan_id)
    if not db_loan:
        return None
    db_loan.date_retour_reelle = datetime.now(timezone.utc)
    db_loan.statut = models.StatutEmprunt.retourne
    if observations:
        db_loan.observations = observations
    db.commit()
    db.refresh(db_loan)
    return db_loan


def refresh_late_status(db: Session):
    """Détecte et met à jour les emprunts en retard (date prévue dépassée, non retournés)."""
    now = datetime.now(timezone.utc)
    late_loans = (
        db.query(models.Loan)
        .filter(
            models.Loan.statut == models.StatutEmprunt.en_cours,
            models.Loan.date_retour_prevue < now,
        )
        .all()
    )
    for loan in late_loans:
        loan.statut = models.StatutEmprunt.en_retard
    if late_loans:
        db.commit()
    return late_loans


def get_late_loans(db: Session):
    refresh_late_status(db)
    return (
        db.query(models.Loan)
        .filter(models.Loan.statut == models.StatutEmprunt.en_retard)
        .order_by(models.Loan.date_retour_prevue)
        .all()
    )
