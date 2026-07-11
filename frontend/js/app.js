const { SERVICE_LIVRE, SERVICE_UTILISATEUR, SERVICE_EMPRUNT } = window.API_CONFIG;

/* =====================================================================
   UTILITAIRES GÉNÉRAUX
   ===================================================================== */

function formatApiErrorDetail(detail, fallback = "Une erreur est survenue") {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === "string") return item;
      const field = Array.isArray(item.loc) ? item.loc.filter((x) => x !== "body").join(".") : "";
      const msg = item.msg || item.message || JSON.stringify(item);
      return field ? `${field} : ${msg}` : msg;
    }).join(" | ");
  }
  if (typeof detail === "object") {
    if (detail.msg) return detail.msg;
    if (detail.message) return detail.message;
    return JSON.stringify(detail);
  }
  return String(detail);
}

async function parseApiError(resp, fallback) {
  try {
    const data = await resp.json();
    return formatApiErrorDetail(data.detail || data.message || data, fallback);
  } catch (_) {
    return fallback;
  }
}
function toast(message, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 3200);
}

async function api(url, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (window.Auth && window.Auth.token) headers["X-Session-Token"] = window.Auth.token;
  const resp = await fetch(url, { ...options, headers });
  if (resp.status === 401) {
    authClearSession();
    showLoginScreen();
    toast("Votre session a expiré, veuillez vous reconnecter.", true);
    throw new Error("Session expirée");
  }
  if (!resp.ok) {
    const detail = await parseApiError(resp, `Erreur ${resp.status}`);
    throw new Error(detail);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function fmtDate(iso, withTime = false) {
  if (!iso) return "—";
  const d = new Date(iso);
  const opts = withTime
    ? { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "2-digit", month: "short", year: "numeric" };
  return d.toLocaleDateString("fr-FR", opts);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function debounce(fn, delay) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

function daysBetween(startIso, endIso) {
  if (!startIso) return 0;
  const start = new Date(startIso);
  const end = endIso ? new Date(endIso) : new Date();
  return Math.max(0, Math.round((end - start) / 86400000));
}

/* =====================================================================
   ONGLETS
   ===================================================================== */
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");
    if (tab.dataset.tab === "historique") loadHistorique();
    if (tab.dataset.tab === "mesemprunts") loadMesEmprunts();
    if (tab.dataset.tab === "emails") loadEmails();
  });
});

/* =====================================================================
   TRI GÉNÉRIQUE DES EN-TÊTES DE TABLEAU
   ===================================================================== */
function initSortableHeaders(tableId, state, reload) {
  const table = document.getElementById(tableId);
  table.querySelectorAll("th[data-sort]").forEach((th) => {
    th.dataset.label = th.textContent.trim();
    th.addEventListener("click", () => {
      const col = th.dataset.sort;
      if (state.sortBy === col) state.order = state.order === "asc" ? "desc" : "asc";
      else { state.sortBy = col; state.order = "asc"; }
      updateSortArrows(table, state);
      reload();
    });
  });
  updateSortArrows(table, state);
}

function updateSortArrows(table, state) {
  table.querySelectorAll("th[data-sort]").forEach((th) => {
    const active = th.dataset.sort === state.sortBy;
    const arrow = active ? (state.order === "asc" ? " ▲" : " ▼") : "";
    th.textContent = th.dataset.label + arrow;
  });
}

/* =====================================================================
   MODALES
   ===================================================================== */
function openModal(id) { document.getElementById(id).classList.add("open"); }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }
document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.addEventListener("click", () => btn.closest(".modal-overlay").classList.remove("open"));
});
document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.classList.remove("open"); });
});

/* =====================================================================
   LIVRES  — Service-Livre
   ===================================================================== */
const booksSort = { sortBy: "titre", order: "asc" };
let booksCache = [];

function buildBooksUrl() {
  const params = new URLSearchParams();
  const q = document.getElementById("search-books").value.trim();
  const auteur = document.getElementById("filter-books-auteur").value.trim();
  const editeur = document.getElementById("filter-books-editeur").value.trim();
  const categorie = document.getElementById("filter-books-categorie").value.trim();
  const statut = document.getElementById("filter-books-statut").value;
  if (q) params.set("q", q);
  if (auteur) params.set("auteur", auteur);
  if (editeur) params.set("editeur", editeur);
  if (categorie) params.set("categorie", categorie);
  if (statut) params.set("statut", statut);
  params.set("sort_by", booksSort.sortBy);
  params.set("order", booksSort.order);
  return `${SERVICE_LIVRE}/books?${params.toString()}`;
}

