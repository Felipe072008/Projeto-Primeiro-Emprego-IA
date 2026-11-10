// Dados sintéticos ficam somente nos testes; nunca são publicados como ofertas.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.argv[2] || path.resolve(__dirname, '..');
const nodes = new Map();
const node = selector => {
  if (!nodes.has(selector)) nodes.set(selector, {innerHTML:'', textContent:'', data:{all:'1'}, setAttribute(name,value){this[name]=value;}, classList:{remove(){}}, scrollTop:0});
  return nodes.get(selector);
};
const context = vm.createContext({URL, URLSearchParams, Intl, Date,
  FormData: class {constructor(form){this.rows=Object.entries(form.data);} [Symbol.iterator](){return this.rows[Symbol.iterator]();}},
  document:{querySelector:node, querySelectorAll:()=>[]}, sessionStorage:{setItem(){}},
  window:{}, console,
});
vm.runInContext(fs.readFileSync(path.join(root,'static/interface_site.js'),'utf8').replace(/boot\(\);\s*$/, ''),context);
const course = {id:'fixture',title:'Curso sintético <exemplo>',institution:'Instituição de teste',source:'Fonte sintética',original_url:'https://example.org/curso/1',description:'Apenas teste',match:'explore',enrollment_status:'unknown',access_status:'free_full',certificate_status:'paid',checked_on:'2026-10-08',last_verified_at:null,requirements:[]};
const source = {name:'Fonte sintética',classification:'pending',sync_status:'error',last_attempt_at:'2026-11-09T22:00:00-03:00',last_success_at:null,message:'Falha <teste>'};
const envelope = {courses:[course],total:1,catalog_status:'available',data_status:'fresh',result_status:'results',sources:[source],external_links:[{name:'Fonte sintética',url:'https://example.org/',classification:'pending',note:'Link externo'}]};
context.response = envelope;
vm.runInContext('api = async () => response; openModal = () => {};',context);
(async()=>{
  await context.loadCatalog('courses');
  let html=node('#courses-list').innerHTML;
  assert.ok(html.includes('Conteúdo completo gratuito') && html.includes('Certificado pago'));
  assert.ok(html.includes('Inscrição não confirmada') && !html.includes('Com certificado'));
  assert.ok(html.includes('Consulta manual em 08/10/2026') && !html.includes('09/11/2026'));
  assert.ok(html.includes('&lt;exemplo&gt;') && !html.includes('<exemplo>'));
  assert.ok(node('#courses-status').textContent.includes('falha'));
  assert.ok(node('#courses-sources').innerHTML.includes('Nenhuma registrada'));
  assert.ok(node('#courses-sources').innerHTML.includes(context.catalogDate(source.last_attempt_at)));
  assert.ok(node('#courses-external').innerHTML.includes('Consulte também'));
  assert.equal(node('#courses-list')['aria-busy'],'false');
  context.showCatalogDetail('courses',0);
  assert.ok(node('#resume-preview').innerHTML.includes('Certificado pago'));
  for(const url of ['javascript:alert(1)','data:text/html,abc','http://example.org','https://user:pass@example.org']) assert.ok(!context.catalogLink(url,'Teste').includes('<a '));
  assert.ok(context.catalogLink('https://example.org/?a=1&b=2','Fonte').includes('noopener noreferrer'));
  for(const access of ['preview','trial','financial_aid','paid','unknown']) {
    assert.ok(!context.courseConditions({...course,access_status:access})[1][1].includes('Conteúdo completo gratuito'));
  }
  assert.equal(context.courseConditions({...course,certificate_status:'free'})[2][1],'Certificado gratuito');
  assert.equal(context.courseConditions({...course,certificate_status:'unknown'})[2][1],'Custo do certificado não informado');
  context.response={...envelope,courses:[],total:0,result_status:'no_matches'};
  await context.loadCatalog('courses');
  assert.ok(node('#courses-list').innerHTML.includes('Nenhum resultado corresponde'));
  context.response={...context.response,data_status:'stale',result_status:'no_data',stale_count:3};
  await context.loadCatalog('courses');
  assert.ok(node('#courses-list').innerHTML.includes('desatualizados'));
  context.response={...context.response,data_status:'unavailable',catalog_status:'unavailable'};
  await context.loadCatalog('courses');
  assert.ok(node('#courses-list').innerHTML.includes('O catálogo está sem cursos com revisão válida'));
  vm.runInContext('api = async () => {throw new Error("Falha de rede")};',context);
  await context.loadCatalog('courses');
  assert.ok(node('#courses-list').innerHTML.includes('role="alert"'));
  assert.equal(node('#courses-external').innerHTML,'');
  context.pending=[];
  vm.runInContext('api = () => new Promise(resolve => pending.push(resolve));',context);
  const first=context.loadCatalog('courses'), second=context.loadCatalog('courses');
  context.pending[1]({...envelope,courses:[{...course,title:'Busca mais recente'}]});
  await second;
  context.pending[0](envelope);
  await first;
  assert.ok(node('#courses-list').innerHTML.includes('Busca mais recente'));
  const jobsFilters = new URLSearchParams('all=0');
  assert.ok(context.catalogEmptyMessage({result_status:'no_matches',catalog_status:'available',data_status:'fresh'},'jobs',jobsFilters).startsWith('Nenhuma vaga corresponde'));
  assert.ok(context.catalogEmptyMessage({result_status:'no_data',catalog_status:'unavailable',data_status:'stale'},'jobs',jobsFilters).startsWith('O catálogo está sem vagas verificadas'));
  const fields = {all:{value:'1'}, q:{value:''}, type:{value:''}, free:{type:'checkbox',checked:false}};
  node('#courses-filters').elements = {namedItem:name=>fields[name]};
  context.sessionStorage.getItem=()=> 'all=1&q=Excel&free=1&type=livre';
  context.restoreCatalogFilters('courses');
  assert.equal(fields.all.value,'0');
  assert.equal(fields.q.value,'Excel');
  assert.equal(fields.free.checked,true);
  node('#jobs-filters').elements = {namedItem:()=>({value:'1'})};
  fields.all.value='1';
  context.resetCatalogAreaFilters();
  assert.equal(fields.all.value,'0');
  console.log('Catálogo frontend: condições, datas, estados, links seguros, erro e concorrência aprovados.');
})().catch(error=>{console.error(error);process.exitCode=1;});
