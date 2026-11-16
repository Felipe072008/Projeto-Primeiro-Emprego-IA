/* O painel usa somente os metadados permitidos pelo backend. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const results = $('#admin-results'), toolbar = $('#admin-toolbar'), message = $('#admin-message');
  const csrf = $('meta[name=csrf-token]').content;
  const titles = {overview:'Visão geral',users:'Usuários',resumes:'Currículos',jobs:'Vagas',courses:'Cursos',system:'Sistema',activities:'Atividades',account:'Conta'};
  const areaOptions = {tecnologia:'Tecnologia',administracao:'Administração',financeiro:'Finanças e contabilidade',comercial:'Comércio e atendimento',marketing:'Marketing e Comunicação',logistica:'Logística',rh:'Recursos humanos',industria:'Indústria e Engenharia',saude:'Saúde',educacao:'Educação e Pedagogia'};
  let current = 'overview', onSave = null, serial = 0;
  function element(tag, text, attrs = {}) {
    const el = document.createElement(tag);
    if (text !== null && text !== undefined) el.textContent = String(text);
    for (const [key,value] of Object.entries(attrs)) el.setAttribute(key,value);
    return el;
  }
  function button(text, handler, className = '') {
    const el = element('button',text,{type:'button',class:className});
    el.addEventListener('click', async () => {
      el.disabled = true;
      try { await handler(); } catch (error) { message.textContent = error.message; }
      finally { el.disabled = false; }
    });
    return el;
  }
  async function api(path, data, method = 'POST') {
    const response = await fetch(path, {method:data === undefined ? 'GET' : method, credentials:'same-origin',
      headers:{'X-Requested-With':'FirstJob','X-CSRF-Token':csrf,'Content-Type':'application/json'},
      body:data === undefined ? undefined : JSON.stringify(data)});
    let result;
    try { result = await response.json(); } catch { throw new Error('Não foi possível concluir a solicitação.'); }
    if (!response.ok) {
      if (response.status === 401) { results.replaceChildren(); toolbar.replaceChildren(); }
      throw new Error(response.status === 401 ? 'Sessão expirada. Volte à página inicial para entrar novamente.' : result.error || 'Solicitação inválida.');
    }
    return result;
  }
  const date = value => value ? new Date(value).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'}) : 'Não registrado';
  const bytes = value => value == null ? 'Não disponível' : (value/1024).toLocaleString('pt-BR',{maximumFractionDigits:1}) + ' KB';
  function table(headers, rows) {
    if (!rows.length) { results.append(element('p','Nenhum registro encontrado.')); return; }
    const wrapper = element('div',null,{class:'admin-table-wrap',tabindex:'0','aria-label':'Tabela com rolagem horizontal'});
    const table = element('table',null,{class:'admin-table'}), head = element('thead'), tr = element('tr');
    for (const title of headers) tr.append(element('th',title,{scope:'col'}));
    head.append(tr); table.append(head);
    const body = element('tbody');
    for (const cells of rows) {
      const row = element('tr');
      for (const value of cells) { const td = element('td'); td.append(value instanceof Node ? value : document.createTextNode(value == null ? 'Não registrado' : String(value))); row.append(td); }
      body.append(row);
    }
    table.append(body); wrapper.append(table); results.append(wrapper);
  }
  function field(name, label, options = {}) {
    const wrapper = element('label',label);
    let input;
    if (options.choices) {
      input = element('select',null,{name});
      if (!options.multiple && options.required !== false) input.append(element('option','Selecione',{value:''}));
      for (const [value,title] of Object.entries(options.choices)) input.append(element('option',title,{value}));
      if (options.multiple) { input.multiple = true; input.size = 6; }
    } else { input = element(options.textarea ? 'textarea' : 'input',null,{name}); }
    if (!options.choices && !options.textarea) input.type = options.type || 'text';
    if (options.max) input.maxLength = options.max;
    if (options.min) input.minLength = options.min;
    input.required = options.required !== false;
    if (options.multiple) for (const option of input.options) option.selected = (options.value || []).includes(option.value);
    else input.value = options.value ?? '';
    if (options.type === 'password') input.autocomplete = name === 'current_password' ? 'current-password' : 'new-password';
    wrapper.append(input);
    return wrapper;
  }
  function filters(fields, submit) {
    const form = element('form');
    for (const item of fields) form.append(item);
    form.append(element('button','Filtrar',{type:'submit',class:'button'}));
    form.addEventListener('submit', event => { event.preventDefault(); submit(new URLSearchParams(new FormData(form))).catch(error => { message.textContent = error.message; }); });
    toolbar.append(form);
  }
  function openEditor(title, fields, save) {
    $('#admin-edit-title').textContent = title;
    $('#admin-edit-error').textContent = '';
    $('#admin-edit-fields').replaceChildren(...fields);
    onSave = save;
    $('#admin-edit-dialog').showModal();
  }
  $('#admin-edit-close').addEventListener('click',() => $('#admin-edit-dialog').close());
  $('#admin-edit-form').addEventListener('submit',async event => {
    event.preventDefault();
    const submit = event.target.querySelector('[type=submit]'); submit.disabled = true;
    try { await onSave(new FormData(event.target)); $('#admin-edit-dialog').close(); await navigate(current); message.textContent = 'Operação concluída.'; }
    catch(error) { $('#admin-edit-error').textContent = error.message; }
    finally { submit.disabled = false; }
  });
  $('#admin-edit-dialog').addEventListener('keydown',event => {
    if (event.key !== 'Tab') return;
    const items = [...event.currentTarget.querySelectorAll('input,select,textarea,button')].filter(el=>!el.disabled);
    const first = items[0],last = items[items.length-1];
    if (event.shiftKey && document.activeElement===first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement===last) { event.preventDefault(); first.focus(); }
  });
  function actions(items) { const el = element('div',null,{class:'admin-actions'}); el.append(...items); return el; }
  async function users(query = new URLSearchParams()) {
    const data = await api('/admin-api/users?' + query);
    results.replaceChildren();
    results.append(element('p','Exibindo até 200 registros por busca. Use nome ou e-mail para localizar uma conta.',{class:'admin-note'}));
    table(['Nome','E-mail','Cadastro','Último acesso','Status','Perfil','Currículos','Ações'],data.items.map(user=>[
      user.name,user.email,date(user.created_at),date(user.last_login_at),user.status==='active'?'Ativo':'Desativado',user.completion+'%',user.resume_count,
      actions([button(user.status==='active'?'Desativar':'Reativar',async()=>{
        await api(`/admin-api/users/${user.id}/${user.status==='active'?'deactivate':'reactivate'}`,{}); await users(query);
      }), ...(user.status==='deactivated'?[button('Apagar de vez',()=>openEditor('Apagar conta definitivamente',[
        element('p','A conta e todos os seus currículos serão apagados. Esta ação é irreversível.'),
        field('confirmation',`Digite APAGAR ${user.id}`,{max:40})
      ],form=>api(`/admin-api/users/${user.id}/delete`,Object.fromEntries(form))))]:[])])
    ]));
  }
  function offerEditor(kind, row) {
    const v = row || {}, job = kind === 'jobs';
    const fields = [field('title','Título',{max:200,value:v.title}),
      field(job?'company':'institution',job?'Empresa':'Instituição',{max:200,value:v[job?'company':'institution']}),
      ...(job?[field('location','Local em Curitiba/PR',{max:200,value:v.location}),field('contract_type','Contrato',{choices:{aprendiz:'Jovem Aprendiz',estagio:'Estágio',clt:'CLT de entrada'},value:v.contract_type})]:[]),
      field('source','Fonte',{max:200,value:v.source}),field('original_url','Link HTTPS da oferta individual',{type:'url',max:2048,value:v.original_url}),
      field('description','Resumo confirmado na fonte',{textarea:true,max:5000,value:v.description}),
      field('requirements','Requisitos confirmados (um por linha)',{textarea:true,max:15000,required:job,value:(v.requirements||[]).join('\n')}),
      field('areas','Áreas (Ctrl ou Command para selecionar mais de uma)',{choices:areaOptions,multiple:true,value:v.areas}),
      field('availability_evidence','Evidência de oferta/inscrição aberta',{textarea:true,max:2000,value:v.availability_evidence}),
      field('review_by','Revisar até',{type:'date',value:v.review_by}),field('expires_on','Prazo informado pela fonte (opcional)',{type:'date',required:false,value:v.expires_on}),
      ...(!job?[
        field('course_type','Tipo',{choices:{livre:'Livre',tecnico:'Técnico',graduacao:'Graduação'},value:v.course_type}),
        field('duration','Carga horária (opcional)',{max:100,required:false,value:v.duration}),
        field('access_evidence','Evidência de acesso completo gratuito',{textarea:true,max:1500,value:v.access_evidence}),
        field('certificate','Condições do certificado',{textarea:true,max:1500,value:v.certificate}),
        field('certificate_status','Custo do certificado',{choices:{free:'Gratuito',paid:'Pago',unknown:'Não informado'},value:v.certificate_status}),
        field('certificate_source','Link das condições do certificado',{type:'url',max:2048,required:false,value:v.certificate_source})
      ]:[]),element('p','Salvar registra sua conferência nesta data. Confira a oferta oficial; não prorrogue uma data sem verificar a fonte.',{class:'admin-note'})];
    openEditor(row?'Editar oferta manual':'Adicionar oferta manual',fields,form=>{
      const payload = Object.fromEntries(form);
      payload.areas = form.getAll('areas');
      payload.requirements = payload.requirements.split('\n').map(v=>v.trim()).filter(Boolean);
      if (row) payload.action = 'edit';
      return api('/admin-api/catalog/' + kind + (row?'/'+row.admin_id:''),payload,row?'PATCH':'POST');
    });
  }
  async function catalog(kind,query = new URLSearchParams()) {
    const data = await api('/admin-api/catalog/' + kind + '?' + query);
    results.replaceChildren();
    results.append(element('p','Visibilidade é uma decisão administrativa. Prazos vencidos ou dados inválidos continuam impedindo a exibição pública.',{class:'admin-note'}));
    table(['Título','Empresa / instituição','Origem','Estado','Verificação','Link oficial','Ações'],data.items.map(row=>{
      const link = element('a','Consultar fonte',{href:row.original_url,target:'_blank',rel:'noopener noreferrer'});
      if (!/^https?:\/\//i.test(row.original_url||'')) link.removeAttribute('href');
      const controls = [];
      if (!row.is_removed) {
        if (row.origin==='manual') controls.push(button('Editar',()=>offerEditor(kind,row)));
        controls.push(button(row.is_hidden?'Reexibir':'Ocultar',async()=>{ await api(`/admin-api/catalog/${kind}/${row.admin_id}`,{action:row.is_hidden?'show':'hide'},'PATCH'); await catalog(kind,query); }));
        controls.push(button('Remover',async()=>{
          if (!window.confirm('Remover esta oferta do catálogo? A importação não a reativará.')) return;
          await api(`/admin-api/catalog/${kind}/${row.admin_id}`,{action:'remove'},'PATCH'); await catalog(kind,query);
        }));
      }
      return [row.title,row.company||row.institution,row.origin==='auto'?'Automática':'Manual',row.is_removed?'Removida':row.is_hidden?'Oculta':row.public_visible?'Visível':'Fora de validade/validação',date(row.last_verified_at)||row.checked_on,link,actions(controls)];
    }));
  }
  function info(title, pairs) {
    const block = element('section',null,{class:'admin-info'}); block.append(element('h2',title));
    const dl = element('dl'); for (const [key,value] of pairs) dl.append(element('dt',key),element('dd',value));
    block.append(dl); results.append(block);
  }
  async function navigate(view) {
    const requestId = ++serial; current = view;
    document.querySelectorAll('[data-view]').forEach(button=>{ button.disabled=true; });
    $('#admin-title').textContent = titles[view];
    for (const button of document.querySelectorAll('[data-view]')) button.setAttribute('aria-current',button.dataset.view===view?'page':'false');
    toolbar.replaceChildren(); results.replaceChildren(); message.textContent = 'Carregando…';
    try {
      if (view==='users') { filters([field('q','Nome ou e-mail',{required:false,max:120}),field('status','Status',{required:false,choices:{'':'Todos',active:'Ativo',deactivated:'Desativado'}})],users); await users(); }
      if (view==='jobs'||view==='courses') {
        filters([field('origin','Origem',{required:false,choices:{'':'Todas',auto:'Automática',manual:'Manual'}}),field('visibility','Estado',{required:false,choices:{'':'Todos',visible:'Visível',hidden:'Oculta',removed:'Removida'}})],q=>catalog(view,q));
        toolbar.append(button('Adicionar manual',()=>offerEditor(view), 'button button--primary')); await catalog(view);
      }
      if (view==='resumes') {
        const data = await api('/admin-api/resumes');
        results.append(element('p','Somente metadados. Currículos gerados são armazenados em JSON; o tamanho exibido não é o tamanho de um PDF. Até 200 registros.',{class:'admin-note'}));
        table(['Dono','Tipo','Data','Tamanho armazenado','Ação'],data.items.map(row=>[row.owner,row.kind==='uploaded'?'PDF enviado':'Gerado (JSON)',date(row.created_at),bytes(row.size_bytes),button('Excluir',async()=>{
          if (!window.confirm('Excluir definitivamente este currículo?')) return;
          await api('/admin-api/resumes/'+row.id,{},'DELETE'); await navigate(view);
        })]));
      }
      if (view==='overview') {
        const data = await api('/admin-api/overview'), cards = element('div',null,{class:'admin-cards'});
        for (const [title,values] of [['Usuários',{'Total':data.users.total,'Ativos':data.users.active||0,'Desativados':data.users.deactivated||0,'Cadastros em 7 dias':data.users.registrations_7d||0,'Cadastros em 30 dias':data.users.registrations_30d||0,'Perfis completos':data.users.complete_profiles}],['Currículos',{'Enviados':data.resumes.uploaded||0,'Gerados':data.resumes.generated||0}],...['jobs','courses'].map(kind=>[titles[kind],{'Total':data.catalogs[kind].total,'Visíveis':data.catalogs[kind].visible,'Ocultos':data.catalogs[kind].hidden,'Removidos':data.catalogs[kind].removed,'Fora de validade/validação':data.catalogs[kind].ineligible,'Automáticos':data.catalogs[kind].auto,'Manuais':data.catalogs[kind].manual}])]) {
          const card = element('article'); card.append(element('h2',title)); for (const [key,value] of Object.entries(values)) card.append(element('p',key+': '+value)); cards.append(card);
        }
        results.append(cards);
      }
      if (view==='system') {
        const data = await api('/admin-api/system');
        info('Armazenamento e horário',[['Agora (Brasília)',date(data.time)],['Banco principal',bytes(data.database_bytes)],['Banco administrativo',bytes(data.admin_database_bytes)],['Banco do catálogo',bytes(data.catalog_database_bytes)],['Uploads',bytes(data.uploads_bytes)]]);
        for (const kind of ['jobs','courses']) {
          const state = data.updates[kind], last = state.last_attempt;
          info('Atualização de '+titles[kind].toLowerCase(),[['Última tentativa',date(last?.last_attempt_at)],['Resultado',last?.sync_status||'Nunca registrada'],['Mensagem',last?.message||'Nenhuma execução registrada'],['Última verificação bem-sucedida',date(state.last_success_at)]]);
        }
        results.append(element('p',data.scheduling,{class:'admin-note'}));
      }
      if (view==='activities') {
        const data = await api('/admin-api/activities');
        results.append(element('h2','Últimas 200 atividades'));
        table(['Data','Ação','Alvo','Detalhes'],data.items.map(row=>[date(row.created_at),row.action,row.target_type+' '+row.target_id,row.details]));
        results.append(element('h2','Últimas 200 tentativas'));
        table(['Data','IP','Etapa','Resultado'],data.attempts.map(row=>[date(row.created_at*1000),row.ip,row.kind,row.success?'Aceita':'Negada']));
      }
      if (view==='account') {
        results.append(element('p','A troca encerra todas as sessões administrativas. Nenhuma credencial é exibida.'));
        results.append(button('Trocar senha ou PIN',()=>openEditor('Atualizar credenciais',[
          field('current_password','Senha atual',{type:'password',max:256}),field('new_password','Nova senha (12 a 256 caracteres; opcional)',{type:'password',min:12,max:256,required:false}),field('new_pin','Novo PIN (6 dígitos; opcional)',{type:'password',min:6,max:6,required:false})
        ],async form=>{ await api('/admin-api/account',Object.fromEntries(form)); window.location.assign('/'); }),'button button--primary'));
      }
      if (requestId===serial) message.textContent = '';
    } catch(error) { message.textContent = error.message; }
    finally { document.querySelectorAll('[data-view]').forEach(button=>{ button.disabled=false; }); }
  }
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>navigate(button.dataset.view)));
  $('#admin-logout').addEventListener('click',async()=>{ try { await api('/admin-api/logout',{}); window.location.assign('/'); } catch(error) { message.textContent = error.message; } });
  navigate('overview');
})();
