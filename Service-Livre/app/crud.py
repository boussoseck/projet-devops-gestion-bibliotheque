from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, schemas


def create_book(db: Session, book: schemas.BookCreate) -> models.Book:
    db_book = models.Book(
        titre=book.titre,
        auteur=book.auteur,
        editeur=book.editeur,
        isbn=book.isbn,
        date_edition=book.date_edition,
        categorie=book.categorie,
        quantite_totale=book.quantite_totale,
        quantite_disponible=book.quantite_totale,
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def get_book(db: Session, book_id: int) -> Optional[models.Book]:
    return db.query(models.Book).filter(models.Book.id == book_id).first()


def get_book_by_isbn(db: Session, isbn: str) -> Optional[models.Book]:
    return db.query(models.Book).filter(models.Book.isbn == isbn).first()


SORTABLE_FIELDS = {
    "titre": models.Book.titre,
    "auteur": models.Book.auteur,
    "editeur": models.Book.editeur,
    "isbn": models.Book.isbn,
    "categorie": models.Book.categorie,
    "quantite_disponible": models.Book.quantite_disponible,
    "date_edition": models.Book.date_edition,
    "date": models.Book.created_at,
    "id": models.Book.id,
}


def list_books(
    db: Session,
    q: Optional[str] = None,
    auteur: Optional[str] = None,
    editeur: Optional[str] = None,
    categorie: Optional[str] = None,
    statut: Optional[str] = None,
    sort_by: str = "titre",
    order: str = "asc",
):
    query = db.query(models.Book)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Book.titre.ilike(like),
                models.Book.auteur.ilike(like),
                models.Book.editeur.ilike(like),
                models.Book.isbn.ilike(like),
                models.Book.categorie.ilike(like),
            )
        )
    if auteur:
        query = query.filter(models.Book.auteur.ilike(f"%{auteur}%"))
    if editeur:
        query = query.filter(models.Book.editeur.ilike(f"%{editeur}%"))
    if categorie:
        query = query.filter(models.Book.categorie.ilike(f"%{categorie}%"))

    column = SORTABLE_FIELDS.get(sort_by, models.Book.titre)
    query = query.order_by(column.desc() if order == "desc" else column.asc())

    books = query.all()

    # Le statut (disponible / emprunte) est une propriété calculée : filtrage en mémoire
    if statut:
        books = [b for b in books if b.statut == statut]

    return books


def update_book(db: Session, book_id: int, data: schemas.BookUpdate):
    db_book = get_book(db, book_id)
    if not db_book:
        return None
    for field, value in data.dict(exclude_unset=True).items():
        setattr(db_book, field, value)
    db.commit()
    db.refresh(db_book)
    return db_book


def delete_book(db: Session, book_id: int) -> bool:
    db_book = get_book(db, book_id)
    if not db_book:
        return False
    db.delete(db_book)
    db.commit()
    return True


def adjust_availability(db: Session, book_id: int, delta: int):
    db_book = get_book(db, book_id)
    if not db_book:
        return None
    new_value = db_book.quantite_disponible + delta
    if new_value < 0 or new_value > db_book.quantite_totale:
        return "invalid"
    db_book.quantite_disponible = new_value
    db.commit()
    db.refresh(db_book)
    return db_book