async function loadBooks() {
  const tbody = document.getElementById("books-tbody");
  try {
    const books = await api(buildBooksUrl());
    booksCache = books;
    if (!books.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">Aucun livre trouvé.</td></tr>`;
      return;
    }
    tbody.innerHTML = books.map(renderBookRow).join("");
    tbody.querySelectorAll("[data-edit-book]").forEach((b) => b.addEventListener("click", () => editBook(b.dataset.editBook)));
    tbody.querySelectorAll("[data-delete-book]").forEach((b) => b.addEventListener("click", () => deleteBook(b.dataset.deleteBook)));
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-state">Impossible de charger le Service-Livre (${e.message}).</td></tr>`;
  }
}

const STOCK_BADGE = {
  ok: { emoji: "🟢", cls: "badge-green", label: "Disponible" },
  faible: { emoji: "🟡", cls: "badge-amber", label: "Stock faible" },
  rupture: { emoji: "🔴", cls: "badge-red", label: "Rupture" },
};

function renderBookRow(b) {
  const badge = STOCK_BADGE[b.stock_badge] || STOCK_BADGE.ok;
  const actions = isAdmin()
    ? `<td class="col-actions">
        <button class="btn-mini" data-edit-book="${b.id}">Modifier</button>
        <button class="btn-mini danger" data-delete-book="${b.id}">Supprimer</button>
      </td>`
    : "";
  return `
    <tr>
      <td><strong>${escapeHtml(b.titre)}</strong></td>
      <td>${escapeHtml(b.auteur)}</td>
      <td>${escapeHtml(b.editeur || "—")}</td>
      <td>${escapeHtml(b.isbn)}</td>
      <td>${escapeHtml(b.categorie || "—")}</td>
      <td>${b.date_edition ? fmtDate(b.date_edition) : "—"}</td>
      <td><span class="badge ${badge.cls}">${badge.emoji} ${b.quantite_disponible}/${b.quantite_totale}</span></td>
      ${actions}
    </tr>`;
}

document.getElementById("btn-new-book").addEventListener("click", () => {
  document.getElementById("form-book").reset();
  document.getElementById("book-id").value = "";
  openModal("modal-book");
});

function editBook(id) {
  const b = booksCache.find((x) => String(x.id) === String(id));
  if (!b) return;
  document.getElementById("book-id").value = b.id;
  document.getElementById("book-titre").value = b.titre;
  document.getElementById("book-auteur").value = b.auteur;
  document.getElementById("book-editeur").value = b.editeur || "";
  document.getElementById("book-isbn").value = b.isbn;
  document.getElementById("book-date-edition").value = b.date_edition || "";
  document.getElementById("book-categorie").value = b.categorie || "";
  document.getElementById("book-quantite").value = b.quantite_totale;
  openModal("modal-book");
}

async function deleteBook(id) {
  if (!confirm("Supprimer définitivement ce livre ?")) return;
  try {
    await api(`${SERVICE_LIVRE}/books/${id}`, { method: "DELETE" });
    toast("Livre supprimé.");
    loadBooks();
  } catch (e) { toast(e.message, true); }
}

document.getElementById("form-book").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("book-id").value;
  const payload = {
    titre: document.getElementById("book-titre").value,
    auteur: document.getElementById("book-auteur").value,
    editeur: document.getElementById("book-editeur").value || null,
    isbn: document.getElementById("book-isbn").value,
    date_edition: document.getElementById("book-date-edition").value || null,
    categorie: document.getElementById("book-categorie").value || null,
    quantite_totale: parseInt(document.getElementById("book-quantite").value, 10),
  };
  try {
    if (id) { await api(`${SERVICE_LIVRE}/books/${id}`, { method: "PUT", body: JSON.stringify(payload) }); toast("Livre mis à jour."); }
    else { await api(`${SERVICE_LIVRE}/books`, { method: "POST", body: JSON.stringify(payload) }); toast("Livre ajouté au catalogue."); }
    closeModal("modal-book");
    loadBooks();
  } catch (e) { toast(e.message, true); }
});

