const state = {
  me: null,
  profile: null,
  dashboard: null,
};

const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatTime(value) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    dateStyle: "medium",
  }).format(parsed);
}

function toast(message, type = "success") {
  const item = document.createElement("div");
  item.className = `toast ${type === "error" ? "error" : ""}`;
  item.textContent = message;
  $("#toast-region").append(item);
  window.setTimeout(() => item.remove(), 4600);
}

async function api(path, options = {}) {
  const config = { credentials: "same-origin", ...options };
  if (config.body && !(config.body instanceof FormData) && typeof config.body !== "string") {
    config.headers = { "Content-Type": "application/json", ...(config.headers || {}) };
    config.body = JSON.stringify(config.body);
  }
  const response = await fetch(path, config);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    throw new Error(data?.error || "Não foi possível concluir esta ação agora.");
  }
  return data;
}

function updateDate(meta) {
  $("#site-date").textContent = meta.date;
  $("#auth-date").textContent = meta.date;
}

function toggleAuth(mode) {
  $("#login-card").classList.toggle("hidden", mode !== "login");
  $("#register-card").classList.toggle("hidden", mode !== "register");
}

function switchView(isAuthenticated) {
  $("#auth-view").classList.toggle("hidden", isAuthenticated);
  $("#app-view").classList.toggle("hidden", !isAuthenticated);
}

function accountDetails() {
  const user = state.me?.user;
  if (!user) return;
  $("#account-name").textContent = user.name;
  $("#account-initial").textContent = user.name.trim().charAt(0).toUpperCase() || "P";
  $("#welcome-name").textContent = user.name.trim().split(/\s+/)[0] || "";
}

function navigate(route) {
  $$(".page").forEach((page) => page.classList.toggle("active", page.dataset.page === route));
  $$(".nav-link").forEach((button) => button.classList.toggle("active", button.dataset.route === route));
  $(".sidebar").classList.remove("open");
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (route === "dashboard") loadDashboard();
  if (route === "profile") populateProfileForm();
  if (route === "jobs") loadJobs();
  if (route === "resume") loadResumes();
  if (route === "courses") loadCourses();
}

function renderRecommendationCards(target, recommendations, emptyMessage) {
  if (!recommendations?.length) {
    target.innerHTML = `<div class="empty-card">${escapeHtml(emptyMessage)}</div>`;
    return;
  }
  target.innerHTML = recommendations.map((item, index) => `
    <article class="recommendation-card">
      <span class="recommendation-number">0${index + 1}</span>
      <h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(item.reason)}</p>
    </article>
  `).join("");
}

function renderDashboard(data) {
  state.dashboard = data;
  const completion = data.profile_completion || 0;
  $("#profile-progress-text").textContent = `${completion}% concluído`;
  $("#profile-progress-number").innerHTML = `${completion}<small>%</small>`;
  $("#profile-progress-line").style.width = `${completion}%`;
  $("#profile-progress-message").textContent = completion
    ? "Continue preenchendo: as sugestões usam somente as suas respostas."
    : "Quanto mais você preencher, mais personalizada será sua orientação.";
  $("#advice-basis").textContent = `Esta orientação considera ${data.advice.basis.join(", ")}.`;
  $("#advice-list").innerHTML = data.advice.next_steps
    .map((step) => `<li>${escapeHtml(step)}</li>`).join("");
  renderRecommendationCards(
    $("#dashboard-recommendations"),
    data.recommendations,
    "Complete seu perfil para receber sugestões de áreas de estudo relacionadas ao que você procura."
  );
}

async function loadDashboard() {
  try {
    renderDashboard(await api("/api/dashboard"));
  } catch (error) {
    if (!$("#app-view").classList.contains("hidden")) toast(error.message, "error");
  }
}

function populateProfileForm() {
  const form = $("#profile-form");
  if (!state.me) return;
  const { user, profile } = state.me;
  state.profile = profile;
  $("#profile-name").value = user.name || "";
  $("#profile-email").value = user.email || "";
  $$('[name]', form).forEach((field) => {
    if (field.name in profile) field.value = profile[field.name] || "";
  });
  renderProfileSummary();
}

