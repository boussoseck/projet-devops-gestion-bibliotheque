import os
import httpx

SERVICE_LIVRE_URL = os.getenv("SERVICE_LIVRE_URL", "http://service-livre:8001")
SERVICE_UTILISATEUR_URL = os.getenv("SERVICE_UTILISATEUR_URL", "http://service-utilisateur:8002")

TIMEOUT = 5.0


async def get_book(book_id: int) -> dict | None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{SERVICE_LIVRE_URL}/books/{book_id}")
        if resp.status_code == 200:
            return resp.json()
        return None


async def get_book_by_isbn(isbn: str) -> dict | None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{SERVICE_LIVRE_URL}/books/isbn/{isbn}")
        if resp.status_code == 200:
            return resp.json()
        return None


async def get_user(user_id: int) -> dict | None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{SERVICE_UTILISATEUR_URL}/users/{user_id}")
        if resp.status_code == 200:
            return resp.json()
        return None


async def verify_session(token: str | None) -> dict | None:
    """Valide une session auprès de Service-Utilisateur et retourne le profil de l'utilisateur connecté."""
    if not token:
        return None
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{SERVICE_UTILISATEUR_URL}/auth/me",
            headers={"X-Session-Token": token},
        )
        if resp.status_code == 200:
            return resp.json()
        return None


async def adjust_book_availability(book_id: int, delta: int) -> tuple[bool, str]:
    """Retourne (succès, message)."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.patch(
            f"{SERVICE_LIVRE_URL}/books/{book_id}/availability",
            json={"delta": delta},
        )
        if resp.status_code == 200:
            return True, "ok"
        try:
            detail = resp.json().get("detail", "erreur inconnue")
        except Exception:
            detail = "erreur inconnue"
        return False, detail
