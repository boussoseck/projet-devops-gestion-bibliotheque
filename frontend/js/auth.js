const { SERVICE_UTILISATEUR: AUTH_SERVICE_UTILISATEUR } = window.API_CONFIG;

const AUTH_STORAGE_TOKEN = "bib_session_token";
const AUTH_STORAGE_USER = "bib_session_user";

window.Auth = {
  token: localStorage.getItem(AUTH_STORAGE_TOKEN) || null,
  user: JSON.parse(localStorage.getItem(AUTH_STORAGE_USER) || "null"),
};

function authIsLoggedIn() {
  return !!(window.Auth.token && window.Auth.user);
}

function authSetSession(token, user) {
  window.Auth.token = token;
  window.Auth.user = user;
  localStorage.setItem(AUTH_STORAGE_TOKEN, token);
  localStorage.setItem(AUTH_STORAGE_USER, JSON.stringify(user));
}

function authClearSession() {
  window.Auth.token = null;
  window.Auth.user = null;
  localStorage.removeItem(AUTH_STORAGE_TOKEN);
  localStorage.removeItem(AUTH_STORAGE_USER);
}

const ROLE_LABELS = {
  etudiant: "Étudiant",
  professeur: "Professeur",
  personnel_administratif: "Personnel administratif",
};

function isAdmin() {
  return window.Auth.user && window.Auth.user.type_utilisateur === "personnel_administratif";
}

/* =====================================================================
   AFFICHAGE : écran de connexion <-> application
   ===================================================================== */
function showLoginScreen() {
  document.getElementById("login-screen").classList.remove("hidden");
  document.getElementById("app").classList.add("hidden");
}

function showApp() {
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  applyRoleUI();
}

function applyRoleUI() {
  const user = window.Auth.user;
  if (!user) return;

  document.getElementById("user-name").textContent = `${user.prenom} ${user.nom} (${user.id_utilisateur})`;
  document.getElementById("user-role-badge").textContent = ROLE_LABELS[user.type_utilisateur] || user.type_utilisateur;

  const admin = isAdmin();

  // Onglets et boutons réservés à l'administration
  document.querySelectorAll('[data-role="admin"]').forEach((el) => el.classList.toggle("hidden", !admin));
  document.querySelectorAll('[data-role="user"]').forEach((el) => el.classList.toggle("hidden", admin));

  // Onglet actif par défaut : Livres pour tous
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
  document.querySelector('.tab[data-tab="livres"]').classList.add("active");
  document.getElementById("panel-livres").classList.add("active");
  document.getElementById("livres-title").textContent = admin ? "Catalogue des livres" : "Consultation du catalogue";

  // Bannière de rappel de changement de mot de passe
  document.getElementById("password-banner").classList.toggle("hidden", !user.doit_changer_mot_de_passe);

  if (window.initAppData) window.initAppData(admin);
}

/* =====================================================================
   CONNEXION
   ===================================================================== */
document.getElementById("form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id_utilisateur = document.getElementById("login-id").value.trim();
  const mot_de_passe = document.getElementById("login-password").value;
  try {
    const resp = await fetch(`${AUTH_SERVICE_UTILISATEUR}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_utilisateur, mot_de_passe }),
    });
    if (!resp.ok) {
      const detail = await parseApiError(resp, "Connexion impossible");
      throw new Error(detail);
    }
    const data = await resp.json();
    authSetSession(data.token, data.user);
    document.getElementById("form-login").reset();
    showApp();
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("link-show-register").addEventListener("click", (e) => {
  e.preventDefault();
  document.getElementById("form-login").classList.add("hidden");
  document.getElementById("form-register-admin").classList.remove("hidden");
});

document.getElementById("link-show-login").addEventListener("click", (e) => {
  e.preventDefault();
  document.getElementById("form-register-admin").classList.add("hidden");
  document.getElementById("form-login").classList.remove("hidden");
});

document.getElementById("form-register-admin").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    id_utilisateur: document.getElementById("reg-id").value.trim(),
    nom: document.getElementById("reg-nom").value.trim(),
    prenom: document.getElementById("reg-prenom").value.trim(),
    email: document.getElementById("reg-email").value.trim(),
    telephone: document.getElementById("reg-telephone").value.trim() || null,
    mot_de_passe: document.getElementById("reg-password").value,
  };
  try {
    const resp = await fetch(`${AUTH_SERVICE_UTILISATEUR}/auth/register-admin`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const detail = await parseApiError(resp, "Inscription impossible");
      throw new Error(detail);
    }
    const data = await resp.json();
    authSetSession(data.token, data.user);
    document.getElementById("form-register-admin").reset();
    showApp();
  } catch (err) {
    toast(err.message, true);
  }
});

/* =====================================================================
   DÉCONNEXION
   ===================================================================== */
document.getElementById("btn-logout").addEventListener("click", async () => {
  try {
    await fetch(`${AUTH_SERVICE_UTILISATEUR}/auth/logout`, {
      method: "POST",
      headers: { "X-Session-Token": window.Auth.token || "" },
    });
  } catch (_) { /* ignore network errors on logout */ }
  authClearSession();
  showLoginScreen();
});

/* =====================================================================
   CHANGEMENT DE MOT DE PASSE
   ===================================================================== */
function openPasswordModal() {
  document.getElementById("form-password").reset();
  openModal("modal-password");
}
document.getElementById("btn-change-password").addEventListener("click", openPasswordModal);
document.getElementById("btn-banner-change-password").addEventListener("click", openPasswordModal);

document.getElementById("form-password").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ancien = document.getElementById("pwd-ancien").value;
  const nouveau = document.getElementById("pwd-nouveau").value;
  const confirmation = document.getElementById("pwd-confirmation").value;
  if (nouveau !== confirmation) {
    toast("Les nouveaux mots de passe ne correspondent pas.", true);
    return;
  }
  try {
    const user = await api(`${AUTH_SERVICE_UTILISATEUR}/auth/change-password`, {
      method: "PUT",
      body: JSON.stringify({ ancien_mot_de_passe: ancien, nouveau_mot_de_passe: nouveau }),
    });
    window.Auth.user = user;
    localStorage.setItem(AUTH_STORAGE_USER, JSON.stringify(user));
    document.getElementById("password-banner").classList.add("hidden");
    closeModal("modal-password");
    toast("Mot de passe mis à jour avec succès.");
  } catch (err) {
    toast(err.message, true);
  }
});

/* =====================================================================
   DÉMARRAGE
   ===================================================================== */
if (authIsLoggedIn()) {
  showApp();
} else {
  showLoginScreen();
}