function profileText(value, fallback = "Não informado") {
  const cleanValue = String(value || "").trim();
  return cleanValue ? escapeHtml(cleanValue) : `<span class="not-informed">${fallback}</span>`;
}

function profileTags(value, fallback = "Nenhuma habilidade informada") {
  const items = String(value || "")
    .split(/[;,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (!items.length) return `<span class="not-informed">${fallback}</span>`;
  return `<div class="profile-tags">${items.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`;
}

function renderProfileSummary() {
  const target = $("#profile-summary");
  if (!target || !state.me) return;
  const { user, profile } = state.me;
  const location = [profile.city, profile.state].filter(Boolean).join(" · ");
  const completion = state.me.completion ?? 0;
  target.innerHTML = `
    <section class="profile-overview-card">
      <div class="profile-avatar">${escapeHtml(user.name.trim().charAt(0).toUpperCase() || "P")}</div>
      <div class="profile-overview-main">
        <p class="eyebrow">Seu espaço profissional</p>
        <h2>${escapeHtml(user.name)}</h2>
        <p>${escapeHtml(user.email)}${profile.phone ? ` · ${escapeHtml(profile.phone)}` : ""}${location ? ` · ${escapeHtml(location)}` : ""}</p>
      </div>
      <div class="profile-completion"><span>${completion}%</span><small>perfil concluído</small></div>
      <button class="square-action" data-open-profile type="button" aria-label="Editar perfil">✎</button>
    </section>

    <section class="profile-summary-section">
      <div class="profile-section-heading">
        <div><p class="eyebrow">Direção profissional</p><h2>Pretensões</h2></div>
        <button class="section-action" data-open-profile type="button"><span>✎</span> Editar</button>
      </div>
      <div class="profile-info-grid profile-pretension-grid">
        <article class="profile-info-card"><span>Área desejada</span><strong>${profileText(profile.desired_area, "Conte qual área você deseja explorar")}</strong></article>
        <article class="profile-info-card"><span>Objetivo profissional</span><p>${profileText(profile.objective, "Defina o tipo de oportunidade que você procura")}</p></article>
        <article class="profile-info-card"><span>Disponibilidade e momento</span><p>${profileText(profile.age ? `${profile.age} anos` : "", "Idade não informada")}</p></article>
      </div>
    </section>

    <section class="profile-summary-section">
      <div class="profile-section-heading">
        <div><p class="eyebrow">Sua trajetória</p><h2>Experiência profissional</h2></div>
        <div class="section-actions"><button class="square-action square-action--small" data-open-profile type="button" aria-label="Editar experiência">✎</button><button class="square-action square-action--small" data-open-profile type="button" aria-label="Adicionar experiência">+</button></div>
      </div>
      ${profile.professional_experience ? `
        <article class="experience-record">
          <div class="experience-record-title"><span class="record-icon">▣</span><div><p>Experiência informada</p><h3>Vivência profissional</h3></div></div>
          <p class="experience-copy">${escapeHtml(profile.professional_experience)}</p>
        </article>` : `
        <div class="profile-empty-state"><span>+</span><div><b>Você ainda não adicionou uma experiência profissional.</b><p>Sem problema: projetos acadêmicos, cursos e habilidades também ajudam a contar sua história.</p></div><button class="text-link" data-open-profile type="button">Adicionar informação <span>→</span></button></div>`}
    </section>

    <section class="profile-summary-section">
      <div class="profile-section-heading">
        <div><p class="eyebrow">Base e desenvolvimento</p><h2>Formação, projetos e habilidades</h2></div>
        <button class="section-action" data-open-profile type="button"><span>✎</span> Editar</button>
      </div>
      <div class="profile-info-grid profile-development-grid">
        <article class="profile-info-card"><span>Escolaridade</span><p>${profileText(profile.education, "Nenhuma formação informada")}</p></article>
        <article class="profile-info-card"><span>Curso</span><p>${profileText(profile.course, "Nenhum curso em andamento informado")}</p></article>
        <article class="profile-info-card"><span>Idiomas</span><p>${profileText(profile.languages, "Nenhum idioma informado")}</p></article>
        <article class="profile-info-card profile-info-card--wide"><span>Projetos e experiências acadêmicas</span><p>${profileText(profile.academic_experience, "Adicione projetos, voluntariado ou trabalhos acadêmicos reais")}</p></article>
        <article class="profile-info-card profile-info-card--wide"><span>Habilidades</span>${profileTags(profile.skills)}</article>
        <article class="profile-info-card profile-info-card--wide"><span>Cursos e certificações</span><p>${profileText(profile.courses, "Nenhum curso ou certificação informado")}</p></article>
      </div>
    </section>`;
}

function openProfileEditor() {
  populateProfileForm();
  openModal("#profile-modal");
}

async function saveProfile(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  try {
    const result = await api("/api/profile", { method: "PUT", body: data });
    state.me.profile = result.profile;
    state.me.completion = result.completion;
    state.profile = result.profile;
    closeModal("#profile-modal");
    toast(result.message);
    await loadDashboard();
    navigate("dashboard");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function loadJobs() {
  const target = $("#jobs-list");
  target.innerHTML = "";
  try {
    const data = await api("/api/jobs");
    if (!data.jobs.length) {
      target.innerHTML = `
        <article class="empty-card">
          Ainda não há oportunidades publicadas com link individual verificado. Quando uma vaga tiver fonte e URL original válidas, ela aparecerá aqui.
        </article>`;
      return;
    }
    target.innerHTML = data.jobs.map((job) => `
      <article class="job-card">
        <div class="job-card-main">
          <p class="job-source">Fonte: ${escapeHtml(job.source)}</p>
          <h2>${escapeHtml(job.title)}</h2>
          <p>${escapeHtml(job.company)} · ${escapeHtml(job.location)}</p>
          <div class="job-meta">
            ${job.published_at ? `<span>Publicada: ${escapeHtml(formatTime(job.published_at))}</span>` : ""}
            ${job.last_updated_at ? `<span>Atualizada: ${escapeHtml(formatTime(job.last_updated_at))}</span>` : ""}
          </div>
        </div>
        <a class="button button--primary" href="${escapeHtml(job.original_url)}" target="_blank" rel="noopener noreferrer">Ver vaga <span>↗</span></a>
      </article>
    `).join("");
  } catch (error) {
    target.innerHTML = `<div class="empty-card">${escapeHtml(error.message)}</div>`;
  }
}

function resumeTitle(resume) {
  if (resume.kind === "uploaded") return resume.original_name || "Currículo enviado";
  return "Currículo criado no PrimeiroEmprego IA";
}

function renderResumes(resumes) {
  const target = $("#resume-list");
  if (!resumes.length) {
    target.innerHTML = `<div class="empty-card">Você ainda não salvou nenhum currículo. Envie um arquivo ou crie uma versão com as suas informações.</div>`;
    return;
  }
  target.innerHTML = resumes.map((resume) => `
    <article class="resume-row ${escapeHtml(resume.kind)}" data-resume-id="${resume.id}" data-resume-kind="${escapeHtml(resume.kind)}">
      <span class="resume-file-icon">${resume.kind === "uploaded" ? "PDF" : "IA"}</span>
      <div class="resume-row-main">
        <h3>${escapeHtml(resumeTitle(resume))}</h3>
        <p>${resume.kind === "uploaded" ? "Arquivo enviado" : "Currículo gerado"} · ${escapeHtml(formatTime(resume.updated_at))}</p>
      </div>
      <div class="resume-actions">
        <button class="small-button" data-resume-action="view">Visualizar</button>
        <button class="small-button" data-resume-action="analyze">Melhorar com IA</button>
        ${resume.kind === "generated" ? '<button class="small-button" data-resume-action="download">Baixar PDF</button>' : ""}
        <button class="small-button danger" data-resume-action="delete">Excluir</button>
      </div>
    </article>
  `).join("");
}

async function loadResumes() {
  try {
    const data = await api("/api/resumes");
    renderResumes(data.resumes);
  } catch (error) {
    $("#resume-list").innerHTML = `<div class="empty-card">${escapeHtml(error.message)}</div>`;
  }
}

function openModal(selector) {
  $(selector).classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeModal(selector) {
  $(selector).classList.add("hidden");
  if ($$(".modal:not(.hidden)").length === 0) document.body.style.overflow = "";
}

function populateBuilder() {
  const form = $("#resume-builder-form");
  const profile = state.me.profile || {};
  const { user } = state.me;
  const values = {
    full_name: user.name,
    phone: profile.phone || "",
    location: [profile.city, profile.state].filter(Boolean).join(" / "),
    objective: profile.objective || "",
    education: profile.education || "",
    professional_experience: profile.professional_experience || "",
    academic_experience: profile.academic_experience || "",
    courses: profile.courses || "",
    skills: profile.skills || "",
    languages: profile.languages || "",
    additional_information: "",
  };
  Object.entries(values).forEach(([name, value]) => {
    const field = $(`[name="${name}"]`, form);
    if (field) field.value = value;
  });
}

function renderResumePreview(data, resumeId) {
  const sections = data.sections.map((section) => `
    <section class="resume-document-section">
      <h2>${escapeHtml(section.title)}</h2>
      <p>${escapeHtml(section.content)}</p>
    </section>
  `).join("");
  $("#resume-preview").innerHTML = `
    <article class="resume-document">
      <header class="resume-document-header">
        <h1>${escapeHtml(data.name).toUpperCase()}</h1>
        <p>${data.contacts.map(escapeHtml).join(" &nbsp;•&nbsp; ")}</p>
      </header>
      ${sections}
      <div class="preview-actions">
        <a class="button button--primary" href="/api/resumes/${resumeId}/pdf">Baixar PDF <span>↓</span></a>
      </div>
    </article>`;
  openModal("#preview-modal");
}

async function handleResumeAction(event) {
  const button = event.target.closest("[data-resume-action]");
  if (!button) return;
  const row = button.closest("[data-resume-id]");
  const id = row.dataset.resumeId;
  const kind = row.dataset.resumeKind;
  const action = button.dataset.resumeAction;
  try {
    if (action === "delete") {
      if (!window.confirm("Excluir este currículo? Esta ação não pode ser desfeita.")) return;
      const result = await api(`/api/resumes/${id}`, { method: "DELETE" });
      toast(result.message);
      loadResumes();
      loadDashboard();
      return;
    }
    if (action === "download") {
      window.location.assign(`/api/resumes/${id}/pdf`);
      return;
    }
    if (action === "view") {
      if (kind === "uploaded") {
        window.open(`/api/resumes/${id}/file`, "_blank", "noopener");
      } else {
        const resume = await api(`/api/resumes/${id}`);
        renderResumePreview(resume.content, id);
      }
      return;
    }
    if (action === "analyze") {
      const analysis = await api(`/api/resumes/${id}/analyze`, { method: "POST" });
      $("#resume-preview").innerHTML = `
        <article class="resume-document">
          <header class="resume-document-header"><h1>Análise do currículo</h1><p>${escapeHtml(analysis.message)}</p></header>
          <section class="analysis-panel"><h3>Pontos observados</h3><ul>${analysis.feedback.map((item) => `<li>${escapeHtml(item.text)}</li>`).join("")}</ul></section>
        </article>`;
      openModal("#preview-modal");
    }
  } catch (error) {
    toast(error.message, "error");
  }
}

async function uploadResume(event) {
  event.preventDefault();
  const file = $("#resume-file").files[0];
  if (!file) {
    toast("Selecione um arquivo PDF ou DOCX.", "error");
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  try {
    const result = await api("/api/resumes/upload", { method: "POST", body: formData });
    toast(result.message);
    event.currentTarget.reset();
    $(".file-label span").textContent = "Selecionar arquivo";
    loadResumes();
    loadDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function generateResume(event) {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const result = await api("/api/resumes/generate", { method: "POST", body: values });
    closeModal("#builder-modal");
    toast(result.message);
    renderResumePreview(result.resume, result.id);
    loadResumes();
    loadDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function loadCourses() {
  const institutionsTarget = $("#institutions-list");
  try {
    const data = await api("/api/courses");
    if (data.recommendations.length) {
      $("#courses-intro").textContent = "As áreas abaixo foram sugeridas a partir das informações reais do seu perfil. Elas não garantem emprego.";
    } else {
      $("#courses-intro").textContent = "Preencha sua área desejada, objetivo ou habilidades no perfil para receber sugestões personalizadas.";
    }
    renderRecommendationCards(
      $("#courses-recommendations"),
      data.recommendations,
      "Ainda não há uma recomendação personalizada. Conte no seu perfil qual área você deseja explorar."
    );
    institutionsTarget.innerHTML = data.institutions.map((institution) => `
      <article class="institution-card">
        <span class="institution-logo">✦</span>
        <h3>${escapeHtml(institution.name)}</h3>
        <p>${escapeHtml(institution.description)}</p>
        <a href="${escapeHtml(institution.url)}" target="_blank" rel="noopener noreferrer">Conhecer cursos ↗</a>
      </article>
    `).join("");
  } catch (error) {
    institutionsTarget.innerHTML = `<div class="empty-card">${escapeHtml(error.message)}</div>`;
  }
}

async function enterApplication() {
  const me = await api("/api/me");
  state.me = me;
  state.profile = me.profile;
  switchView(true);
  accountDetails();
  populateProfileForm();
  await loadDashboard();
}

async function handleLogin(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const result = await api("/api/auth/login", { method: "POST", body: data });
    toast(result.message);
    await enterApplication();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const result = await api("/api/auth/register", { method: "POST", body: data });
    toast(result.message);
    await enterApplication();
    navigate("profile");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function logout() {
  try {
    const result = await api("/api/auth/logout", { method: "POST" });
    state.me = null;
    switchView(false);
    toggleAuth("login");
    toast(result.message);
  } catch (error) {
    toast(error.message, "error");
  }
}

function bindEvents() {
  $$('[data-show-auth]').forEach((button) => button.addEventListener("click", () => toggleAuth(button.dataset.showAuth)));
  $("#login-form").addEventListener("submit", handleLogin);
  $("#register-form").addEventListener("submit", handleRegister);
  $("#profile-form").addEventListener("submit", saveProfile);
  $("#upload-form").addEventListener("submit", uploadResume);
  $("#resume-builder-form").addEventListener("submit", generateResume);
  $("#resume-list").addEventListener("click", handleResumeAction);
  $("#logout-button").addEventListener("click", logout);
  $("#mobile-menu").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
  $$('[data-route]').forEach((button) => button.addEventListener("click", () => navigate(button.dataset.route)));
  $$('[data-go]').forEach((button) => button.addEventListener("click", () => navigate(button.dataset.go)));
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-open-profile]")) openProfileEditor();
  });
  $("#open-builder").addEventListener("click", () => { populateBuilder(); openModal("#builder-modal"); });
  $$('[data-close-modal]').forEach((item) => item.addEventListener("click", () => closeModal("#builder-modal")));
  $$('[data-close-profile]').forEach((item) => item.addEventListener("click", () => closeModal("#profile-modal")));
  $$('[data-close-preview]').forEach((item) => item.addEventListener("click", () => closeModal("#preview-modal")));
  $("#resume-file").addEventListener("change", (event) => {
    $(".file-label span").textContent = event.target.files[0]?.name || "Selecionar arquivo";
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeModal("#profile-modal");
      closeModal("#builder-modal");
      closeModal("#preview-modal");
    }
  });
}

async function boot() {
  bindEvents();
  try {
    const [meta, me] = await Promise.all([api("/api/meta"), api("/api/me")]);
    updateDate(meta);
    if (me.authenticated) {
      state.me = me;
      state.profile = me.profile;
      switchView(true);
      accountDetails();
      populateProfileForm();
      await loadDashboard();
    }
  } catch (error) {
    toast("Não foi possível iniciar a aplicação. Atualize a página e tente novamente.", "error");
  }
}

boot();
