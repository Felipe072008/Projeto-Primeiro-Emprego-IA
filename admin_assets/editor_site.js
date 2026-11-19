/* O editor trabalha só com o catálogo permitido e uma prévia sem scripts/sessão de usuário. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s), frame = $('#editor-frame'), status = $('#editor-status');
  const csrf = $('meta[name=csrf-token]').content;
  let content, catalog, revision, saved, previewOnly=false, sequence=0, busy=false, cssURL;
  const past=[], future=[];
  const clone = value => structuredClone(value);
  const equal = (a,b) => JSON.stringify(a)===JSON.stringify(b);
  const dirty = () => content && !equal(content,saved);
  function el(tag,text,attrs={}) {
    const node=document.createElement(tag);
    if (text!=null) node.textContent=text;
    for (const [key,value] of Object.entries(attrs)) node.setAttribute(key,value);
    return node;
  }
  function button(label,fn,attrs={}) {
    const node=el('button',label,{type:'button',class:'button',...attrs});
    node.addEventListener('click',()=>run(fn)); return node;
  }
  async function run(fn) {
    if (busy) return;
    busy=true;
    document.querySelectorAll('.editor-toolbar button,.editor-toolbar select').forEach(b=>{b.disabled=true;});
    document.querySelectorAll('.editor-inspector,.editor-canvas').forEach(node=>{node.inert=true;});
    try { await fn(); } catch(error) { status.textContent=error.message; $('#editor-dialog-error').textContent=error.message; }
    finally { busy=false; document.querySelectorAll('.editor-toolbar button,.editor-toolbar select').forEach(b=>{b.disabled=false;}); document.querySelectorAll('.editor-inspector,.editor-canvas').forEach(node=>{node.inert=false;}); }
  }
  async function api(path,data) {
    const response=await fetch('/admin-api/site/'+path,{method:data===undefined?'GET':'POST',credentials:'same-origin',
      headers:{'X-Requested-With':'FirstJob','X-CSRF-Token':csrf,...(data instanceof FormData?{}:{'Content-Type':'application/json'})},
      body:data===undefined?undefined:data instanceof FormData?data:JSON.stringify(data)});
    const result=await response.json().catch(()=>({error:'Resposta inválida. Recarregue o editor.'}));
    if (!response.ok) throw new Error(response.status===401?'Sessão expirada. Volte ao painel e entre novamente.':result.error||'Não foi possível concluir a ação.');
    return result;
  }
  function change(fn) {
    past.push(clone(content)); if (past.length>50) past.shift(); future.length=0;
    fn(); status.textContent='Há alterações não salvas.'; drawInspector(); return render();
  }
  function input(label,value,max=120,large=false) {
    const wrapper=el('label',label), node=el(large?'textarea':'input',null,{maxlength:max});
    node.value=value; wrapper.append(node); return {wrapper,node};
  }
  function select(label,values,current,onChange) {
    const wrapper=el('label',label), node=el('select',null,{'aria-label':label});
    for (const [key,title] of Object.entries(values)) node.append(el('option',title,{value:key}));
    node.value=current; node.addEventListener('change',()=>run(()=>onChange(node.value))); wrapper.append(node); return wrapper;
  }
  function dialog(title,nodes) {
    $('#editor-dialog-title').textContent=title; $('#editor-dialog-error').textContent='';
    $('#editor-dialog-body').replaceChildren(...nodes); $('#editor-dialog').showModal();
  }
  function close() { $('#editor-dialog').close(); }
  $('#editor-dialog-close').addEventListener('click',close);

  async function render() {
    const serial=++sequence, data=await api('render',{content,page:$('#editor-page').value});
    if (serial!==sequence) return;
    if (cssURL) URL.revokeObjectURL(cssURL);
    cssURL=URL.createObjectURL(new Blob([data.css],{type:'text/css'}));
    await new Promise(resolve=>{
      frame.onload=()=>{
        const doc=frame.contentDocument, theme=doc.querySelector('link[href="/site-theme.css"]');
        if (theme) theme.href=cssURL;
        const sheet=doc.createElement('link'); sheet.rel='stylesheet'; sheet.href='/admin-assets/editor_site.css'; doc.head.append(sheet);
        doc.addEventListener('submit',e=>e.preventDefault());
        doc.addEventListener('click',event=>{
          event.preventDefault();
          const target=event.target.closest('[data-edit-key]');
          if (target && !previewOnly && !target.querySelector('textarea')) inlineText(target,doc);
        });
        doc.querySelectorAll('[data-edit-key]').forEach(node=>{
          node.tabIndex=previewOnly?-1:0;
          if (!previewOnly) { node.title='Selecionar para editar texto'; node.addEventListener('keydown',event=>{if (['Enter',' '].includes(event.key) && event.target===node) {event.preventDefault();inlineText(node,doc);}}); }
        });
        resolve();
      };
      frame.srcdoc=data.html;
    });
  }
  function inlineText(target,doc) {
    const key=target.dataset.editKey, meta=catalog.texts[key]; if (!meta) return;
    const area=doc.createElement('textarea'); area.value=content.texts[key]; area.maxLength=meta.limit;
    area.setAttribute('aria-label','Editar texto');
    const ok=doc.createElement('button'); ok.type='button'; ok.textContent='Confirmar texto';
    const cancel=doc.createElement('button'); cancel.type='button'; cancel.textContent='Cancelar';
    const restore=doc.createElement('button'); restore.type='button'; restore.textContent='Restaurar este texto';
    target.classList.add('editor-live-text'); target.replaceChildren(area,ok,cancel,restore);
    ok.addEventListener('click',e=>{e.stopPropagation();run(()=>change(()=>{content.texts[key]=area.value;}));});
    restore.addEventListener('click',e=>{e.stopPropagation();run(()=>change(()=>{content.texts[key]=meta.default;}));});
    cancel.addEventListener('click',e=>{e.stopPropagation();run(render);}); area.addEventListener('click',e=>e.stopPropagation()); area.focus();
  }
  function editText(key) {
    const field=input('Texto (até '+catalog.texts[key].limit+' caracteres)',content.texts[key],catalog.texts[key].limit,true);
    dialog('Editar texto',[field.wrapper,button('Confirmar texto',async()=>{await change(()=>{content.texts[key]=field.node.value;});close();}),
      button('Restaurar este texto',async()=>{await change(()=>{content.texts[key]=catalog.texts[key].default;});close();})]);
  }
  function move(items,index,delta) {
    const next=index+delta; if (next<0 || next>=items.length) return;
    [items[index],items[next]]=[items[next],items[index]];
  }
  function drawInspector() {
    const page=$('#editor-page').value;
    const labels={primary:'Primária',secondary:'Secundária',background:'Fundo',text:'Texto',accent:'Destaque'};
    const theme=$('#editor-theme'); theme.replaceChildren();
    for (const key of catalog.colors) {
      const field=input(labels[key],content.theme[key],7); field.node.type='color'; field.node.setAttribute('aria-label',labels[key]);
      field.node.addEventListener('change',()=>run(()=>change(()=>{content.theme[key]=field.node.value;}))); theme.append(field.wrapper);
    }
    const fonts=Object.fromEntries(catalog.fonts.map(v=>[v,v]));
    theme.append(select('Fonte dos títulos',fonts,content.theme.heading_font,value=>change(()=>{content.theme.heading_font=value;})),
      select('Fonte dos textos',fonts,content.theme.body_font,value=>change(()=>{content.theme.body_font=value;})));
    const sections=$('#editor-sections'); sections.replaceChildren();
    content.layout[page].forEach((item,index)=>{
      const meta=catalog.sections[page].find(v=>v.key===item.key), row=el('div',null,{class:'editor-row'});
      row.append(el('strong',meta.label+(meta.locked?' — travada':'')));
      if (!meta.locked) {
        row.draggable=true;
        row.addEventListener('dragstart',event=>event.dataTransfer.setData('text/plain',item.key));
        row.addEventListener('dragover',event=>event.preventDefault());
        row.addEventListener('drop',event=>{event.preventDefault(); const from=content.layout[page].findIndex(v=>v.key===event.dataTransfer.getData('text/plain'));
          if (from<0) return;
          const locked=catalog.sections[page].filter(v=>v.locked).map(v=>v.key);
          if (content.layout[page].slice(Math.min(from,index),Math.max(from,index)+1).some(v=>locked.includes(v.key))) return;
          run(()=>change(()=>{const [moved]=content.layout[page].splice(from,1);content.layout[page].splice(index,0,moved);}));
        });
        row.append(button(item.visible?'Ocultar':'Mostrar',()=>change(()=>{item.visible=!item.visible;})));
        for (const [delta,label] of [[-1,'Subir'],[1,'Descer']]) {
          const other=content.layout[page][index+delta], control=button(label,()=>change(()=>move(content.layout[page],index,delta)));
          control.disabled=!other || catalog.sections[page].find(v=>v.key===other.key).locked; row.append(control);
        }
      }
      sections.append(row);
    });
    const blockList=$('#editor-blocks'); blockList.replaceChildren();
    const blocks=content.blocks.filter(v=>v.slot===page);
    blocks.forEach((block,index)=>{
      const row=el('div',null,{class:'editor-row'}); row.append(el('strong',block.title||block.label||'Perguntas frequentes'));
      row.append(button('Editar',()=>editBlock(block)),button(block.visible?'Ocultar':'Mostrar',()=>change(()=>{block.visible=!block.visible;})),
        button('Duplicar',()=>change(()=>{if(content.blocks.length>=30) throw new Error('Limite de 30 blocos.');content.blocks.push({...clone(block),id:crypto.randomUUID()});})),
        button('Excluir',()=>change(()=>{content.blocks=content.blocks.filter(v=>v!==block);}))); 
      for (const [delta,label] of [[-1,'Subir'],[1,'Descer']]) {
        const other=blocks[index+delta], control=button(label,()=>change(()=>{
          const a=content.blocks.indexOf(block),b=content.blocks.indexOf(other);[content.blocks[a],content.blocks[b]]=[content.blocks[b],content.blocks[a]];
        }));control.disabled=!other;row.append(control);
      }
      blockList.append(row);
    });
    $('#editor-texts').replaceChildren(...Object.entries(catalog.texts).filter(([,meta])=>meta.page===page).map(([key])=>button(content.texts[key],()=>editText(key))));
  }
  function editBlock(block) {
    const fields=[], values={};
    function add(key,label,max,large=false) { const field=input(label,block[key],max,large); values[key]=field.node; fields.push(field.wrapper); }
    if (block.type==='button') { add('label','Rótulo do botão',120);add('url','Link http/https ou rota interna permitida',2048);fields.push(el('p','Rotas internas: '+catalog.internal_links.join(', '))); }
    else { add('title','Título',120); if(block.type!=='faq')add('body','Mensagem',3000,true); }
    if (block.type==='notice') {
      const wrapper=el('label','Estilo'), select=el('select'); select.append(el('option','Informativo',{value:'info'}),el('option','Atenção',{value:'warning'}));select.value=block.style;wrapper.append(select);fields.push(wrapper);values.style=select;
    }
    let questions=[];
    if (block.type==='faq') {
      const area=el('div');
      function question(item={question:'',answer:''}) {
        if (questions.length>=12) throw new Error('Use até 12 perguntas.');
        const q=input('Pergunta',item.question,200), a=input('Resposta',item.answer,2000,true), row=el('div');
        const pair={q:q.node,a:a.node};questions.push(pair);row.append(q.wrapper,a.wrapper,button('Remover pergunta',()=>{questions=questions.filter(v=>v!==pair);row.remove();}));area.append(row);
      }
      (block.items.length?block.items:[{question:'',answer:''}]).forEach(question); fields.push(area,button('Adicionar pergunta',()=>question()));
    }
    fields.push(button('Confirmar bloco',async()=>{
      const updated={...clone(block)}; for(const [key,node] of Object.entries(values))updated[key]=node.value;
      if(block.type==='faq')updated.items=questions.map(v=>({question:v.q.value,answer:v.a.value}));
      const candidate=clone(content); const index=candidate.blocks.findIndex(v=>v.id===block.id);candidate.blocks[index]=updated;
      await api('render',{content:candidate,page:$('#editor-page').value});
      await change(()=>{content=candidate;});close();
    })); dialog('Editar bloco',fields);
  }
  async function load() {
    const data=await api('state'); content=data.draft; saved=clone(content); catalog=data.catalog; revision=data.revision;
    if (!$('#editor-page').options.length) {
      for(const [key,label]of Object.entries(catalog.pages))$('#editor-page').append(el('option',label,{value:key}));
      $('#editor-page').value='login';
    }
    drawInspector(); await render();status.textContent='Rascunho carregado.';return data;
  }
  async function save() {const result=await api('draft',{content,revision});revision=result.revision;saved=clone(content);status.textContent=result.message;}
  $('#editor-save').addEventListener('click',()=>run(save));
  $('#editor-page').addEventListener('change',()=>run(async()=>{drawInspector();await render();}));
  $('#editor-width').addEventListener('change',()=>frame.classList.toggle('mobile',$('#editor-width').value==='mobile'));
  $('#editor-preview').addEventListener('click',()=>run(async()=>{previewOnly=!previewOnly;$('#editor-preview').setAttribute('aria-pressed',String(previewOnly));$('#editor-preview').textContent=previewOnly?'Voltar à edição':'Pré-visualizar';await render();}));
  for (const [id,from,to] of [['undo',past,future],['redo',future,past]])$('#editor-'+id).addEventListener('click',()=>run(async()=>{if(!from.length)return;to.push(clone(content));content=from.pop();drawInspector();await render();status.textContent=dirty()?'Há alterações não salvas.':'Rascunho salvo.';}));
  $('#editor-add-block').addEventListener('click',()=>run(async()=>{
    if(content.blocks.length>=30)throw new Error('O site permite até 30 blocos.');
    const type=$('#editor-block-type').value,block={id:crypto.randomUUID(),slot:$('#editor-page').value,type,visible:true,title:'Novo bloco',body:'Edite esta mensagem.',label:'Saiba mais',url:'/',style:'info',items:[]};
    await change(()=>content.blocks.push(block)); editBlock(block);
  }));
  $('#editor-original-logo').addEventListener('click',()=>run(()=>change(()=>{content.theme.logo=null;})));
  $('#editor-logo-form').addEventListener('submit',event=>{event.preventDefault();run(async()=>{const result=await api('logo',new FormData(event.target));await change(()=>{content.theme.logo=result.logo;});event.target.reset();});});
  $('#editor-publish').addEventListener('click',()=>run(async()=>{
    if(dirty())await save();const data=await api('state');
    const note=input('Nota da publicação (opcional)','',200),nodes=[el('p','Mudanças: '+(data.changes.join(', ')||'Nenhuma diferença em relação ao publicado.')),note.wrapper];
    let low;
    if(data.contrast<4.5){const label=el('label','Contraste texto/fundo: '+data.contrast+':1, abaixo de 4,5:1. Confirmo publicar mesmo assim.');low=el('input',null,{type:'checkbox'});label.prepend(low);nodes.push(label);}
    nodes.push(button('Confirmar publicação',async()=>{if(low&&!low.checked)throw new Error('Confirme o aviso de contraste.');await api('publish',{revision,confirm:true,confirm_low_contrast:!!low?.checked,note:note.node.value});close();await load();status.textContent='Versão publicada. O público já vê as alterações.';}));dialog('Publicar alterações no site?',nodes);
  }));
  $('#editor-history').addEventListener('click',()=>run(async()=>{
    const data=await api('state');
    async function restore(version){if(dirty()&&!window.confirm('Substituir as alterações locais pelo rascunho restaurado?'))return;await api('restore',{revision,version});close();past.length=future.length=0;await load();status.textContent='Versão restaurada como rascunho. Publique para aplicar.';}
    const nodes=[button('Restaurar original (padrão do código)',()=>restore('original')),
      button('Desfazer última publicação',async()=>{if(dirty()&&!window.confirm('Substituir também o rascunho local?'))return;await api('undo',{revision});close();past.length=future.length=0;await load();status.textContent='Última publicação desfeita.';})];
    for(const item of data.history)nodes.push(button(new Date(item.created_at).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'})+' — '+(item.note||'Sem nota')+' — Restaurar rascunho',()=>restore(item.id)));
    dialog('Histórico (últimas 30 versões)',nodes);
  }));
  window.addEventListener('beforeunload',event=>{if(dirty()){event.preventDefault();event.returnValue='';}});
  run(load);
})();