["search-books"].forEach((id) => document.getElementById(id).addEventListener("input", debounce(loadBooks, 350)));
["filter-books-auteur", "filter-books-editeur", "filter-books-categorie"].forEach((id) =>
  document.getElementById(id).addEventListener("input", debounce(loadBooks, 350))
);
document.getElementById("filter-books-statut").addEventListener("change", loadBooks);
document.getElementById("btn-reset-books").addEventListener("click", () => {
  document.getElementById("search-books").value = "";
  document.getElementById("filter-books-auteur").value = "";
  document.getElementById("filter-books-editeur").value = "";
  document.getElementById("filter-books-categorie").value = "";
  document.getElementById("filter-books-statut").value = "";
  loadBooks();
});

initSortableHeaders("table-books", booksSort, loadBooks);

/* =====================================================================
   UTILISATEURS  — Service-Utilisateur
   ===================================================================== */
const usersSort = { sortBy: "nom", order: "asc" };
let usersCache = [];

const TYPE_LABELS = { etudiant: "Étudiant", professeur: "Professeur", personnel_administratif: "Personnel administratif" };

async function loadUsers() {
  const type = document.getElementById("filter-user-type").value;
  const params = new URLSearchParams();
  if (type) params.set("type_utilisateur", type);
  params.set("sort_by", usersSort.sortBy);
  params.set("order", usersSort.order);
  const tbody = document.getElementById("users-tbody");
  try {
    let users = await api(`${SERVICE_UTILISATEUR}/users?${params.toString()}`);
    const search = document.getElementById("search-users").value.trim().toLowerCase();
    if (search) {
      users = users.filter((u) =>
        [u.nom, u.prenom, u.email, u.id_utilisateur].filter(Boolean).some((v) => v.toLowerCase().includes(search))
      );
    }
    usersCache = users;
    if (!users.length) {
      tbody.innerHTML = `<tr><td colspan="11" class="empty-state">Aucun utilisateur trouvé.</td></tr>`;
      return;
    }
    tbody.innerHTML = users.map(renderUserRow).join("");
    tbody.querySelectorAll("[data-edit-user]").forEach((b) => b.addEventListener("click", () => editUser(b.dataset.editUser)));
    tbody.querySelectorAll("[data-delete-user]").forEach((b) => b.addEventListener("click", () => deleteUser(b.dataset.deleteUser)));
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="11" class="empty-state">Impossible de charger le Service-Utilisateur (${e.message}).</td></tr>`;
  }
}

function renderUserRow(u) {
  return `
    <tr>
      <td>${escapeHtml(u.id_utilisateur)}</td>
      <td>${escapeHtml(u.nom)}</td>
      <td>${escapeHtml(u.prenom)}</td>
      <td>${escapeHtml(u.email)}</td>
      <td>${escapeHtml(u.telephone || "—")}</td>
      <td><span class="badge badge-accent">${TYPE_LABELS[u.type_utilisateur] || u.type_utilisateur}</span></td>
      <td>${escapeHtml(u.faculte || "—")}</td>
      <td>${escapeHtml(u.departement || "—")}</td>
      <td>${escapeHtml(u.classe || "—")}</td>
      <td>${fmtDate(u.created_at)}</td>
      <td class="col-actions">
        <button class="btn-mini" data-edit-user="${u.id}">Modifier</button>
        <button class="btn-mini danger" data-delete-user="${u.id}">Supprimer</button>
      </td>
    </tr>`;
}

document.getElementById("btn-new-user").addEventListener("click", () => {
  document.getElementById("form-user").reset();
  document.getElementById("user-id").value = "";
  openModal("modal-user");
});

function editUser(id) {
  const u = usersCache.find((x) => String(x.id) === String(id));
  if (!u) return;
  document.getElementById("user-id").value = u.id;
  document.getElementById("user-id-utilisateur").value = u.id_utilisateur;
  document.getElementById("user-nom").value = u.nom;
  document.getElementById("user-prenom").value = u.prenom;
  document.getElementById("user-email").value = u.email;
  document.getElementById("user-telephone").value = u.telephone || "";
  document.getElementById("user-type").value = u.type_utilisateur;
  document.getElementById("user-faculte").value = u.faculte || "";
  document.getElementById("user-departement").value = u.departement || "";
  document.getElementById("user-classe").value = u.classe || "";
  openModal("modal-user");
}

async function deleteUser(id) {
  if (!confirm("Supprimer définitivement cet utilisateur ?")) return;
  try {
    await api(`${SERVICE_UTILISATEUR}/users/${id}`, { method: "DELETE" });
    toast("Utilisateur supprimé.");
    loadUsers();
  } catch (e) { toast(e.message, true); }
}

document.getElementById("form-user").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("user-id").value;
  const payload = {
    id_utilisateur: document.getElementById("user-id-utilisateur").value,
    nom: document.getElementById("user-nom").value,
    prenom: document.getElementById("user-prenom").value,
    email: document.getElementById("user-email").value,
    telephone: document.getElementById("user-telephone").value || null,
    type_utilisateur: document.getElementById("user-type").value,
    faculte: document.getElementById("user-faculte").value || null,
    departement: document.getElementById("user-departement").value || null,
    classe: document.getElementById("user-classe").value || null,
  };
  try {
    if (id) { await api(`${SERVICE_UTILISATEUR}/users/${id}`, { method: "PUT", body: JSON.stringify(payload) }); toast("Utilisateur mis à jour."); }
    else { await api(`${SERVICE_UTILISATEUR}/users`, { method: "POST", body: JSON.stringify(payload) }); toast("Utilisateur créé."); }
    closeModal("modal-user");
    loadUsers();
    populateLoanUserSelect();
  } catch (e) { toast(e.message, true); }
});

document.getElementById("filter-user-type").addEventListener("change", loadUsers);
document.getElementById("search-users").addEventListener("input", debounce(loadUsers, 300));
document.getElementById("btn-reset-users").addEventListener("click", () => {
  document.getElementById("search-users").value = "";
  document.getElementById("filter-user-type").value = "";
  loadUsers();
});

initSortableHeaders("table-users", usersSort, loadUsers);

/* =====================================================================
   EMPRUNTS  — Service-Emprunt
   ===================================================================== */
const loansSort = { sortBy: "date", order: "desc" };

async function populateLoanUserSelect() {
  const select = document.getElementById("loan-user-id");
  try {
    const users = await api(`${SERVICE_UTILISATEUR}/users?sort_by=nom&order=asc`);
    if (!users.length) {
      select.innerHTML = `<option value="">Aucun utilisateur disponible</option>`;
      select.disabled = true;
      return;
    }
    select.disabled = false;
    select.innerHTML = `<option value="">Sélectionner un emprunteur</option>` + users
      .map((u) => `<option value="${u.id}">${escapeHtml(u.nom)} ${escapeHtml(u.prenom)} (${escapeHtml(u.id_utilisateur)} — ${TYPE_LABELS[u.type_utilisateur] || u.type_utilisateur})</option>`)
      .join("");
  } catch (e) {
    select.innerHTML = `<option value="">Impossible de charger les utilisateurs</option>`;
    select.disabled = true;
    toast(`Liste des emprunteurs indisponible : ${e.message}`, true);
  }
}

async function loadLoans(onlyLate = false) {
  const statut = document.getElementById("filter-loan-status").value;
  const tbody = document.getElementById("loans-tbody");
  const params = new URLSearchParams();
  if (!onlyLate && statut) params.set("statut", statut);
  params.set("sort_by", loansSort.sortBy);
  params.set("order", loansSort.order);
  const url = onlyLate ? `${SERVICE_EMPRUNT}/loans/late` : `${SERVICE_EMPRUNT}/loans?${params.toString()}`;

  try {
    const loans = await api(url);
    if (!loans.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Aucun emprunt à afficher.</td></tr>`;
      return;
    }
    const enriched = await Promise.all(loans.map(enrichLoan));
    tbody.innerHTML = enriched.map(renderLoanRow).join("");
    tbody.querySelectorAll("[data-return-loan]").forEach((b) => b.addEventListener("click", () => openReturnModal(b.dataset.returnLoan)));
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Impossible de charger le Service-Emprunt (${e.message}).</td></tr>`;
  }
}

async function enrichLoan(loan) {
  const [livre, utilisateur] = await Promise.all([
    api(`${SERVICE_LIVRE}/books/${loan.book_id}`).catch(() => null),
    api(`${SERVICE_UTILISATEUR}/users/${loan.user_id}`).catch(() => null),
  ]);
  return { ...loan, livre, utilisateur };
}

const STATUS_BADGE = {
  en_cours: { cls: "badge-accent", label: "En cours" },
  retourne: { cls: "badge-green", label: "Retourné" },
  en_retard: { cls: "badge-red", label: "En retard" },
};

function renderLoanRow(l) {
  const s = STATUS_BADGE[l.statut] || STATUS_BADGE.en_cours;
  return `
    <tr>
      <td><strong>${l.livre ? escapeHtml(l.livre.titre) : "—"}</strong></td>
      <td>${l.utilisateur ? escapeHtml(l.utilisateur.prenom + " " + l.utilisateur.nom) : "—"}</td>
      <td>${escapeHtml(l.isbn)}</td>
      <td>${fmtDate(l.date_emprunt)}</td>
      <td>${fmtDate(l.date_retour_prevue)}</td>
      <td><span class="badge ${s.cls}">${s.label}</span></td>
      <td class="col-actions">
        ${l.statut !== "retourne" ? `<button class="btn-mini accent" data-return-loan="${l.id}">Retourner</button>` : `<span class="muted">${l.observations ? escapeHtml(l.observations) : ""}</span>`}
      </td>
    </tr>`;
}

function openReturnModal(loanId) {
  document.getElementById("return-loan-id").value = loanId;
  document.getElementById("return-observations").value = "bon_etat";
  openModal("modal-return");
}

document.getElementById("form-return").addEventListener("submit", async (e) => {
  e.preventDefault();
  const loanId = document.getElementById("return-loan-id").value;
  const observations = document.getElementById("return-observations").value || null;
  try {
    await api(`${SERVICE_EMPRUNT}/loans/${loanId}/return`, { method: "PUT", body: JSON.stringify({ observations }) });
    toast("Livre retourné avec succès.");
    closeModal("modal-return");
    loadLoans();
    loadBooks();
  } catch (e) { toast(e.message, true); }
});

document.getElementById("btn-new-loan").addEventListener("click", async () => {
  document.getElementById("form-loan").reset();
  await populateLoanUserSelect();
  openModal("modal-loan");
});

document.getElementById("form-loan").addEventListener("submit", async (e) => {
  e.preventDefault();
  const selectedUserId = document.getElementById("loan-user-id").value;
  if (!selectedUserId) {
    toast("Veuillez sélectionner un emprunteur.", true);
    return;
  }
  const payload = {
    user_id: parseInt(selectedUserId, 10),
    isbn: document.getElementById("loan-isbn").value.trim(),
    duree_jours: parseInt(document.getElementById("loan-duree").value, 10),
  };
  try {
    await api(`${SERVICE_EMPRUNT}/loans`, { method: "POST", body: JSON.stringify(payload) });
    toast("Emprunt enregistré.");
    closeModal("modal-loan");
    loadLoans();
    loadBooks();
  } catch (e) { toast(e.message, true); }
});

document.getElementById("filter-loan-status").addEventListener("change", () => loadLoans(false));
document.getElementById("btn-show-late").addEventListener("click", () => loadLoans(true));
document.getElementById("btn-reset-loans").addEventListener("click", () => {
  document.getElementById("filter-loan-status").value = "";
  loadLoans(false);
});

initSortableHeaders("table-loans", loansSort, () => loadLoans(false));

/* =====================================================================
   HISTORIQUE DÉTAILLÉ
   ===================================================================== */
let historiqueData = []; // emprunts enrichis (livre + utilisateur complets)

document.getElementById("hist-period").addEventListener("change", (e) => {
  const isCustom = e.target.value === "custom";
  document.getElementById("hist-date-start").classList.toggle("hidden", !isCustom);
  document.getElementById("hist-date-end").classList.toggle("hidden", !isCustom);
  renderHistorique();
});

["hist-search"].forEach((id) => document.getElementById(id).addEventListener("input", debounce(renderHistorique, 250)));
["hist-user", "hist-book", "hist-status", "hist-sort", "hist-date-start", "hist-date-end"].forEach((id) =>
  document.getElementById(id).addEventListener("change", renderHistorique)
);
document.getElementById("btn-reset-hist").addEventListener("click", () => {
  document.getElementById("hist-search").value = "";
  document.getElementById("hist-period").value = "";
  document.getElementById("hist-date-start").value = "";
  document.getElementById("hist-date-end").value = "";
  document.getElementById("hist-date-start").classList.add("hidden");
  document.getElementById("hist-date-end").classList.add("hidden");
  document.getElementById("hist-user").value = "";
  document.getElementById("hist-book").value = "";
  document.getElementById("hist-status").value = "";
  document.getElementById("hist-sort").value = "emprunt_desc";
  renderHistorique();
});

async function loadHistorique() {
  const tbody = document.getElementById("historique-tbody");
  tbody.innerHTML = `<tr><td colspan="10" class="empty-state">Chargement…</td></tr>`;
  try {
    const [loans, books, users] = await Promise.all([
      api(`${SERVICE_EMPRUNT}/loans?sort_by=date&order=desc`),
      api(`${SERVICE_LIVRE}/books`),
      api(`${SERVICE_UTILISATEUR}/users`),
    ]);

    const bookById = Object.fromEntries(books.map((b) => [b.id, b]));
    const userById = Object.fromEntries(users.map((u) => [u.id, u]));

    historiqueData = loans.map((l) => ({ ...l, livre: bookById[l.book_id] || null, utilisateur: userById[l.user_id] || null }));

    // Peupler les listes déroulantes de filtre (une seule fois par chargement)
    const userSelect = document.getElementById("hist-user");
    const currentUserVal = userSelect.value;
    userSelect.innerHTML = `<option value="">Tous les utilisateurs</option>` + users
      .sort((a, b) => a.nom.localeCompare(b.nom))
      .map((u) => `<option value="${u.id}">${escapeHtml(u.nom)} ${escapeHtml(u.prenom)}</option>`).join("");
    userSelect.value = currentUserVal;

    const bookSelect = document.getElementById("hist-book");
    const currentBookVal = bookSelect.value;
    bookSelect.innerHTML = `<option value="">Tous les livres</option>` + books
      .sort((a, b) => a.titre.localeCompare(b.titre))
      .map((b) => `<option value="${b.id}">${escapeHtml(b.titre)}</option>`).join("");
    bookSelect.value = currentBookVal;

    renderHistorique();
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty-state">Erreur de chargement de l'historique (${e.message}).</td></tr>`;
  }
}

