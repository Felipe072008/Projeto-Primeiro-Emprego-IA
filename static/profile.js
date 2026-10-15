const profileSections = {
  contact: {title: 'Dados pessoais e contato', hint: 'Seus contatos e sua localização.'},
  goals: {title: 'Pretensões profissionais', hint: 'Escolha sua direção e os tipos de oportunidade que deseja.'},
  experiences: {title: 'Experiências profissionais', hint: 'Aprendizagem, estágio e outras vivências reais também contam.', singular: 'experiência'},
  education: {title: 'Formação acadêmica', hint: 'Sua escolaridade e os cursos de formação.', singular: 'formação'},
  courses: {title: 'Cursos e certificações', hint: 'Registre somente cursos que você está fazendo ou já fez.', singular: 'curso'},
  skills: {title: 'Habilidades', hint: 'Adicione um conhecimento por vez.'},
  languages: {title: 'Idiomas', hint: 'Informe o nível que representa seu conhecimento.', singular: 'idioma'},
  projects: {title: 'Projetos e voluntariado', hint: 'Valorize sua participação na escola, na comunidade ou em projetos pessoais.', singular: 'projeto'},
  availability: {title: 'Disponibilidade', hint: 'Conte quais períodos e dias combinam com sua rotina.'},
};
const educationLevels = ['Fundamental Incompleto','Fundamental Completo','Médio Incompleto','Médio Completo','Cursando Ensino Médio','Superior Incompleto','Cursando Superior','Superior Completo'];
let profileEditor = null;

