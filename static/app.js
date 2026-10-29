/* teste commit e bra */
const state = { me: null, aiAvailable: false };
const optionCache = { locations: null, occupations: null };
const openOptionLists = new WeakMap();

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
    dateStyle: "medium", timeStyle: "short",
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
  const config = { credentials: "same-origin", ...options, headers: { ...options.headers, "X-Requested-With": "FirstJob" } };
  if (config.body && !(config.body instanceof FormData) && typeof config.body !== "string") {
    config.headers = { "Content-Type": "application/json", ...(config.headers || {}) };
    config.body = JSON.stringify(config.body);
  }
  const response = await fetch(path, config);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const error = new Error(data?.error || "Não foi possível concluir esta ação agora.");
    error.fields = data?.errors;
    throw error;
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

function navigate(route, fromHistory = false) {
  if (!['dashboard','profile','jobs','courses','resume'].includes(route)) route='dashboard';
  if (!fromHistory && location.hash !== '#'+route) history.pushState(null, '', '#'+route);
  $$('.nav-link').forEach(button => { if(button.dataset.route===route) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current'); });
  $$(".page").forEach((page) => page.classList.toggle("active", page.dataset.page === route));
  $$(".nav-link").forEach((button) => button.classList.toggle("active", button.dataset.route === route));
  setMobileMenuOpen(false);
  window.scrollTo({ top: 0, behavior: 'auto' });
  const heading = $(`[data-page="${route}"] h1`);
  if (heading) { heading.tabIndex=-1; heading.focus({preventScroll:true}); }
  if (route === "dashboard") loadDashboard();
  if (route === "profile") populateProfileForm();
  if (route === "jobs" || route === "courses") loadCatalog(route);
  if (route === "resume") { loadResumes(); loadAIStatus(); }
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
  const completion = data.profile_completion || 0;
  $('#page-dashboard [data-go="profile"]').textContent = completion === 100 ? 'Revisar perfil' : 'Completar meu perfil';
  $("#profile-progress-text").textContent = completion === 100 ? "Perfil básico completo" : `${completion}% do perfil básico`;
  $("#profile-progress-number").innerHTML = `${completion}<small>%</small>`;
  $("#profile-progress-line").style.width = `${completion}%`;
  $("#profile-progress-message").textContent = completion === 100
    ? "Seu perfil básico está completo. Acrescente experiências e projetos no seu ritmo."
    : completion
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

function normalizeOptionText(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

function loadOptionData(kind) {
  if (!optionCache[kind]) {
    const path = kind === "locations" ? "/static/locations.json" : "/static/occupations.json";
    optionCache[kind] = api(path).then((data) => {
      if (kind === "locations") {
        const stateNames = new Map(data.states.map((item) => [item.uf, item.name]));
        data.stateOptions = data.states.map((item) => ({ value: item.name, label: `${item.name} · ${item.uf}`, key: normalizeOptionText(`${item.name} ${item.uf}`) })).sort((a, b) => a.label.localeCompare(b.label, "pt-BR"));
        data.cityOptions = data.cities.map((item) => ({ value: item.name, label: `${item.name} · ${item.uf}`, key: normalizeOptionText(`${item.name} ${item.uf}`), stateName: stateNames.get(item.uf) })).sort((a, b) => a.label.localeCompare(b.label, "pt-BR"));
      } else {
        data.options = data.sectors.map((item) => ({value:item.title,label:item.title,key:normalizeOptionText(item.title),aliases:normalizeOptionText(item.aliases.join(' ')),family:item.code}));
      }
      return data;
    }).catch((error) => { optionCache[kind] = null; throw error; });
  }
  return optionCache[kind];
}

function rankOptions(items, query, kind) {
  if (!query) return items;
  const terms = query.split(/\s+/).filter(Boolean);
  const ranked = [];
  const relatedFamilies = new Set();
  items.forEach((item) => {
    const inTitle = item.key.includes(query);
    const inAliases = item.aliases?.includes(query);
    const termsMatch = terms.every((term) => item.key.includes(term) || item.aliases?.includes(term));
    if (!inTitle && !inAliases && !termsMatch) return;
    const score = item.key.startsWith(query) ? 0 : inTitle ? 1 : inAliases ? 2 : 3;
    ranked.push({ item, score });
    if (kind === "desired_area" && score <= 2) relatedFamilies.add(item.family);
  });
  if (kind === "desired_area" && query.length >= 3 && relatedFamilies.size) {
    const alreadyFound = new Set(ranked.map(({ item }) => item.value));
    items.forEach((item) => {
      if (relatedFamilies.has(item.family) && !alreadyFound.has(item.value)) ranked.push({ item, score: 4 });
    });
  }
  ranked.sort((a, b) => a.score - b.score || a.item.label.localeCompare(b.item.label, "pt-BR"));
  return ranked.map(({ item }) => item);
}

function closeOptionList(wrapper) {
  const input = $("input", wrapper);
  const list = $(".autocomplete-list", wrapper);
  list.hidden = true;
  input.setAttribute("aria-expanded", "false");
  input.removeAttribute("aria-activedescendant");
  openOptionLists.delete(wrapper);
}

function closeAllOptionLists() {
  $$(".autocomplete-field").forEach(closeOptionList);
}

function appendOptionBatch(wrapper) {
  const list = $(".autocomplete-list", wrapper);
  const current = openOptionLists.get(wrapper);
  if (!current || current.rendered >= current.matches.length) return;
  const next = Math.min(current.rendered + 80, current.matches.length);
  const name = $("input", wrapper).id;
  list.insertAdjacentHTML("beforeend", current.matches.slice(current.rendered, next).map((item, offset) => {
    const index = current.rendered + offset;
    return `<button id="${name}-option-${index}" class="autocomplete-option" type="button" role="option" aria-selected="false" data-option-index="${index}">${escapeHtml(item.label)}</button>`;
  }).join(""));
  current.rendered = next;
}

async function openOptionList(wrapper) {
  const input = $("input", wrapper);
  const list = $(".autocomplete-list", wrapper);
  const kind = wrapper.dataset.autocomplete;
  const requestValue = input.value;
  list.hidden = false;
  list.innerHTML = '<span class="autocomplete-message">Carregando opções…</span>';
  input.setAttribute("aria-expanded", "true");
  try {
    const data = await loadOptionData(kind === "desired_area" ? "occupations" : "locations");
    if (document.activeElement !== input || input.value !== requestValue || list.hidden) return;
    const items = kind === "city" ? data.cityOptions : kind === "state" ? data.stateOptions : data.options;
    const matches = rankOptions(items, normalizeOptionText(input.value), kind);
    openOptionLists.set(wrapper, { matches, rendered: 0, active: -1 });
    list.innerHTML = "";
    list.scrollTop = 0;
    if (matches.length) appendOptionBatch(wrapper);
    else list.innerHTML = '<span class="autocomplete-message">Nenhuma opção encontrada.</span>';
  } catch {
    if (!list.hidden) list.innerHTML = '<span class="autocomplete-message">Não foi possível carregar as opções. Tente novamente.</span>';
  }
}

function chooseOption(wrapper, index) {
  const current = openOptionLists.get(wrapper);
  const choice = current?.matches[index];
  if (!choice) return;
  const input = $("input", wrapper);
  input.value = choice.value;
  if (wrapper.dataset.autocomplete === "city" && choice.stateName) {
    const stateInput = $('[name="state"]', wrapper.closest("form"));
    if (stateInput) stateInput.value = choice.stateName;
  }
  closeAllOptionLists();
}

function bindOptionLists(parent = document) {
  $$(".autocomplete-field", parent).forEach((wrapper) => {
    const input = $("input", wrapper);
    const list = $(".autocomplete-list", wrapper);
    input.addEventListener("focus", () => openOptionList(wrapper));
    input.addEventListener("click", () => { if (list.hidden) openOptionList(wrapper); });
    input.addEventListener("input", () => openOptionList(wrapper));
    input.addEventListener("keydown", (event) => {
      const current = openOptionLists.get(wrapper);
      if (event.key === "Escape" && !list.hidden) { event.stopPropagation(); closeOptionList(wrapper); return; }
      if (!current || list.hidden || !current.matches.length) return;
      if (event.key === "Enter") {
        event.preventDefault();
        chooseOption(wrapper, current.active >= 0 ? current.active : 0);
        return;
      }
      if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
      event.preventDefault();
      const old = list.querySelector('[aria-selected="true"]');
      old?.setAttribute("aria-selected", "false");
      current.active = event.key === "ArrowDown" ? Math.min(current.active + 1, current.matches.length - 1) : Math.max(current.active - 1, 0);
      while (current.active >= current.rendered) appendOptionBatch(wrapper);
      const option = list.querySelector(`[data-option-index="${current.active}"]`);
      option?.setAttribute("aria-selected", "true");
      option?.scrollIntoView({ block: "nearest" });
      input.setAttribute("aria-activedescendant", option.id);
    });
    list.addEventListener("mousedown", (event) => event.preventDefault());
    list.addEventListener("click", (event) => {
      const option = event.target.closest("[data-option-index]");
      if (option) chooseOption(wrapper, Number(option.dataset.optionIndex));
    });
    list.addEventListener("scroll", () => {
      if (list.scrollTop + list.clientHeight >= list.scrollHeight - 60) appendOptionBatch(wrapper);
    });
    wrapper.addEventListener("focusout", (event) => {
      if (!wrapper.contains(event.relatedTarget)) closeOptionList(wrapper);
    });
  });
}

function profileText(value, fallback = "Não informado") {
  const cleanValue = String(value || "").trim();
  return cleanValue ? escapeHtml(cleanValue) : `<span class="not-informed">${fallback}</span>`;
}

const catalogRows = {jobs: [], courses: []};
const catalogVersions = {jobs: 0, courses: 0};
function catalogDate(value) { return value ? value.split("-").reverse().join("/") : "Não informada"; }
async function loadCatalog(kind) {
  const version = ++catalogVersions[kind];
  const target = $(`#${kind}-list`);
  target.innerHTML = '<p role="status">Carregando oportunidades…</p>';
  const filters = new URLSearchParams(new FormData($(`#${kind}-filters`)));
  try { sessionStorage.setItem('filters-'+kind, filters.toString()); } catch {}
  try {
    const data = await api(`/api/${kind}?${filters}`);
    if (version !== catalogVersions[kind]) return;
    catalogRows[kind] = data[kind];
    $(`#${kind}-context`).textContent = `${data.total} ${data.total === 1 ? "resultado" : "resultados"}. ${data.interest ? `Área do perfil: ${data.interest}. ` : 'Informe sua área no perfil para personalizar. '}${data.interest && !data.recognized_areas.length ? 'Ainda não reconhecemos essa área; você pode explorar todas as áreas. ' : ''}${data.notice}`;
    target.innerHTML = data[kind].length ? data[kind].map((item, index) => `
      <article class="job-card catalog-card">
        <div class="job-card-main"><p class="job-source">${escapeHtml(item.company || item.institution)}${(item.company || item.institution) !== item.source ? ` · Fonte: ${escapeHtml(item.source)}` : ""}</p>
        <span class="match-badge ${item.match}">${item.match === 'direct' ? 'Sua área' : item.match === 'related' ? 'Área correlata' : 'Para explorar'}</span>
        <h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.location || item.modality)}</p>
        <p>${escapeHtml(item.description)}</p><p class="match-reason">${escapeHtml(item.match_reason)}</p>
        <div class="job-meta"><span>${escapeHtml(kind === 'jobs' ? item.contract : item.duration)}</span><span>${escapeHtml(item.salary || item.price || 'Consultar condições')}</span>${kind === 'courses' ? '<span>Com certificado</span>' : ''}<span>Consultado em ${catalogDate(item.checked_on)}</span></div></div>
        <button class="button button--outline" data-catalog="${kind}" data-index="${index}">Ver detalhes</button>
      </article>`).join('') : `<div class="empty-card">${data.catalog_status === 'unavailable' ? (kind === 'jobs' ? 'Ainda não há vagas com revisão válida em Curitiba/PR. Os anúncios antigos permanecem ocultos até nova verificação. Consulte as fontes abaixo.' : 'O catálogo de cursos aguarda revisão. Consulte novamente mais tarde.') : (kind === 'courses' && filters.get('type') === 'tecnico' ? 'Não há curso técnico cadastrado para estes filtros.' : 'Nenhum resultado corresponde aos filtros aplicados.')} ${data.catalog_status !== 'unavailable' && filters.get('all') !== '1' ? 'Você pode explorar Todas as áreas.' : ''} Use Limpar filtros para reiniciar a busca.</div>`;
  } catch (error) { if (version === catalogVersions[kind]) { $(`#${kind}-context`).textContent='Falha ao carregar. Seus filtros foram mantidos.'; target.innerHTML = `<div class="empty-card" role="alert">${escapeHtml(error.message)} Use Buscar para tentar novamente.</div>`; } }
}
async function loadAIStatus() {
  const target = $('#ai-availability');
  try {
    const status = await api('/api/ai/status');
    state.aiAvailable = !!status.available;
    target.textContent = status.available ? 'Revisão de estrutura e análise contextual disponíveis.' : 'Revisão de estrutura disponível. As regras automáticas não substituem uma revisão de redação.';
  } catch { state.aiAvailable=false; target.textContent='Revisão de estrutura disponível.'; }
  $$('[data-resume-action="analyze"]').forEach(button => button.textContent=state.aiAvailable?'Analisar currículo':'Revisar estrutura');
}
function showCatalogDetail(kind, index) {
  const item = catalogRows[kind][index];
  if (!item) return;
  $('#preview-modal').classList.remove('return-to-builder');
  $('[data-close-preview].modal-close').setAttribute('aria-label', 'Fechar');
  $('#preview-title').textContent = item.title;
  const details = kind === 'jobs' ? [['Empresa / recrutamento', item.company], ['Local', item.location], ['Contrato', item.contract], ['Remuneração', item.salary], ['Horário', item.schedule], ['Inscrições até', item.expires_on ? catalogDate(item.expires_on) : 'Prazo não informado na fonte']] : [['Instituição', item.institution], ['Tipo', item.course_type === 'tecnico' ? 'Curso técnico' : 'Curso livre de capacitação'], ['Modalidade', item.modality], ['Duração', item.duration], ['Custo', item.price], ['Certificado', item.certificate], ['Custo do certificado', item.certificate_cost], ['Turmas', item.availability]];
  $('#resume-preview').innerHTML = `<article class="listing-detail"><p class="match-reason">${escapeHtml(item.match_reason)}</p><p>${escapeHtml(item.description)}</p><dl>${details.map(([label,value]) => `<div><dt>${label}</dt><dd>${escapeHtml(value || 'Não informado na fonte')}</dd></div>`).join('')}</dl><h3>${kind === 'jobs' ? 'Requisitos e observações' : 'Requisitos e conteúdo'}</h3><ul>${(item.requirements || []).map(v => `<li>${escapeHtml(v)}</li>`).join('')}</ul>${item.benefits?.length ? `<h3>Benefícios informados</h3><ul>${item.benefits.map(v => `<li>${escapeHtml(v)}</li>`).join('')}</ul>` : ''}<p class="muted">Fonte: ${escapeHtml(item.source)}. Consulta em ${catalogDate(item.checked_on)}. A disponibilidade pode mudar. ${escapeHtml(item.access_note || '')}</p><a class="button button--primary" href="${escapeHtml(item.original_url)}" target="_blank" rel="noopener noreferrer">${kind === 'jobs' ? 'Ver vaga na fonte' : 'Ver curso na instituição'} ↗</a></article>`;
  openModal('#preview-modal');
}

function resumeTitle(resume) {
  if (resume.kind === "uploaded") return resume.original_name || "Currículo enviado";
  return resume.original_name || `Currículo #${resume.id}`;
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
        <p>${resume.kind === "uploaded" ? "Arquivo enviado" : "Currículo gerado"} · ${escapeHtml(formatTime(resume.created_at))} · #${resume.id}</p>
      </div>
      <div class="resume-actions">
        <button class="small-button" data-resume-action="view">Visualizar</button>
        <button class="small-button" data-resume-action="analyze">${state.aiAvailable ? "Analisar currículo" : "Revisar estrutura"}</button><button class="small-button" data-resume-action="rename">Renomear</button>
        ${resume.kind === "generated" ? '<button class="small-button" data-resume-action="download">Baixar PDF</button><button class="small-button" data-resume-action="edit">Editar nova versão</button><button class="small-button" data-resume-action="duplicate">Duplicar</button>' : ""}
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
  if (selector === '#preview-modal' && $('button[type="submit"]:disabled', modal)) return;
  if(selector === '#builder-modal') {
    const form=$('#resume-builder-form');
    if($('button[type="submit"]',form).disabled) return;
    if(modal.dataset.draft !== JSON.stringify(Object.fromEntries(new FormData(form))) && !confirm('Descartar alterações não salvas do currículo?')) return;
  }
  if (selector === '#preview-modal' && modal.dataset.versionDraft && $('#version-form')) {
    if (modal.dataset.versionDraft !== JSON.stringify(Object.fromEntries(new FormData($('#version-form')))) && !confirm('Descartar alterações desta versão?')) return;
    delete modal.dataset.versionDraft;
  }
  modal.classList.add('hidden');
  if (selector === '#preview-modal') $('#builder-modal').inert = false;
  if (!$$('.modal:not(.hidden)').length) {
    document.body.style.overflow = '';
    $('#app-view').inert = false;
    $('#auth-view').inert = false;
  }
  const origin = modalOrigins.get(modal);
  if (origin?.isConnected && !origin.closest('.hidden')) origin.focus();
  else {
    const resumeId=origin?.closest?.('[data-resume-id]')?.dataset.resumeId;
    const action=origin?.dataset.resumeAction;
    const replacement=resumeId && action ? $(`[data-resume-id="${resumeId}"] [data-resume-action="${action}"]`) : null;
    (replacement || $('.page.active h1'))?.focus();
  }
  modalOrigins.delete(modal);
  if (selector === '#preview-modal') {
    modal.classList.remove('return-to-builder');
    $('[data-close-preview].modal-close').setAttribute('aria-label','Fechar');
  }
}
function setMobileMenuOpen(open) {
  const mobile = window.matchMedia('(max-width: 900px)').matches;
  $('.sidebar').classList.toggle('open', mobile && open);
  $('#app-view').classList.toggle('menu-open', mobile && open);
  syncMobileMenu();
  if (mobile && open) $('.sidebar .nav-link')?.focus();
  else if (mobile && $('.sidebar').contains(document.activeElement)) $('#mobile-menu').focus();
}
function syncMobileMenu() {
  const mobile = window.matchMedia('(max-width: 900px)').matches;
  if (!mobile) {
    $('.sidebar').classList.remove('open');
    $('#app-view').classList.remove('menu-open');
  }
  const open = mobile && $('.sidebar').classList.contains('open');
  $('.sidebar').inert = mobile && !open;
  $('.sidebar').setAttribute('aria-hidden', String(mobile && !open));
  $('#mobile-menu').setAttribute('aria-expanded', String(open));
  $('#mobile-menu').setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
}

function populateBuilder() {
  const form = $("#resume-builder-form");
  const profile = state.me.profile || {};
  const { user } = state.me;
  const values = {
    ...profile,
    ...profile.resume_fields,
    full_name: user.name,
    email: user.email,
    headline: profile.sections?.goals?.target_role || profile.desired_area || "",
    location: [profile.city, profile.state].filter(Boolean).join(" / "),
    additional_information: "",
  };
  $$('[name]', form).forEach((field) => {
    field.value = values[field.name] || "";
  });
  $('#builder-modal').dataset.draft=JSON.stringify(Object.fromEntries(new FormData(form)));
}

function resumeSectionHtml(section) {
  const records = ['Formação acadêmica','Curso em andamento ou concluído','Experiência profissional','Experiências acadêmicas e projetos','Cursos e certificações'].includes(section.title);
  const skills = section.title === 'Habilidades';
  return section.content.trim().split(/\n\s*\n/).map(group => {
    const lines = group.split(skills ? /[;\n]+/ : /\n/).map(line=>line.trim()).filter(Boolean);
    return `<div class="resume-record">${lines.map((line,index)=>{
      const bullet = skills || /^[-•●*]\s+/.test(line);
      if(bullet) line = line.replace(/^[-•●*]\s+/, '');
      let text = escapeHtml(line);
      if(records && index===0 && !bullet && line.split(' · ')[0].length<=180) {
        const [title,...details] = line.split(' · ');
        text = `<strong>${escapeHtml(title)}</strong>${details.length ? escapeHtml(' · '+details.join(' · ')) : ''}`;
      }
      return `<p${bullet ? ' class="resume-bullet"' : ''}>${text}</p>`;
    }).join('')}</div>`;
  }).join('');
}

function resumeContactHtml(contact) {
  const phone = /^(?:\d{10,11}|\(\d{2}\) ?\d{4,5}-\d{4})$/.test(contact);
  const label = phone ? 'Telefone' : contact.includes('@') ? 'E-mail' : 'Localização';
  const value = phone ? contact.replace(/^(\d{2})(\d{4,5})(\d{4})$/, '($1) $2-$3') : contact;
  return `<p><strong>${label}:</strong> ${escapeHtml(value)}</p>`;
}

function renderResumePreview(data, resumeId, returnToBuilder = false) {
  $("#preview-title").textContent = returnToBuilder ? "Currículo pronto para revisar" : "Prévia do currículo";
  $('#preview-modal').classList.toggle('return-to-builder', returnToBuilder);
  $('[data-close-preview].modal-close').setAttribute('aria-label', returnToBuilder ? 'Voltar à edição do currículo' : 'Fechar');
  const sections = data.sections.map((section) => `
    <section class="resume-document-section">
      <h2>${escapeHtml(section.title)}</h2>
      ${resumeSectionHtml(section)}
    </section>
  `).join("");
  $("#resume-preview").innerHTML = `
    <p class="muted">Versão #${resumeId} · ${escapeHtml(data.source || 'Versão histórica salva')} · independente do perfil atual.</p><article class="resume-document">
      <header class="resume-document-header">
        <h1>${escapeHtml(data.name).toUpperCase()}</h1>
        <p class="resume-headline">${escapeHtml(data.headline || "")}</p>
      </header>
      <div class="resume-document-contacts">${data.contacts.map(resumeContactHtml).join("")}</div>
      ${sections}
      <div class="preview-actions">
        <a class="button button--primary" href="/api/resumes/${resumeId}/pdf">Baixar PDF</a><a class="button button--outline" href="/api/resumes/${resumeId}/pdf?inline=1" target="_blank" rel="noopener">Abrir prévia em PDF ↗</a>
      </div>
    </article>`;
  openModal("#preview-modal");
  $('[data-close-preview].modal-close').focus();
  if (returnToBuilder) $('#builder-modal').inert = true;
}

async function handleResumeAction(event) {
  const button = event.target.closest("[data-resume-action]");
  if (!button) return;
  const row = button.closest("[data-resume-id]");
  const id = row.dataset.resumeId;
  const kind = row.dataset.resumeKind;
  const action = button.dataset.resumeAction;
  try {
    if (action === 'rename') {
      $('#preview-title').textContent='Renomear currículo';
      $('#resume-preview').innerHTML=`<form id="rename-resume-form" class="builder-form"><label>Nome desta versão<input name="title" required maxlength="120" value="${escapeHtml($('h3',row).textContent)}" /></label><p class="muted">O conteúdo e a data da versão permanecem iguais.</p><p role="alert" id="rename-error"></p><button type="submit" class="button button--primary">Salvar título</button></form>`;
      openModal('#preview-modal');
      $('#rename-resume-form').addEventListener('submit',async event=>{
        event.preventDefault();const form=event.currentTarget;const save=$('button',form);if(save.disabled)return;save.disabled=true;
        try{await api(`/api/resumes/${id}`,{method:'PATCH',body:{title:form.elements.title.value}});await loadResumes();save.disabled=false;closeModal('#preview-modal');toast('Título atualizado.');}
        catch(error){$('#rename-error').textContent=error.message;}finally{save.disabled=false;}
      });
      return;
    }
    if (action === 'duplicate') {
      button.disabled=true;
      await api(`/api/resumes/${id}/version`,{method:'POST',body:{}}); await loadResumes(); return;
    }
    if (action === 'edit') { await editResumeVersion(id); return; }
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
      $('#resume-preview').innerHTML = `<p role="status">${state.aiAvailable ? 'Analisando o documento. A análise contextual pode levar alguns minutos.' : 'Revisando a estrutura e as informações do documento…'}</p>`;
      openModal('#preview-modal');
      try {
        const analysis = await api(`/api/resumes/${id}/analyze${state.aiAvailable ? "" : "?mode=checks"}`, { method: 'POST' });
        renderAnalysis(analysis);
      } catch (error) { $('#resume-preview').innerHTML = `<p role="alert">${escapeHtml(error.message)}</p>`; }
      finally { button.disabled = false; }
    }
  } catch (error) {
    button.disabled=false; toast(error.message, "error");
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

async function editResumeVersion(id) {
  const saved=await api(`/api/resumes/${id}`);
  const content=saved.content;
  $('#preview-title').textContent='Editar uma nova versão';
  const field=(name,label,value,textarea=false)=>`<label>${escapeHtml(label)}${textarea?`<textarea name="${name}" maxlength="12000">${escapeHtml(value)}</textarea>`:`<input name="${name}" value="${escapeHtml(value)}" maxlength="300" />`}</label>`;
  $('#resume-preview').innerHTML=`<p>Origem: currículo #${id}, salvo em ${escapeHtml(formatTime(saved.created_at))}. A versão anterior será preservada.</p><form id="version-form" class="builder-form">${field('name','Nome',content.name)}${field('headline','Cargo-alvo',content.headline)}${field('contacts','Contatos (um por linha)',content.contacts.join('\n'),true)}${content.sections.map((s,i)=>field('section-'+i,s.title,s.content,true)).join('')}<button class="button button--primary" type="submit">Salvar nova versão</button></form><button class="button button--outline" type="button" id="version-from-profile">Criar outra a partir do perfil atual</button>`;
  openModal('#preview-modal');
  const form=$('#version-form');
  const initial=JSON.stringify(Object.fromEntries(new FormData(form)));
  $('#preview-modal').dataset.versionDraft=initial;
  form.addEventListener('submit',async event=>{
    event.preventDefault(); const button=$('button',form); if(button.disabled)return;button.disabled=true;
    const values=Object.fromEntries(new FormData(form));
    const next={name:values.name,headline:values.headline,contacts:values.contacts.split('\n').map(x=>x.trim()).filter(Boolean),sections:content.sections.map((s,i)=>({title:s.title,content:values['section-'+i]}))};
    try {const result=await api(`/api/resumes/${id}/version`,{method:'POST',body:{content:next}});delete $('#preview-modal').dataset.versionDraft;renderResumePreview(result.resume,result.id);loadResumes();toast(result.message);}
    catch(error){toast(error.message,'error');} finally{button.disabled=false;}
  });
  $('#version-from-profile').addEventListener('click',()=>{if($('button[type="submit"]',form).disabled || !confirm('Abrir um novo currículo com o perfil atual? Alterações não salvas desta edição serão descartadas.'))return;delete $('#preview-modal').dataset.versionDraft;closeModal('#preview-modal');populateBuilder();openModal('#builder-modal');});
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
    $('#builder-modal').dataset.draft=JSON.stringify(values);
    toast(result.message);
    renderResumePreview(result.resume, result.id, true);
    loadResumes();
    loadDashboard();
  } catch (error) {
    toast(error.message, "error");
  } finally { button.disabled = false; }
}

async function enterApplication(me) {
  me ||= await api("/api/me");
  state.me = me;
  switchView(true);
  accountDetails();
  populateProfileForm();
  navigate(location.hash.slice(1) || 'dashboard', true);
}

async function handleAuth(event) {
  event.preventDefault();
  const submit = event.currentTarget.querySelector?.('button[type="submit"]');
  if(submit?.disabled) return;
  if(submit) submit.disabled=true;
  const mode = event.currentTarget.id === "register-form" ? "register" : "login";
  const data = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const result = await api(`/api/auth/${mode}`, { method: "POST", body: data });
    toast(result.message);
    await enterApplication();
    if (mode === "register") navigate("profile");
  } catch (error) {
    toast(error.message, "error");
  } finally { if(submit) submit.disabled=false; }
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
  $('.skip-link').addEventListener('click',event=>{event.preventDefault();$('#main-content').focus();});
  window.addEventListener('hashchange', () => { if(state.me && location.hash !== '#main-content') navigate(location.hash.slice(1),true); });
  bindProfileEvents();
  document.addEventListener("pointerdown", (event) => {
    if (!event.target.closest(".autocomplete-field")) closeAllOptionLists();
  });
  ['jobs', 'courses'].forEach(kind => {
    const form=$(`#${kind}-filters`);
    try { const saved=new URLSearchParams(sessionStorage.getItem('filters-'+kind)||''); for(const [name,value] of saved) { const field=form.elements.namedItem(name); if(field) { if(field.type==='checkbox') field.checked=value==='1'; else field.value=value; } } } catch {}
    form.addEventListener('reset', () => { setTimeout(() => loadCatalog(kind), 0); });
    $(`#${kind}-filters`).addEventListener('submit', event => { event.preventDefault(); loadCatalog(kind); });
    $(`#${kind}-filters`).addEventListener('change', event => { if (event.target.matches('select, [type="checkbox"]')) loadCatalog(kind); });
    $(`#${kind}-list`).addEventListener('click', event => { const button = event.target.closest('[data-catalog]'); if (button) showCatalogDetail(button.dataset.catalog, Number(button.dataset.index)); });
  });
  $$('#resume-builder-form textarea').forEach(field => field.maxLength = 12000);
  window.addEventListener('resize', syncMobileMenu);
  syncMobileMenu();
  document.addEventListener('keydown', event => {
    const modal = $$('.modal:not(.hidden)').at(-1);
    if (event.key !== 'Tab') return;
    if (!modal && $('.sidebar').classList.contains('open')) {
      const buttons=$$('a[href], button', $('.sidebar')).filter(x=>x.getClientRects().length);
      if(event.shiftKey && document.activeElement===buttons[0]) { event.preventDefault(); buttons.at(-1)?.focus(); }
      else if(!event.shiftKey && document.activeElement===buttons.at(-1)) { event.preventDefault(); buttons[0]?.focus(); }
      return;
    }
    if (!modal) return;
    const focusable = $$('button:not(:disabled), a[href], input:not(:disabled), textarea, select', modal).filter(x => x.getClientRects().length);
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  });
  $$('[data-show-auth]').forEach((button) => button.addEventListener("click", () => toggleAuth(button.dataset.showAuth)));
  $("#login-form").addEventListener("submit", handleAuth);
  $("#register-form").addEventListener("submit", handleAuth);
  $("#profile-form").addEventListener("submit", saveProfile);
  $("#upload-form").addEventListener("submit", uploadResume);
  $("#resume-builder-form").addEventListener("submit", generateResume);
  $("#resume-list").addEventListener("click", handleResumeAction);
  $("#logout-button").addEventListener("click", logout);
  $("#mobile-menu").addEventListener("click", () => setMobileMenuOpen(!$(".sidebar").classList.contains("open")));
  $("#sidebar-backdrop").addEventListener("click", () => setMobileMenuOpen(false));
  $("#app-brand").addEventListener("click", (event) => { event.preventDefault(); navigate("dashboard"); });
  $$('[data-route]').forEach((button) => button.addEventListener("click", () => navigate(button.dataset.route)));
  $$('[data-go]').forEach((button) => button.addEventListener("click", () => navigate(button.dataset.go)));
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-open-profile]")) openProfileEditor();
  });
  $("#open-builder").addEventListener("click", () => { populateBuilder(); openModal("#builder-modal"); });
  $$('[data-close-modal]').forEach((item) => item.addEventListener("click", () => closeModal("#builder-modal")));
  $$('[data-close-profile]').forEach((item) => item.addEventListener("click", () => requestCloseProfile()));
  $$('[data-close-preview]').forEach((item) => item.addEventListener("click", () => closeModal("#preview-modal")));
  $("#resume-file").addEventListener("change", (event) => {
    $(".file-label span").textContent = event.target.files[0]?.name || "Selecionar arquivo";
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if ($$('.modal:not(.hidden)').length) {
        const modal = $$('.modal:not(.hidden)').at(-1);
        if (modal.id === "profile-modal") requestCloseProfile();
        else closeModal(`#${modal.id}`);
      } else if ($('.sidebar').classList.contains('open')) setMobileMenuOpen(false);
    }
  });
}

async function boot() {
  bindEvents();
  try {
    const [meta, me] = await Promise.all([api("/api/meta"), api("/api/me")]);
    updateDate(meta);
    if (me.authenticated) {
      await enterApplication(me);
    }
  } catch (error) {
    toast("Não foi possível iniciar a aplicação. Atualize a página e tente novamente.", "error");
  }
}

boot();