function isInPeriod(dateIso, period) {
  if (!period) return true;
  const d = new Date(dateIso);
  const now = new Date();
  if (period === "today") return d.toDateString() === now.toDateString();
  if (period === "week") {
    const start = new Date(now); start.setDate(now.getDate() - now.getDay());
    start.setHours(0, 0, 0, 0);
    return d >= start;
  }
  if (period === "month") return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  if (period === "year") return d.getFullYear() === now.getFullYear();
  if (period === "custom") {
    const startVal = document.getElementById("hist-date-start").value;
    const endVal = document.getElementById("hist-date-end").value;
    if (startVal && d < new Date(startVal)) return false;
    if (endVal && d > new Date(endVal + "T23:59:59")) return false;
    return true;
  }
  return true;
}

function renderHistorique() {
  const tbody = document.getElementById("historique-tbody");
  const search = document.getElementById("hist-search").value.trim().toLowerCase();
  const period = document.getElementById("hist-period").value;
  const userFilter = document.getElementById("hist-user").value;
  const bookFilter = document.getElementById("hist-book").value;
  const statusFilter = document.getElementById("hist-status").value;
  const sortMode = document.getElementById("hist-sort").value;

  let rows = historiqueData.filter((l) => {
    if (statusFilter && l.statut !== statusFilter) return false;
    if (userFilter && String(l.user_id) !== userFilter) return false;
    if (bookFilter && String(l.book_id) !== bookFilter) return false;
    if (!isInPeriod(l.date_emprunt, period)) return false;
    if (search) {
      const haystack = [
        l.utilisateur ? l.utilisateur.nom + " " + l.utilisateur.prenom : "",
        l.livre ? l.livre.titre : "",
        l.livre ? l.livre.auteur : "",
        l.isbn,
      ].join(" ").toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });

  const userName = (l) => (l.utilisateur ? `${l.utilisateur.nom} ${l.utilisateur.prenom}` : "");
  const bookName = (l) => (l.livre ? l.livre.titre : "");

  rows.sort((a, b) => {
    switch (sortMode) {
      case "user_asc": return userName(a).localeCompare(userName(b));
      case "user_desc": return userName(b).localeCompare(userName(a));
      case "book_asc": return bookName(a).localeCompare(bookName(b));
      case "book_desc": return bookName(b).localeCompare(bookName(a));
      case "emprunt_asc": return new Date(a.date_emprunt) - new Date(b.date_emprunt);
      case "emprunt_desc": return new Date(b.date_emprunt) - new Date(a.date_emprunt);
      case "retour_asc": return new Date(a.date_retour_reelle || 0) - new Date(b.date_retour_reelle || 0);
      case "retour_desc": return new Date(b.date_retour_reelle || 0) - new Date(a.date_retour_reelle || 0);
      default: return 0;
    }
  });

  window.__historiqueFiltered = rows; // utilisé par les exports CSV/PDF

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty-state">Aucun résultat pour ces critères.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map((l) => {
    const s = STATUS_BADGE[l.statut] || STATUS_BADGE.en_cours;
    const duree = daysBetween(l.date_emprunt, l.date_retour_reelle);
    return `
      <tr>
        <td>#${l.id}</td>
        <td>${l.utilisateur ? escapeHtml(l.utilisateur.nom + " " + l.utilisateur.prenom) : "—"}</td>
        <td>${l.livre ? escapeHtml(l.livre.titre) : "—"}</td>
        <td>${l.livre ? escapeHtml(l.livre.auteur) : "—"}</td>
        <td>${escapeHtml(l.isbn)}</td>
        <td>${fmtDate(l.date_emprunt, true)}</td>
        <td>${fmtDate(l.date_retour_prevue, true)}</td>
        <td>${l.date_retour_reelle ? fmtDate(l.date_retour_reelle, true) : "—"}</td>
        <td><span class="badge ${s.cls}">${s.label}</span></td>
        <td>${duree}</td>
      </tr>`;
  }).join("");
}

