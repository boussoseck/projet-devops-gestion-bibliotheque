import os
import httpx

SERVICE_UTILISATEUR_URL = os.getenv("SERVICE_UTILISATEUR_URL", "http://service-utilisateur:8002")

TIMEOUT = 5.0


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
