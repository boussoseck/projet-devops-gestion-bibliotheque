// Configuration des URLs des microservices backend.
// En développement local avec Docker Compose, les services sont exposés
// sur les ports suivants de la machine hôte.
window.API_CONFIG = {
  SERVICE_LIVRE: "http://localhost:8001",
  SERVICE_UTILISATEUR: "http://localhost:8002",
  SERVICE_EMPRUNT: "http://localhost:8003",
};