/* -------- Export CSV -------- */
document.getElementById("btn-export-csv").addEventListener("click", () => {
  const rows = window.__historiqueFiltered || [];
  if (!rows.length) { toast("Aucune donnée à exporter.", true); return; }
  const header = ["ID", "Utilisateur", "Titre", "Auteur", "ISBN", "Date emprunt", "Retour prévu", "Retour effectif", "Statut", "Durée (j)"];
  const lines = rows.map((l) => [
    l.id,
    l.utilisateur ? `${l.utilisateur.nom} ${l.utilisateur.prenom}` : "",
    l.livre ? l.livre.titre : "",
    l.livre ? l.livre.auteur : "",
    l.isbn,
    fmtDate(l.date_emprunt, true),
    fmtDate(l.date_retour_prevue, true),
    l.date_retour_reelle ? fmtDate(l.date_retour_reelle, true) : "",
    (STATUS_BADGE[l.statut] || {}).label || l.statut,
    daysBetween(l.date_emprunt, l.date_retour_reelle),
  ].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(";"));
  const csv = [header.join(";"), ...lines].join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `historique_emprunts_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});

/* -------- Export PDF -------- */
document.getElementById("btn-export-pdf").addEventListener("click", () => {
  const rows = window.__historiqueFiltered || [];
  if (!rows.length) { toast("Aucune donnée à exporter.", true); return; }
  if (!window.jspdf) { toast("Export PDF indisponible (bibliothèque non chargée).", true); return; }
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: "landscape" });
  doc.setFontSize(14);
  doc.text("Bibliothèque Numérique DIT — Historique des emprunts", 14, 12);
  const head = [["ID", "Utilisateur", "Titre", "Auteur", "ISBN", "Emprunt", "Retour prévu", "Retour effectif", "Statut", "Durée (j)"]];
  const body = rows.map((l) => [
    l.id,
    l.utilisateur ? `${l.utilisateur.nom} ${l.utilisateur.prenom}` : "",
    l.livre ? l.livre.titre : "",
    l.livre ? l.livre.auteur : "",
    l.isbn,
    fmtDate(l.date_emprunt),
    fmtDate(l.date_retour_prevue),
    l.date_retour_reelle ? fmtDate(l.date_retour_reelle) : "—",
    (STATUS_BADGE[l.statut] || {}).label || l.statut,
    daysBetween(l.date_emprunt, l.date_retour_reelle),
  ]);
  doc.autoTable({ head, body, startY: 18, styles: { fontSize: 8 }, headStyles: { fillColor: [16, 73, 83] } });
  doc.save(`historique_emprunts_${new Date().toISOString().slice(0, 10)}.pdf`);
});

/* =====================================================================
   MES EMPRUNTS — Étudiant / Professeur (Service-Emprunt, filtré par rôle côté serveur)
   ===================================================================== */
function joursRestantsLabel(l) {
  if (l.statut === "retourne") return "—";
  const now = new Date();
  const prevue = new Date(l.date_retour_prevue);
  const diffJours = Math.ceil((prevue - now) / 86400000);
  if (diffJours >= 0) return `Reste ${diffJours} jour${diffJours > 1 ? "s" : ""}`;
  return `Retard de ${Math.abs(diffJours)} jour${Math.abs(diffJours) > 1 ? "s" : ""}`;
}

async function loadMesEmprunts() {
  const tbody = document.getElementById("mesemprunts-tbody");
  const statut = document.getElementById("mine-status").value;
  const order = document.getElementById("mine-sort").value;
  const params = new URLSearchParams();
  if (statut) params.set("statut", statut);
  params.set("sort_by", "date");
  params.set("order", order);
  try {
    const loans = await api(`${SERVICE_EMPRUNT}/loans?${params.toString()}`);
    if (!loans.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-state">Aucun emprunt à afficher.</td></tr>`;
      return;
    }
    const enriched = await Promise.all(loans.map(async (l) => ({
      ...l,
      livre: await api(`${SERVICE_LIVRE}/books/${l.book_id}`).catch(() => null),
    })));
    tbody.innerHTML = enriched.map((l) => {
      const s = STATUS_BADGE[l.statut] || STATUS_BADGE.en_cours;
      return `
        <tr>
          <td><strong>${l.livre ? escapeHtml(l.livre.titre) : "—"}</strong></td>
          <td>${l.livre ? escapeHtml(l.livre.auteur) : "—"}</td>
          <td>${fmtDate(l.date_emprunt)}</td>
          <td>${fmtDate(l.date_retour_prevue)}</td>
          <td><span class="badge ${s.cls}">${s.label}</span></td>
          <td>${joursRestantsLabel(l)}</td>
        </tr>`;
    }).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">Impossible de charger vos emprunts (${e.message}).</td></tr>`;
  }
}

