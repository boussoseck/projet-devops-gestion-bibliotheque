from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, crud, clients
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Service-Emprunt",
    description="Microservice de gestion des emprunts - Bibliothèque Numérique DIT",
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
    return {"status": "ok", "service": "Service-Emprunt"}


async def _enrich(loan: models.Loan) -> dict:
    livre = await clients.get_book(loan.book_id)
    utilisateur = await clients.get_user(loan.user_id)
    data = schemas.LoanOut.model_validate(loan).model_dump()
    data["livre"] = livre
    data["utilisateur"] = utilisateur
    return data


@app.post("/loans", status_code=201)
async def emprunter_un_livre(
    payload: schemas.LoanCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Seul le personnel administratif enregistre un emprunt."""
    # Vérifier que l'utilisateur existe (appel à Service-Utilisateur)
    utilisateur = await clients.get_user(payload.user_id)
    if not utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable (Service-Utilisateur)")

    # Résoudre le livre à partir de l'ISBN (appel à Service-Livre)
    livre = await clients.get_book_by_isbn(payload.isbn)
    if not livre:
        raise HTTPException(status_code=404, detail="Aucun livre ne correspond à cet ISBN (Service-Livre)")

    # Décrémenter la disponibilité côté Service-Livre (vérifie aussi le stock)
    ok, message = await clients.adjust_book_availability(livre["id"], -1)
    if not ok:
        raise HTTPException(status_code=409, detail=f"Emprunt impossible : {message}")

    db_loan = crud.create_loan(db, payload.user_id, livre["id"], payload.isbn, payload.duree_jours)
    return await _enrich(db_loan)


@app.put("/loans/{loan_id}/return")
async def retourner_un_livre(
    loan_id: int,
    payload: schemas.LoanReturn = schemas.LoanReturn(),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    db_loan = crud.get_loan(db, loan_id)
    if not db_loan:
        raise HTTPException(status_code=404, detail="Emprunt introuvable")
    if db_loan.statut == models.StatutEmprunt.retourne:
        raise HTTPException(status_code=400, detail="Ce livre a déjà été retourné")

    # Incrémenter la disponibilité côté Service-Livre
    await clients.adjust_book_availability(db_loan.book_id, +1)

    db_loan = crud.return_loan(db, loan_id, payload.observations)
    return await _enrich(db_loan)


@app.get("/loans")
def historique_emprunts(
    user_id: Optional[int] = None,
    statut: Optional[str] = None,
    sort_by: str = "date",
    order: str = "desc",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Historique des emprunts, filtrable par utilisateur ou statut.
    - Personnel administratif : voit tous les emprunts (ou filtre par user_id).
    - Étudiant / professeur : ne voit que ses propres emprunts, quel que soit le user_id demandé.
    sort_by: date | date_retour_prevue | statut | user_id | book_id | isbn | id
    order: asc | desc
    """
    crud.refresh_late_status(db)
    if current_user["type_utilisateur"] != "personnel_administratif":
        user_id = current_user["id"]
    loans = crud.list_loans(db, user_id, statut, sort_by, order)
    return [schemas.LoanOut.model_validate(loan) for loan in loans]


@app.get("/loans/late")
def detecter_les_retards(db: Session = Depends(get_db), _admin: dict = Depends(require_admin)):
    """Détection des retards : emprunts en cours dont la date prévue est dépassée."""
    late_loans = crud.get_late_loans(db)
    return [schemas.LoanOut.model_validate(loan) for loan in late_loans]


@app.get("/loans/{loan_id}")
async def get_loan(loan_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_loan = crud.get_loan(db, loan_id)
    if not db_loan:
        raise HTTPException(status_code=404, detail="Emprunt introuvable")
    if current_user["type_utilisateur"] != "personnel_administratif" and db_loan.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé à cet emprunt")
    return await _enrich(db_loan)
