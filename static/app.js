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
  syncMobileMenu();
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (route === "dashboard") loadDashboard();
  if (route === "profile") populateProfileForm();
  if (route === "jobs") loadJobs();
  if (route === "resume") { loadResumes(); loadAIStatus(); }
  if (route === "courses") loadCourses();
}

function renderRecommendationCards(target, recommendations, emptyMessage) {
  if (!recommendations?.length) {
    target.innerHTML = `<div class="empty-card">${escapeHtml(emptyMessage)}</div>`;
    return;
  }
  target.innerHTML = recommendations.map((item) => `
    <article class="recommendation-card">
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

const catalogRows = {jobs: [], courses: []};
const catalogVersions = {jobs: 0, courses: 0};
function catalogDate(value) { return value ? value.split("-").reverse().join("/") : "Não informada"; }
async function loadCatalog(kind) {
  const version = ++catalogVersions[kind];
  const target = $(`#${kind}-list`);
  target.innerHTML = '<p role="status">Carregando oportunidades…</p>';
  const filters = new URLSearchParams(new FormData($(`#${kind}-filters`)));
  try {
    const data = await api(`/api/${kind}?${filters}`);
    if (version !== catalogVersions[kind]) return;
    catalogRows[kind] = data[kind];
    $(`#${kind}-context`).textContent = `${data.total} resultado(s). ${data.interest ? `Área do perfil: ${data.interest}. ` : 'Informe sua área no perfil para personalizar. '}${data.interest && !data.recognized_areas.length ? 'Ainda não reconhecemos essa área; você pode explorar todas as áreas. ' : ''}${data.notice}`;
    target.innerHTML = data[kind].length ? data[kind].map((item, index) => `
      <article class="job-card catalog-card">
        <div class="job-card-main"><p class="job-source">${escapeHtml(item.company || item.institution)} · ${escapeHtml(item.source)}</p>
        <span class="match-badge ${item.match}">${item.match === 'direct' ? 'Sua área' : item.match === 'related' ? 'Área correlata' : 'Para explorar'}</span>
        <h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.location || item.modality)}</p>
        <p>${escapeHtml(item.description)}</p><p class="match-reason">${escapeHtml(item.match_reason)}</p>
        <div class="job-meta"><span>${escapeHtml(kind === 'jobs' ? item.contract : item.duration)}</span><span>${escapeHtml(item.salary || item.price || 'Consultar condições')}</span><span>Consultado em ${catalogDate(item.checked_on)}</span></div></div>
        <button class="button button--outline" data-catalog="${kind}" data-index="${index}">Ver detalhes</button>
      </article>`).join('') : '<div class="empty-card">Nenhum resultado disponível para estes filtros. Experimente outra busca ou escolha “Todas as áreas”. Anúncios com revisão vencida ficam ocultos.</div>';
  } catch (error) { if (version === catalogVersions[kind]) target.innerHTML = `<div class="empty-card">${escapeHtml(error.message)}</div>`; }
}
function loadJobs() { return loadCatalog('jobs'); }
function loadCourses() { return loadCatalog('courses'); }
async function loadAIStatus() {
  const target = $('#ai-availability');
  try {
    const status = await api('/api/ai/status');
    target.textContent = status.available ? `Análise com IA local disponível (${status.model}).` : 'Revisão automática disponível. A análise contextual com IA local será ativada quando o modelo gratuito estiver instalado neste servidor.';
  } catch { target.textContent = 'Revisão automática disponível. Não foi possível verificar o serviço de IA local.'; }
}
function showCatalogDetail(kind, index) {
  const item = catalogRows[kind][index];
  if (!item) return;
  $('#preview-title').textContent = item.title;
  const details = kind === 'jobs' ? [['Empresa / recrutamento', item.company], ['Local', item.location], ['Contrato', item.contract], ['Remuneração', item.salary], ['Horário', item.schedule]] : [['Instituição', item.institution], ['Tipo', item.course_type === 'tecnico' ? 'Curso técnico' : 'Curso livre de capacitação'], ['Modalidade', item.modality], ['Duração', item.duration], ['Custo', item.price], ['Turmas', item.availability]];
  $('#resume-preview').innerHTML = `<article class="listing-detail"><p class="match-reason">${escapeHtml(item.match_reason)}</p><p>${escapeHtml(item.description)}</p><dl>${details.map(([label,value]) => `<div><dt>${label}</dt><dd>${escapeHtml(value || 'Não informado na fonte')}</dd></div>`).join('')}</dl><h3>${kind === 'jobs' ? 'Requisitos e observações' : 'Requisitos e conteúdo'}</h3><ul>${(item.requirements || []).map(v => `<li>${escapeHtml(v)}</li>`).join('')}</ul>${item.benefits?.length ? `<h3>Benefícios informados</h3><ul>${item.benefits.map(v => `<li>${escapeHtml(v)}</li>`).join('')}</ul>` : ''}<p class="muted">Fonte: ${escapeHtml(item.source)}. Consulta em ${catalogDate(item.checked_on)}. A disponibilidade pode mudar. ${escapeHtml(item.access_note || '')}</p><a class="button button--primary" href="${escapeHtml(item.original_url)}" target="_blank" rel="noopener noreferrer">${kind === 'jobs' ? 'Ver vaga na fonte' : 'Ver curso na instituição'} ↗</a></article>`;
  openModal('#preview-modal');
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
      <span class="resume-file-icon">${resume.kind === "uploaded" ? "PDF" : "CV"}</span>
      <div class="resume-row-main">
        <h3>${escapeHtml(resumeTitle(resume))}</h3>
        <p>${resume.kind === "uploaded" ? "Arquivo enviado" : "Currículo gerado"} · ${escapeHtml(formatTime(resume.updated_at))}</p>
      </div>
      <div class="resume-actions">
        <button class="small-button" data-resume-action="view">Visualizar</button>
        <button class="small-button" data-resume-action="analyze">Analisar currículo</button>
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

const modalOrigins = new Map();
function openModal(selector) {
  const modal = $(selector);
  if (!modal.classList.contains('hidden')) return;
  modalOrigins.set(modal, document.activeElement);
  modal.classList.remove('hidden');
  $('#app-view').inert = true;
  $('#auth-view').inert = true;
  document.body.style.overflow = 'hidden';
  const first = $('button, input, a[href], textarea, select', modal);
  first?.focus();
}
function closeModal(selector) {
  const modal = $(selector);
  if (modal.classList.contains('hidden')) return;
  modal.classList.add('hidden');
  if (!$$('.modal:not(.hidden)').length) {
    document.body.style.overflow = '';
    $('#app-view').inert = false;
    $('#auth-view').inert = false;
  }
  const origin = modalOrigins.get(modal);
  if (origin?.isConnected && !origin.closest('.hidden')) origin.focus();
  modalOrigins.delete(modal);
}
function syncMobileMenu() {
  const open = $('.sidebar').classList.contains('open');
  $('.sidebar').inert = window.matchMedia('(max-width: 900px)').matches && !open;
  $('#mobile-menu').setAttribute('aria-expanded', String(open));
  $('#mobile-menu').setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
}

function populateBuilder() {
  const form = $("#resume-builder-form");
  const profile = state.me.profile || {};
  const { user } = state.me;
  const values = {
    full_name: user.name,
    email: user.email,
    headline: profile.desired_area || "",
    course: profile.course || "",
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
  $("#preview-title").textContent = "Prévia do currículo";
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
        <p class="resume-headline">${escapeHtml(data.headline || "")}</p><p>${data.contacts.map(escapeHtml).join(" &nbsp;•&nbsp; ")}</p>
      </header>
      ${sections}
      <div class="preview-actions">
        <a class="button button--primary" href="/api/resumes/${resumeId}/pdf">Baixar PDF</a><a class="button button--outline" href="/api/resumes/${resumeId}/pdf?inline=1" target="_blank" rel="noopener">Abrir prévia em PDF ↗</a>
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
      if (button.disabled) return;
      button.disabled = true;
      $('#preview-title').textContent = 'Análise do currículo';
      $('#resume-preview').innerHTML = '<p role="status">Lendo o PDF e analisando as informações… A IA local pode levar alguns minutos.</p>';
      openModal('#preview-modal');
      try {
        const analysis = await api(`/api/resumes/${id}/analyze`, { method: 'POST' });
        renderAnalysis(analysis);
      } catch (error) { $('#resume-preview').innerHTML = `<p role="alert">${escapeHtml(error.message)}</p>`; }
      finally { button.disabled = false; }
    }
  } catch (error) {
    toast(error.message, "error");
  }
}

function renderAnalysis(data) {
  const ai = data.contextual;
  const cards = (items, content) => items.map(item => `<article class="analysis-card">${content(item)}</article>`).join('');
  $('#resume-preview').innerHTML = `<article class="analysis-report"><p class="analysis-notice">${escapeHtml(data.ai_notice)}</p><p>${escapeHtml(data.summary)}</p><p class="muted">${data.metrics.pages} página(s) · ${data.metrics.words} palavras</p>
    ${ai ? `<h3>Pontos fortes com evidências</h3>${cards(ai.strengths, x => `<h4>${escapeHtml(x.title)}</h4><blockquote>${escapeHtml(x.evidence)}</blockquote><p>${escapeHtml(x.explanation)}</p>`)}<h3>Melhorias prioritárias</h3>${cards(ai.improvements, x => `<span class="match-badge">Prioridade ${escapeHtml(x.priority)}</span><h4>${escapeHtml(x.title)}</h4><p>${escapeHtml(x.evidence)}</p><p>${escapeHtml(x.suggestion)}</p>`)}${ai.rewrites.length ? `<h3>Sugestões de reescrita</h3><p>Confira se cada sugestão preserva seus fatos antes de usá-la.</p>${cards(ai.rewrites, x => `<p><b>Original:</b> ${escapeHtml(x.original)}</p><p><b>Sugestão:</b> ${escapeHtml(x.suggested)}</p><p class="muted">${escapeHtml(x.reason)}</p>`)}` : ''}<h3>Próximos passos</h3><ol>${ai.next_steps.map(x => `<li>${escapeHtml(x)}</li>`).join('')}</ol>` : ''}
    <h3>Verificação do documento</h3>${cards(data.checks, x => `<h4>${escapeHtml(x.title)} <span class="check-status">${x.status === 'ok' ? 'Identificado' : x.status === 'attention' ? 'Revisar' : 'Orientação'}</span></h4><p>${escapeHtml(x.evidence)}</p><p>${escapeHtml(x.suggestion)}</p>`)}
    <h3>Relação com a área desejada</h3><p>${escapeHtml(data.alignment.desired_area || 'Área ainda não informada no perfil.')}</p><p><b>Conhecimentos encontrados:</b> ${escapeHtml(data.alignment.skills_found.join(', ') || 'Nenhum dos termos monitorados.')}</p><p><b>Termos das vagas para revisar ou estudar:</b> ${escapeHtml(data.alignment.terms_to_review.join(', ') || 'Nenhum termo adicional identificado nas vagas disponíveis.')}</p><ul>${data.alignment.jobs.map(j => `<li><a href="${escapeHtml(j.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(j.title)} ↗</a></li>`).join('')}</ul><p class="muted">${escapeHtml(data.alignment.note)}</p><p class="muted">${escapeHtml(data.limitations)}</p></article>`;
}
async function uploadResume(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $('button[type="submit"]', form);
  if (button.disabled) return;
  const file = $('#resume-file').files[0];
  if (!file || !file.name.toLowerCase().endsWith('.pdf')) return toast('Selecione apenas um arquivo PDF.', 'error');
  if (!file.size || file.size > 8 * 1024 * 1024) return toast('Envie um PDF não vazio de até 8 MB.', 'error');
  const formData = new FormData(); formData.append('file', file);
  button.disabled = true; button.textContent = 'Verificando PDF…';
  try {
    const result = await api('/api/resumes/upload', {method: 'POST', body: formData});
    toast(result.message);
    if (result.warning) toast(result.warning, 'error');
    form.reset(); $('.file-label span').textContent = 'Selecionar arquivo';
    await loadResumes(); loadDashboard();
  } catch (error) { toast(error.message, 'error'); }
  finally { button.disabled = false; button.textContent = 'Enviar currículo'; }
}

async function generateResume(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $('button[type="submit"]', form);
  if (button.disabled) return;
  const values = Object.fromEntries(new FormData(form));
  button.disabled = true;
  try {
    const result = await api("/api/resumes/generate", { method: "POST", body: values });
    closeModal("#builder-modal");
    toast(result.message);
    renderResumePreview(result.resume, result.id);
    loadResumes();
    loadDashboard();
  } catch (error) {
    toast(error.message, "error");
  } finally { button.disabled = false; }
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
  ['jobs', 'courses'].forEach(kind => {
    $(`#${kind}-filters`).addEventListener('submit', event => { event.preventDefault(); loadCatalog(kind); });
    $(`#${kind}-filters`).addEventListener('change', event => { if (event.target.matches('select, [type="checkbox"]')) loadCatalog(kind); });
    $(`#${kind}-list`).addEventListener('click', event => { const button = event.target.closest('[data-catalog]'); if (button) showCatalogDetail(button.dataset.catalog, Number(button.dataset.index)); });
  });
  $$('#resume-builder-form textarea').forEach(field => field.maxLength = 4000);
  window.addEventListener('resize', syncMobileMenu);
  syncMobileMenu();
  document.addEventListener('keydown', event => {
    const modal = $('.modal:not(.hidden)');
    if (!modal || event.key !== 'Tab') return;
    const focusable = $$('button:not(:disabled), a[href], input:not(:disabled), textarea, select', modal).filter(x => x.getClientRects().length);
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  });
  $$('[data-show-auth]').forEach((button) => button.addEventListener("click", () => toggleAuth(button.dataset.showAuth)));
  $("#login-form").addEventListener("submit", handleLogin);
  $("#register-form").addEventListener("submit", handleRegister);
  $("#profile-form").addEventListener("submit", saveProfile);
  $("#upload-form").addEventListener("submit", uploadResume);
  $("#resume-builder-form").addEventListener("submit", generateResume);
  $("#resume-list").addEventListener("click", handleResumeAction);
  $("#logout-button").addEventListener("click", logout);
  $("#mobile-menu").addEventListener("click", () => { $(".sidebar").classList.toggle("open"); syncMobileMenu(); });
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