function populateProfileForm() { renderProfileSummary(); }
function sectionData(section) { return state.me.profile.sections[section]; }
function sectionButton(section, text = 'Editar', index = '', accessible = '') {
  return `<button type="button" class="section-action" data-profile-section="${section}" data-profile-index="${index}" aria-label="${escapeHtml(accessible || text+' '+profileSections[section].title)}">${text}</button>`;
}
function recordSummary(section, item) {
  if (section === 'experiences') return [item.role, `${item.company} · ${item.contract || 'Vínculo não informado'}`, `${catalogDate(item.start)} — ${item.current ? 'atualmente' : item.end ? catalogDate(item.end) : 'Término não informado'}`, item.description];
  if (section === 'education') return [item.course || item.level, `${item.institution} · ${item.level}`, `${item.status}${item.year ? ` · ${item.status === 'Cursando' ? 'Previsão' : item.status === 'Concluído' ? 'Conclusão' : 'Ano informado'}: ${item.year}` : ''}`, [item.city,item.state].filter(Boolean).join(' / ')];
  if (section === 'courses') return [item.name, item.institution, `${item.status}${item.hours ? ` · ${item.hours}h` : ''}${item.year ? ` · ${item.status === 'Cursando' ? 'Previsão' : 'Ano'}: ${item.year}` : ''}`, ''];
  if (section === 'languages') return [item.language,item.level,'',''];
  return [item.title,item.context,[item.start,item.end].filter(Boolean).map(catalogDate).join(' — '),item.description];
}
function recordCards(section, data, inEditor = false) {
  const records = data.items.map((item,index)=>({item,index}));
  if (section === 'experiences') records.sort((a,b)=>Number(b.item.current)-Number(a.item.current) || b.item.start.localeCompare(a.item.start));
  return records.map(({item,index})=>{
    const [title,subtitle,period,description] = recordSummary(section,item);
    const edit = inEditor ? `<button type="button" class="small-button" data-edit-draft="${index}" aria-label="Editar ${escapeHtml(title)}">Editar</button>` : sectionButton(section,'Editar',index,'Editar '+title);
    const remove = `<button type="button" class="small-button danger" ${inEditor ? 'data-remove-draft' : 'data-remove-record'}="${index}" data-record-section="${section}" aria-label="Excluir ${escapeHtml(title)}">Excluir</button>`;
    const certificate = section==='courses' && item.certificate_url ? `<a href="${escapeHtml(item.certificate_url)}" target="_blank" rel="noopener noreferrer">Ver certificado ↗</a>` : '';
    return `<article class="profile-info-card profile-record"><div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(subtitle)}</p>${period ? `<p class="muted">${escapeHtml(period)}</p>` : ''}${description ? `<p class="experience-copy">${escapeHtml(description)}</p>` : ''}${certificate}</div><div class="profile-record-actions">${edit}${remove}</div></article>`;
  }).join('');
}
function renderProfileSummary() {
  const target = $('#profile-summary');
  if (!state.me?.profile?.sections || !target) return;
  const {profile,user} = state.me;
  const blocks = Object.entries(profileSections).map(([section,config])=>{
    const data = sectionData(section);
    let content = '';
    if (section === 'contact') content = `<div class="profile-info-grid">${[['Telefone',data.phone],['Idade',data.age ? data.age+' anos' : ''],['Cidade / Estado',[data.city,data.state].filter(Boolean).join(' / ')]].map(([label,value])=>`<article class="profile-info-card"><span>${label}</span><p>${profileText(value)}</p></article>`).join('')}</div>`;
    else if (section === 'goals') content = `<div class="profile-info-grid"><article class="profile-info-card"><span>Área principal</span><strong>${profileText(data.desired_area)}</strong></article><article class="profile-info-card"><span>Objetivo</span><p>${profileText(data.objective)}</p></article><article class="profile-info-card"><span>Pretensão salarial</span><p>${profileText(data.salary)}</p></article></div><div class="profile-tags">${data.secondary_areas.map(v=>`<span>${escapeHtml(v)}</span>`).join('')}${data.contracts.map(v=>`<span>${({aprendiz:'Jovem Aprendiz',estagio:'Estágio',clt:'CLT'})[v]}</span>`).join('')}${data.work_modes.map(v=>`<span>${escapeHtml(v)}</span>`).join('')}</div>`;
    else if (section === 'availability') content = `<div class="profile-info-grid">${[['Períodos',data.periods.join(', ')],['Dias',data.days.join(', ')],['Outra cidade',data.other_city],['Viagens',data.travel]].map(([label,value])=>`<article class="profile-info-card"><span>${label}</span><p>${profileText(value)}</p></article>`).join('')}</div>`;
    else {
      if (section === 'education') content += `<p><b>Escolaridade atual:</b> ${profileText(data.level)}</p>`;
      if (section === 'skills') content += `<div class="profile-tags">${data.items.map(item=>`<span>${escapeHtml(item.name)}</span>`).join('')}</div>`;
      else content += `<div class="profile-record-grid">${recordCards(section,data)}</div>`;
      if (data.legacy) content += `<article class="profile-info-card legacy-record"><span>Informações anteriores</span><p class="experience-copy">${escapeHtml(data.legacy)}</p></article>`;
      if (section === 'experiences' && data.no_experience) content += '<p class="not-informed">Você informou que ainda não tem experiência profissional.</p>';
      else if (!data.items.length && !data.legacy) content += `<div class="profile-empty-state"><span>+</span><p>${section === 'experiences' ? 'Seu primeiro emprego pode começar aqui. Projetos e habilidades também ajudam a contar sua história.' : config.hint}</p></div>`;
    }
    const add = config.singular ? sectionButton(section,`Adicionar ${config.singular}`,'new') : '';
    return `<section id="profile-block-${section}" class="profile-summary-section"><div class="profile-section-heading"><div><p class="eyebrow">Meu perfil</p><h2>${config.title}</h2></div><div class="section-actions">${sectionButton(section)}${add}</div></div>${content}</section>`;
  }).join('');
  const missing = profile.missing_fields || [];
  target.innerHTML = `<section class="profile-overview-card"><div class="profile-avatar">${escapeHtml(user.name[0] || 'P')}</div><div class="profile-overview-main"><p class="eyebrow">Seu espaço profissional</p><h2>${escapeHtml(user.name)}</h2><p>${escapeHtml(user.email)}</p><p class="profile-basic-status">${missing.length ? `Para completar o básico: ${escapeHtml(missing.join(', '))}.` : 'Seu perfil básico está completo. Continue acrescentando suas vivências no seu ritmo.'}</p></div><div class="profile-completion"><span>${state.me.completion}%</span><small>perfil básico</small></div></section>${blocks}`;
}

