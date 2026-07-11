from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, crud, clients
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Service-Livre",
    description="Microservice de gestion des livres - Bibliothèque Numérique DIT",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Dépendance d'authentification (délègue la vérification à Service-Utilisateur)
# ============================================================

async def get_current_user(x_session_token: Optional[str] = Header(default=None)) -> dict:
    user = await clients.verify_session(x_session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée, veuillez vous reconnecter")
    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["type_utilisateur"] != "personnel_administratif":
        raise HTTPException(status_code=403, detail="Réservé au personnel administratif")
    return current_user


@app.get("/health")
def health():
    return {"status": "ok", "service": "Service-Livre"}


@app.post("/books", response_model=schemas.BookOut, status_code=201)
def create_book(book: schemas.BookCreate, db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    existing = db.query(models.Book).filter(models.Book.isbn == book.isbn).first()
    if existing:
        raise HTTPException(status_code=400, detail="Un livre avec cet ISBN existe déjà")
    return crud.create_book(db, book)


@app.get("/books", response_model=list[schemas.BookOut])
def list_books(
    q: Optional[str] = None,
    auteur: Optional[str] = None,
    editeur: Optional[str] = None,
    categorie: Optional[str] = None,
    statut: Optional[str] = None,
    sort_by: str = "titre",
    order: str = "asc",
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Liste / recherche / filtre les livres. Accessible à tout utilisateur connecté
    (étudiant, professeur, personnel administratif).
    q : recherche libre (titre, auteur, editeur, isbn, categorie)
    statut : disponible | emprunte
    sort_by : titre | auteur | editeur | isbn | categorie | quantite_disponible | date_edition | date | id
    order : asc | desc
    """
    return crud.list_books(db, q, auteur, editeur, categorie, statut, sort_by, order)


@app.get("/books/isbn/{isbn}", response_model=schemas.BookOut)
def get_book_by_isbn(isbn: str, db: Session = Depends(get_db)):
    """Utilisé par Service-Emprunt pour résoudre un ISBN en fiche livre (appel interne)."""
    db_book = crud.get_book_by_isbn(db, isbn)
    if not db_book:
        raise HTTPException(status_code=404, detail="Aucun livre ne correspond à cet ISBN")
    return db_book


@app.get("/books/{book_id}", response_model=schemas.BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    """Consultation d'une fiche livre (aussi appelé en interne par Service-Emprunt)."""
    db_book = crud.get_book(db, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Livre introuvable")
    return db_book


@app.put("/books/{book_id}", response_model=schemas.BookOut)
def update_book(book_id: int, data: schemas.BookUpdate, db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    db_book = crud.update_book(db, book_id, data)
    if not db_book:
        raise HTTPException(status_code=404, detail="Livre introuvable")
    return db_book


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    if not crud.delete_book(db, book_id):
        raise HTTPException(status_code=404, detail="Livre introuvable")


@app.patch("/books/{book_id}/availability", response_model=schemas.BookOut)
def adjust_availability(book_id: int, data: schemas.AvailabilityUpdate, db: Session = Depends(get_db)):
    """Utilisé par Service-Emprunt (appel interne) pour décrémenter/incrémenter la disponibilité."""
    result = crud.adjust_availability(db, book_id, data.delta)
    if result is None:
        raise HTTPException(status_code=404, detail="Livre introuvable")
    if result == "invalid":
        raise HTTPException(status_code=409, detail="Stock insuffisant : aucun exemplaire disponible pour cet emprunt")
    return result
