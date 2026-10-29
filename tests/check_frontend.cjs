const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

(async () => {
  const calls = [];
  const fields = ['full_name', 'email', 'headline', 'location', 'phone', 'course',
    'objective', 'education', 'professional_experience', 'academic_experience',
    'courses', 'skills', 'languages', 'additional_information'].map(name => ({name, value: 'old'}));
  const context = vm.createContext({
    FormData: class {
      constructor(form) { this.entries=Object.entries(form.data || {}).flatMap(([name,value])=>(Array.isArray(value)?value:[value]).map(item=>[name,item])); }
      [Symbol.iterator]() { return this.entries[Symbol.iterator](); }
      getAll(name) { return this.entries.filter(entry=>entry[0]===name).map(entry=>entry[1]); }
    },
    structuredClone,
    document: {querySelector: () => ({dataset: {}, querySelectorAll: () => fields}), querySelectorAll: () => []},
    window: {scrollTo() {}, matchMedia: () => ({matches:true})},
    calls,
  });
  const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/profile.js'), 'utf8'), context);
  vm.runInContext(source.replace(/boot\(\);\s*$/, ''), context);
  const resumeMarkup = context.resumeSectionHtml({title:'Cursos e certificações',content:'<Curso> · Escola\nDescrição\n\nOutro curso · Outra escola'});
  assert.ok(resumeMarkup.includes('<strong>&lt;Curso&gt;</strong> · Escola'));
  assert.equal((resumeMarkup.match(/class="resume-record"/g) || []).length, 2);
  assert.ok(!resumeMarkup.includes('<Curso>'));
  const skillMarkup = context.resumeSectionHtml({title:'Habilidades',content:'Organização; Comunicação\n● Excel'});
  assert.equal((skillMarkup.match(/class="resume-bullet"/g) || []).length, 3);
  assert.ok(context.resumeContactHtml('41996201002').includes('(41) 99620-1002'));
  const originalNavigate = context.navigate;
  const originalReadEditorData = context.readEditorData;
  for (const [raw, formatted] of [['41996201002','(41) 99620-1002'],['1132345678','(11) 3234-5678'],['',''],['4199','4199']]) {
    assert.equal(context.formatProfilePhone(raw), formatted);
    assert.equal(context.formatProfilePhone(formatted), formatted);
  }
  const indexHtml = fs.readFileSync(path.join(__dirname, '../templates/index.html'), 'utf8');
  assert.deepEqual(Array.from(indexHtml.matchAll(/class="nav-link(?: active)?" data-route="([^"]+)"/g), match=>match[1]), ['dashboard','profile','jobs','courses','resume']);
  let modalClosed = false;
  const pendingModal = {
    classList: {contains: () => false, add: () => { modalClosed = true; }},
    querySelector: () => ({disabled: true}),
  };
  const initialQuery = context.document.querySelector;
  context.document.querySelector = () => pendingModal;
  context.closeModal('#preview-modal');
  assert.equal(modalClosed, false, 'A versão não pode ser fechada durante o salvamento.');
  context.document.querySelector = initialQuery;
  vm.runInContext(`
    api = async (url, options) => { calls.push(['api', url, options]); return {message: 'ok'}; };
    toast = (...args) => calls.push(['toast', ...args]);
    enterApplication = async () => calls.push(['enter']);
    navigate = route => calls.push(['navigate', route]);
  `, context);
  for (const mode of ['login', 'register']) {
    calls.length = 0;
    await context.handleAuth({preventDefault() {}, currentTarget: {id: mode + '-form', data: {email: 'teste@example.com'}}});
    assert.equal(calls[0][1], '/api/auth/' + mode);
    assert.equal(calls[0][2].method, 'POST');
    assert.equal(calls[0][2].body.email, 'teste@example.com');
    assert.equal(calls.filter(x => x[0] === 'enter').length, 1);
    assert.deepEqual(calls.filter(x => x[0] === 'navigate').map(x => x[1]), mode === 'register' ? ['profile'] : []);
  }
  calls.length = 0;
  vm.runInContext("api = async () => { throw new Error('invalid'); };", context);
  await context.handleAuth({preventDefault() {}, currentTarget: {id: 'login-form'}});
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [['toast', 'invalid', 'error']]);

  vm.runInContext(`state.me = {user: {name: 'Pessoa', email: 'teste@example.com'},
    profile: {city: 'Curitiba', state: 'PR', desired_area: 'Tecnologia', skills: 'Python', phone: '41999999999'}};`, context);
  context.populateBuilder();
  const values = Object.fromEntries(fields.map(x => [x.name, x.value]));
  assert.equal(values.full_name, 'Pessoa');
  assert.equal(values.location, 'Curitiba / PR');
  assert.equal(values.headline, 'Tecnologia');
  assert.equal(values.skills, 'Python');
  assert.equal(values.professional_experience, '');
  assert.equal(values.additional_information, '');
  vm.runInContext('state.me.profile = {};', context);
  context.populateBuilder();
  assert.equal(fields.find(x => x.name === 'skills').value, '');

  vm.runInContext(`state.me.profile.resume_fields = {education:'Superior · Escola · Cursando',
    professional_experience:'Cargo — Empresa', languages:'Inglês — Básico', additional_information:'Manhã'};`, context);
  context.populateBuilder();
  assert.equal(fields.find(x=>x.name==='education').value,'Superior · Escola · Cursando');
  assert.equal(fields.find(x=>x.name==='professional_experience').value,'Cargo — Empresa');
  assert.equal(fields.find(x=>x.name==='additional_information').value,'');
  const summary = context.recordSummary('education',{course:'Sistemas',level:'Cursando Superior',institution:'Escola',status:'Cursando',year:'2028'});
  assert.ok(summary[2].includes('Previsão: 2028'));
  const html = context.recordCards('projects',{items:[{title:'<script>bad</script>',context:'',start:'',end:'',description:'texto <b>literal</b>'}]});
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!html.includes('<script>'));

  const editorForm={data:{role:'Estagiário',company:'Empresa',contract:'Estágio',start:'2025-01-01',end:'2025-02-01',description:'Atividades reais'},elements:{current:{checked:true}}};
  context.document.querySelector=()=>editorForm;
  vm.runInContext("profileEditor={section:'experiences',draft:{legacy:'Texto antigo',items:[],no_experience:true},itemIndex:'new'};",context);
  let payload=context.readEditorData();
  assert.equal(payload.items[0].role,'Estagiário');
  assert.equal(payload.items[0].current,true);
  assert.equal(payload.items[0].end,'');
  assert.equal(payload.legacy,'Texto antigo');
  assert.equal(payload.no_experience,false);
  assert.equal(vm.runInContext('profileEditor.draft.items.length',context),0);
  editorForm.data={desired_area:'Estágio — Administração',objective:'Aprender',salary:'A combinar',contracts:['aprendiz','estagio'],work_modes:['Presencial']};
  vm.runInContext("profileEditor={section:'goals',draft:{secondary_areas:['Estágio — Logística']},itemIndex:null};",context);
  payload=context.readEditorData();
  assert.deepEqual(Array.from(payload.contracts),['aprendiz','estagio']);
  assert.deepEqual(Array.from(payload.secondary_areas),['Estágio — Logística']);
  assert.equal(payload.salary,'A combinar');
  editorForm.data={level:'Superior Completo',legacy:'Formação antiga'};
  vm.runInContext("profileEditor={section:'education',draft:{level:'Médio Completo',legacy:'',items:[]},itemIndex:null};",context);
  payload=context.readEditorData();
  assert.equal(payload.level,'Superior Completo');
  assert.equal(payload.legacy,'Formação antiga');

  editorForm.data={phone:'(41) 99620-1002',age:'18',city:'Curitiba',state:'Paraná'};
  vm.runInContext("profileEditor={section:'contact',draft:{},itemIndex:null};",context);
  payload=context.readEditorData();
  assert.equal(payload.phone,'41996201002');
  assert.deepEqual(Object.keys(context.validateContact(payload)),[]);
  editorForm.data={periods:['Tarde']};
  vm.runInContext("profileEditor={section:'availability',draft:{periods:['Manhã'],days:['Segunda'],other_city:'Não',travel:'Sim'},itemIndex:null};",context);
  payload=context.readEditorData();
  assert.deepEqual(Array.from(payload.periods),['Tarde']);
  assert.deepEqual(Array.from(payload.days),['Segunda']);
  assert.equal(payload.other_city,'Não');
  assert.equal(payload.travel,'Sim');
  vm.runInContext('bindOptionLists = () => {};',context);
  editorForm.querySelector=()=>null;
  context.renderProfileEditor();
  assert.ok(editorForm.innerHTML.includes('name="periods"'));
  for(const removed of ['days','other_city','travel']) assert.ok(!editorForm.innerHTML.includes(`name="${removed}"`));
  const handlers={};
  editorForm.addEventListener=(type,handler)=>{handlers[type]=handler;};
  context.document.addEventListener=()=>{};
  context.bindProfileEvents();
  const phoneInput={name:'phone',value:'(41) 99620-1002',dataset:{numericLimit:'11'}};
  handlers.input({target:phoneInput});
  assert.equal(phoneInput.value,'41996201002');
  handlers.focusout({target:phoneInput});
  assert.equal(phoneInput.value,'(41) 99620-1002');

  calls.length=0;
  context.document.querySelector=()=>({disabled:false,scrollIntoView(){},focus(){},querySelector(){return this;}});
  vm.runInContext(`
    profileEditor = {section:'contact',pending:false};
    readEditorData = () => ({phone:'41999999999',age:'18'});
    renderProfileSummary = () => calls.push(['summary']);
    loadDashboard = () => calls.push(['dashboard']);
    closeModal = selector => calls.push(['close',selector]);
    api = async (url,options) => {calls.push(['api',url,options]);return {profile:{phone:'41999999999'},completion:50,message:'saved'};};
  `,context);
  await context.saveProfile({preventDefault(){}});
  assert.equal(calls.find(x=>x[0]==='api')[1],'/api/profile/contact');
  assert.equal(calls.find(x=>x[0]==='api')[2].method,'PATCH');
  assert.equal(vm.runInContext('state.me.profile.phone',context),'41999999999');
  assert.ok(calls.some(x=>x[0]==='close'));
  assert.ok(!calls.some(x=>x[0]==='navigate'));

  vm.runInContext(`
    profileEditor = {section:'contact',pending:false,baseline:'original'};
    closeAllOptionLists = () => {};
    window.confirm = () => false;
  `,context);
  calls.length=0;
  context.requestCloseProfile();
  assert.ok(!calls.some(x=>x[0]==='close'));
  vm.runInContext('window.confirm = () => true;',context);
  context.requestCloseProfile();
  assert.ok(calls.some(x=>x[0]==='close'));
  context.document.querySelector=()=>({elements:{skill_name:{value:'Ainda não adicionei'}}});
  vm.runInContext("profileEditor={baseline:JSON.stringify(readEditorData())};",context);
  assert.equal(context.profileHasChanges(),true);
  console.log('Frontend: autenticação, currículo estruturado, salvamento independente, cancelamento e HTML seguros verificados.');
})();