function editorField(name,label,value='',options={}) {
  const id = 'profile-field-'+name;
  const attrs = `id="${id}" name="${name}" ${options.required ? 'required' : ''} ${options.disabled ? 'disabled' : ''}`;
  let control;
  if (options.choices) control = `<select ${attrs}><option value="">Selecione</option>${options.choices.map(v=>`<option value="${escapeHtml(v)}" ${v===value ? 'selected' : ''}>${escapeHtml(v)}</option>`).join('')}</select>`;
  else if (options.textarea) control = `<textarea ${attrs} maxlength="${options.limit || 2000}">${escapeHtml(value)}</textarea>`;
  else control = `<input ${attrs} type="${options.type || 'text'}" value="${escapeHtml(value)}" maxlength="${options.limit || 300}" ${options.numeric ? 'inputmode="numeric" pattern="[0-9]*" data-numeric-limit="'+options.numeric+'"' : ''} ${options.placeholder ? `placeholder="${escapeHtml(options.placeholder)}"` : ''} />`;
  if (options.autocomplete) {
    const kind = options.autocomplete;
    control = control.replace(' />',` autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="${id}-options" />`);
    return `<div class="autocomplete-field editor-field" data-autocomplete="${kind}"><label for="${id}">${label}${options.required?' *':''}</label>${control}<div class="autocomplete-list" id="${id}-options" role="listbox" hidden></div><span class="field-error" data-error-for="${name}" id="${id}-error"></span></div>`;
  }
  return `<div class="editor-field"><label for="${id}">${label}${options.required?' *':''}</label>${control}<span class="field-error" data-error-for="${name}" id="${id}-error"></span></div>`;
}
function checks(name,title,choices,selected) {
  return `<fieldset class="profile-choice-group"><legend>${title}</legend>${choices.map(([value,label])=>`<label><input type="checkbox" name="${name}" value="${value}" ${selected.includes(value)?'checked':''} /> ${label}</label>`).join('')}</fieldset>`;
}
function legacyField(data) { return data.legacy ? editorField('legacy','Informações anteriores — revise ou mantenha este texto',data.legacy,{textarea:true,limit:12000}) : ''; }
function blankRecord(section) {
  const fields = {experiences:'role company contract start end description',education:'level course institution status year city state',courses:'name institution hours status year certificate_url',languages:'language level',projects:'title context start end description'};
  const item = Object.fromEntries(fields[section].split(' ').map(field=>[field,'']));
  if(section==='experiences') item.current=false;
  return item;
}
function itemFields(section,item) {
  const field=(name,label,options={})=>editorField(name,label,item[name],options);
  if(section==='experiences') return field('role','Cargo ou função',{required:true})+field('company','Empresa',{required:true})+field('contract','Tipo de vínculo',{choices:['Jovem Aprendiz','Estágio','CLT','Outra experiência']})+field('start','Data de início',{type:'date',required:true})+field('end','Data de término',{type:'date',disabled:item.current})+`<label class="profile-check"><input type="checkbox" name="current" ${item.current?'checked':''} /> É meu trabalho atual</label>`+field('description','Principais atividades realizadas',{textarea:true});
  if(section==='education') return field('level','Nível da formação',{choices:educationLevels,required:true})+field('course','Nome do curso (quando aplicável)')+field('institution','Instituição de ensino',{required:true})+field('status','Situação',{choices:['Cursando','Concluído','Interrompido'],required:true})+field('year','Ano de conclusão ou previsão',{numeric:4})+field('city','Cidade',{autocomplete:'city'})+field('state','Estado',{autocomplete:'state'});
  if(section==='courses') return field('name','Nome do curso',{required:true})+field('institution','Instituição',{required:true})+field('hours','Carga horária (horas)',{numeric:5})+field('status','Situação',{choices:['Cursando','Concluído','Interrompido'],required:true})+field('year','Ano de conclusão ou previsão',{numeric:4})+field('certificate_url','Link do certificado (opcional)',{type:'url'});
  if(section==='languages') return field('language','Idioma',{required:true,placeholder:'Ex.: Português, Inglês, Libras'})+`<datalist id="language-suggestions">${['Português','Inglês','Espanhol','Francês','Alemão','Italiano','Japonês','Mandarim','Libras'].map(v=>`<option value="${v}">`).join('')}</datalist>`+field('level','Nível',{choices:['Básico','Intermediário','Avançado','Fluente','Nativo'],required:true});
  return field('title','Título do projeto ou voluntariado',{required:true})+field('context','Instituição ou contexto')+field('start','Data de início (opcional)',{type:'date'})+field('end','Data de término (opcional)',{type:'date'})+field('description','Descreva sua participação',{textarea:true,required:true});
}
function readEditorData() {
  const {section,draft,itemIndex} = profileEditor;
  const data = structuredClone(draft);
  const form = $('#profile-form');
  const values = Object.fromEntries(new FormData(form));
  if(itemIndex !== null) {
    const item = Object.fromEntries(Object.keys(blankRecord(section)).map(field=>[field,field==='current'?!!form.elements.current.checked:values[field] || '']));
    if(item.current) item.end='';
    if(itemIndex==='new') data.items.push(item); else data.items[itemIndex]=item;
    if(section==='education' && !data.level) data.level=item.level;
    if(section==='experiences') data.no_experience=false;
  } else if(section==='contact') for(const field of ['phone','age','city','state']) data[field]=values[field] || '';
  else if(section==='goals') {
    for(const field of ['desired_area','objective','salary']) data[field]=values[field] || '';
    for(const field of ['contracts','work_modes']) data[field]=new FormData(form).getAll(field);
  } else if(section==='availability') {
    for(const field of ['periods','days']) data[field]=new FormData(form).getAll(field);
    for(const field of ['other_city','travel']) data[field]=values[field] || '';
  } else {
    if('legacy' in values) data.legacy=values.legacy;
    if(section==='education') data.level=values.level || '';
    if(section==='experiences') data.no_experience=!!form.elements.no_experience?.checked;
  }
  return data;
}
function renderProfileEditor() {
  const {section,draft,itemIndex} = profileEditor;
  const config = profileSections[section];
  const form = $('#profile-form');
  $('#profile-modal-title').textContent = itemIndex!==null ? `${itemIndex==='new'?'Adicionar':'Editar'} ${config.singular}` : config.title;
  $('#profile-modal-hint').textContent = config.hint;
  let fields='';
  if(itemIndex!==null) fields=itemFields(section,itemIndex==='new'?blankRecord(section):draft.items[itemIndex]);
  else if(section==='contact') fields=editorField('account_name','Nome completo',state.me.user.name,{disabled:true})+editorField('account_email','E-mail',state.me.user.email,{disabled:true})+editorField('phone','Telefone',draft.phone,{required:true,numeric:11})+editorField('age','Idade',draft.age,{required:true,numeric:3})+editorField('city','Cidade',draft.city,{required:true,autocomplete:'city'})+editorField('state','Estado',draft.state,{required:true,autocomplete:'state'});
  else if(section==='goals') fields=editorField('desired_area','Área profissional principal',draft.desired_area,{required:true,autocomplete:'desired_area'})+editorField('objective','Objetivo profissional',draft.objective,{textarea:true})+editorField('salary','Pretensão salarial (opcional)',draft.salary,{placeholder:'Ex.: A combinar'})+`<div class="span-3"><p>Áreas adicionais (até 3)</p><div class="profile-tags">${draft.secondary_areas.map((v,i)=>`<span>${escapeHtml(v)} <button type="button" data-remove-area="${i}" aria-label="Remover ${escapeHtml(v)}">×</button></span>`).join('')}</div>${editorField('secondary_choice','Adicionar outra área','',{autocomplete:'desired_area'})}<button type="button" class="small-button" data-add-area>Adicionar área</button><span class="field-error" data-error-for="secondary_areas"></span></div>`+checks('contracts','Tipos de oportunidade',[['aprendiz','Jovem Aprendiz'],['estagio','Estágio'],['clt','CLT']],draft.contracts)+checks('work_modes','Modalidades de trabalho',[['Presencial','Presencial'],['Híbrido','Híbrido'],['Remoto','Remoto']],draft.work_modes)+`<p class="muted span-3">Sem marcar um tipo, usamos as escolhas de área. Modalidade de trabalho é uma preferência informativa; confira o anúncio.</p>`;
  else if(section==='availability') fields=checks('periods','Períodos disponíveis',['Manhã','Tarde','Noite'].map(v=>[v,v]),draft.periods)+checks('days','Dias disponíveis',['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo'].map(v=>[v,v]),draft.days)+editorField('other_city','Aceita trabalhar em outra cidade?',draft.other_city,{choices:['Sim','Não']})+editorField('travel','Disponível para viagens?',draft.travel,{choices:['Sim','Não']});
  else {
    if(section==='education') fields+=editorField('level','Escolaridade atual',draft.level,{choices:educationLevels,required:true});
    if(section==='experiences') fields+=`<label class="profile-check span-3"><input type="checkbox" name="no_experience" ${draft.no_experience?'checked':''} /> Ainda não tenho experiência profissional</label><span class="field-error" data-error-for="no_experience"></span>`;
    fields+=legacyField(draft);
    if(section==='skills') fields+=`<div class="span-3">${editorField('skill_name','Adicionar habilidade','',{placeholder:'Ex.: Excel, organização, comunicação'})}<datalist id="skill-suggestions">${['Excel','Organização','Comunicação','Atendimento ao público','Trabalho em equipe','Python','Informática básica','Canva'].map(v=>`<option value="${v}">`).join('')}</datalist><button type="button" class="small-button" data-add-skill>Adicionar habilidade</button><div class="profile-tags">${draft.items.map((item,i)=>`<span>${escapeHtml(item.name)} <button type="button" data-remove-draft="${i}" aria-label="Remover ${escapeHtml(item.name)}">×</button></span>`).join('')}</div></div>`;
    else fields+=`<div class="span-3 profile-record-grid">${recordCards(section,draft,true)}</div><button type="button" class="button button--outline" data-new-draft>Adicionar ${config.singular}</button>`;
    fields+='<span class="field-error span-3" data-error-for="items"></span>';
  }
  form.innerHTML=`<p class="editor-form-error" data-error-for="_form" role="alert"></p><div class="profile-editor-grid">${fields}</div><div class="form-actions profile-modal-actions"><p class="form-note">* Campos obrigatórios desta seção.</p><div><button class="button button--outline" type="button" data-cancel-section>Cancelar</button><button class="button button--primary" type="submit">Salvar ${itemIndex!==null?config.singular:'informações'}</button></div></div>`;
  bindOptionLists(form);
  $('[name="skill_name"]',form)?.setAttribute('list','skill-suggestions');
  $('[name="language"]',form)?.setAttribute('list','language-suggestions');
}
function openProfileEditor(section='contact', index='') {
  if(!state.me?.profile?.sections) return;
  if(!profileSections[section]) section='contact';
  profileEditor={section,draft:structuredClone(sectionData(section)),baseline:'',itemIndex:index===''?null:index==='new'?'new':Number(index),pending:false};
  renderProfileEditor();
  profileEditor.baseline=JSON.stringify(readEditorData());
  openModal('#profile-modal');
  const first=$('input:not(:disabled), select, textarea', $('#profile-form'));
  first?.focus();
}
function requestCloseProfile() {
  if(profileEditor?.pending) return;
  if(profileEditor && profileHasChanges() && !window.confirm('Descartar as alterações que ainda não foram salvas?')) return;
  closeAllOptionLists();
  closeModal('#profile-modal');
  profileEditor=null;
}
function profileHasChanges() {
  const fields=$('#profile-form').elements;
  return JSON.stringify(readEditorData())!==profileEditor.baseline || !!fields?.skill_name?.value.trim() || !!fields?.secondary_choice?.value.trim();
}
function showProfileErrors(errors) {
  const form=$('#profile-form');
  $$('[data-error-for]',form).forEach(el=>el.textContent='');
  $$('[aria-invalid]',form).forEach(el=>{el.removeAttribute('aria-invalid');el.removeAttribute('aria-describedby');});
  let focused=false;
  for(const [path,message] of Object.entries(errors)) {
    const name=path.startsWith('items.') && profileEditor.itemIndex!==null ? path.split('.').at(-1) : path;
    const label=$$('[data-error-for]',form).find(el=>el.dataset.errorFor===name) || $('[data-error-for="_form"]',form);
    label.textContent=message;
    const input=form.elements.namedItem(name);
    if(input?.setAttribute) {input.setAttribute('aria-invalid','true');input.setAttribute('aria-describedby',label.id);if(!focused){input.focus();focused=true;}}
  }
}
async function saveProfile(event) {
  event.preventDefault();
  if(profileEditor.pending) return;
  if(profileEditor.section==='skills' && $('#profile-form').elements.skill_name.value.trim() && !addDraftSkill()) return;
  const data=readEditorData();
  const section=profileEditor.section;
  profileEditor.pending=true;
  const save=$('button[type="submit"]',$('#profile-form'));
  save.disabled=true;
  try {
    const result=await api(`/api/profile/${section}`,{method:'PATCH',body:data});
    state.me.profile=result.profile;
    state.me.completion=result.completion;
    closeModal('#profile-modal');
    profileEditor=null;
    renderProfileSummary();
    loadDashboard();
    const block=$(`#profile-block-${section}`);
    block?.scrollIntoView({block:'nearest',behavior:'smooth'});
    $('button',block)?.focus({preventScroll:true});
    toast(result.message);
  } catch(error) {showProfileErrors(error.fields || {_form:error.message});}
  finally {if(profileEditor) profileEditor.pending=false;save.disabled=false;}
}
function addDraftSkill() {
  const input=$('#profile-form').elements.skill_name;
  const value=input.value.trim();
  if(!value) return false;
  if(profileEditor.draft.items.some(item=>normalizeOptionText(item.name)===normalizeOptionText(value))) {showProfileErrors({_form:'Esta habilidade já foi adicionada.'});return false;}
  profileEditor.draft=readEditorData();
  profileEditor.draft.items.push({name:value});
  renderProfileEditor();
  $('#profile-form').elements.skill_name.focus();
  return true;
}
async function removeProfileRecord(section,index) {
  if(!window.confirm('Excluir este registro do seu perfil?')) return;
  const data=structuredClone(sectionData(section));
  data.items.splice(index,1);
  try {
    const result=await api(`/api/profile/${section}`,{method:'PATCH',body:data});
    state.me.profile=result.profile;state.me.completion=result.completion;
    renderProfileSummary();loadDashboard();toast('Registro excluído.');
    $('button',$(`#profile-block-${section}`))?.focus({preventScroll:true});
  } catch(error){toast(error.message,'error');}
}
function bindProfileEvents() {
  $('#profile-form').addEventListener('input',event=>{
    if(event.target.dataset.numericLimit) event.target.value=event.target.value.replace(/\D/g,'').slice(0,Number(event.target.dataset.numericLimit));
  });
  $('#profile-form').addEventListener('change',event=>{
    if(event.target.name==='current') {const end=event.currentTarget.elements.end;end.disabled=event.target.checked;if(end.disabled)end.value='';}
  });
  $('#profile-form').addEventListener('click',async event=>{
    if(!profileEditor || profileEditor.pending) return;
    const button=event.target.closest('button');if(!button)return;
    if(button.hasAttribute('data-cancel-section')) return requestCloseProfile();
    if(button.hasAttribute('data-add-skill')) return addDraftSkill();
    if(button.hasAttribute('data-add-area')) {
      const value=event.currentTarget.elements.secondary_choice.value.trim();
      const options=(await loadOptionData('occupations')).options;
      if(!options.some(item=>item.value===value)) return showProfileErrors({_form:'Selecione uma área sugerida.'});
      if(profileEditor.draft.secondary_areas.length>=3) return showProfileErrors({secondary_areas:'Adicione até três áreas.'});
      profileEditor.draft=readEditorData();
      if(value!==profileEditor.draft.desired_area && !profileEditor.draft.secondary_areas.includes(value)) profileEditor.draft.secondary_areas.push(value);
      renderProfileEditor();return;
    }
    if(button.hasAttribute('data-remove-area')) {profileEditor.draft=readEditorData();profileEditor.draft.secondary_areas.splice(Number(button.dataset.removeArea),1);renderProfileEditor();return;}
    if(button.hasAttribute('data-remove-draft')) {
      if(profileEditor.section!=='skills' && !window.confirm('Remover este registro? A exclusão será aplicada ao salvar.')) return;
      profileEditor.draft=readEditorData();profileEditor.draft.items.splice(Number(button.dataset.removeDraft),1);renderProfileEditor();return;
    }
    if(button.hasAttribute('data-new-draft') || button.hasAttribute('data-edit-draft')) {
      if(profileHasChanges()) return showProfileErrors({_form:'Salve ou cancele as alterações desta seção antes de editar um registro.'});
      profileEditor.itemIndex=button.hasAttribute('data-new-draft')?'new':Number(button.dataset.editDraft);renderProfileEditor();profileEditor.baseline=JSON.stringify(readEditorData());$('input,select,textarea',event.currentTarget)?.focus();
    }
  });
  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-profile-section]');
    if(button) openProfileEditor(button.dataset.profileSection,button.dataset.profileIndex);
    const remove=event.target.closest('[data-remove-record]');
    if(remove) removeProfileRecord(remove.dataset.recordSection,Number(remove.dataset.removeRecord));
  });
}