document.getElementById("mine-status").addEventListener("change", loadMesEmprunts);
document.getElementById("mine-sort").addEventListener("change", loadMesEmprunts);

/* =====================================================================
   E-MAILS ENVOYÉS (simulation) — Personnel administratif
   ===================================================================== */
async function loadEmails() {
  const tbody = document.getElementById("emails-tbody");
  try {
    const emails = await api(`${SERVICE_UTILISATEUR}/emails`);
    if (!emails.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="empty-state">Aucun e-mail envoyé pour le moment.</td></tr>`;
      return;
    }
    tbody.innerHTML = emails.map((m) => `
      <tr>
        <td>${escapeHtml(m.destinataire)}</td>
        <td>${escapeHtml(m.sujet)}</td>
        <td class="pre-wrap">${escapeHtml(m.corps)}</td>
        <td>${fmtDate(m.created_at, true)}</td>
      </tr>`).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">Impossible de charger le journal des e-mails (${e.message}).</td></tr>`;
  }
}

/* =====================================================================
   INITIALISATION — appelée par auth.js après connexion réussie
   ===================================================================== */
window.initAppData = function (admin) {
  loadBooks();
  if (admin) {
    loadUsers();
    loadLoans();
    populateLoanUserSelect();
  } else {
    loadMesEmprunts();
  }
};
