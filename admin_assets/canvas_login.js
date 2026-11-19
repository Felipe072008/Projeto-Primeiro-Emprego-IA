(async () => {
'use strict';
const $ = selector => document.querySelector(selector);
const frame = $('#frame'), stage = $('.stage'), status = $('#status');
const params = new URLSearchParams(location.search);
const device = params.get('device') === 'mobile' ? 'mobile' : 'desktop';
const mobile = device === 'mobile';
const kinds = {text:'Texto',card:'Card',button:'Botão com link',notice:'Aviso',faq:'Perguntas frequentes',shape:'Forma',image:'Ilustração'};
const selected = new Set(), past = [], future = [];
const clone = structuredClone;
const clamp = (v,min,max) => Math.min(max,Math.max(min,Math.round(v)));
let content,revision,page,key,width,spec,baseline,desktopBaseline,layout,scene,doc,sheet,drag,clipboard;
let globalKeys,fonts,refreshStyle,themeSerial=0;
let dirty=false,saving,timer,preview=false,publicValue,themeLink,themeURL,currentStyle,marquee;
const active = () => layout || baseline;
const name = id => spec[id]?.[0] || active()[id]?.text || kinds[active()[id]?.kind];
const kind = id => spec[id]?.[2] || active()[id]?.kind;
const essential = id => ['action','functional','dynamic','system'].includes(kind(id));
const node = id => scene.board.querySelector('[data-layer="'+id+'"]') || scene.sources.get(id)?.node;
const element = (tag,text) => {const n=document.createElement(tag);if(text!=null)n.textContent=text;return n};
function button(parent,text,fn,title=text) {
  const b=element('button',text);b.title=title;b.onclick=fn;parent.append(b);return b;
}
async function api(path,data) {
  const r=await fetch('/admin-api/site/'+path,{method:data?'POST':'GET',headers:{'Content-Type':'application/json','X-Requested-With':'FirstJob','X-CSRF-Token':$('meta[name=csrf-token]').content},body:data?JSON.stringify(data):undefined});
  const result=await r.json();
  if(!r.ok)throw Error(result.error || 'Não foi possível concluir. Recarregue o editor.');
  return result;
}
function report(err){status.textContent=err.message}
function mark(){
  content.theme[key]=layout;
  dirty=true;status.textContent='Alterações pendentes';
  clearTimeout(timer);timer=setTimeout(()=>save().catch(report),600);
}
async function save(){
  if(saving)await saving;
  if(!dirty)return;
  dirty=false;
  saving=api('draft',{revision,content:clone(content)}).then(r=>{
    revision=r.revision;
    status.textContent='Rascunho salvo às '+new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})+' · '+(JSON.stringify(content)===JSON.stringify(publicValue)?'Publicado':'Não publicado');
  }).catch(e=>{dirty=true;throw e}).finally(()=>{saving=null});
  await saving;
  if(dirty)await save();
}
function snapshot(){return clone(content.theme)}
function setBackground(bg){if(bg)(content.theme.board_backgrounds??={})[key]=bg;else if(content.theme.board_backgrounds)delete content.theme.board_backgrounds[key]}
function remember(){past.push(snapshot());if(past.length>50)past.shift();future.length=0}
function change(fn){
  if(preview)return;
  remember();layout=clone(active());fn();mark();draw();
}
function step(from,to){
  if(preview||!from.length)return;
  to.push(snapshot());
  const previous=from.pop(),updateTheme=globalKeys.some(k=>content.theme[k]!==previous[k]);
  content.theme=previous;layout=clone(previous[key] || null);
  if(updateTheme)refreshStyle().catch(report);
  mark();draw();
}
function bounded(item,prop,val,id){
  const limits={x:[0,width-item.w],y:[0,20000],w:[16,width-item.x],h:[kind(id)==='dynamic'?80:16,12000],z:[0,99]};
  if(Number.isFinite(val))item[prop]=clamp(val,...limits[prop]);
}
function pick(id,multiple=false){
  if(!multiple)selected.clear();
  if(multiple&&selected.has(id))selected.delete(id);else selected.add(id);
  paint();inspector();
}
function field(parent,label,value,fn,type='text',limits){
  const wrap=element('label',label);const input=element('input');
  input.type=type;input.value=value;
  if(limits){input.min=limits[0];input.max=limits[1]}
  input.onchange=()=>{if(input.reportValidity())fn(type==='number'?Number(input.value):input.value)};
  wrap.append(input);parent.append(wrap);return input;
}
function add(kindName,copy){
  if(Object.values(active()).filter(a=>a.kind).length>=30){report(Error('Esta composição já tem 30 elementos adicionados.'));return}
  const id='item_'+crypto.randomUUID().replaceAll('-','');
  const a=copy?clone(copy):{kind:kindName,x:16,y:16,w:Math.min(width-32,240),h:kindName==='shape'?96:56,z:4,visible:true,locked:false,
    style:{},text:kinds[kindName],url:kindName==='button'?'/#profile':'',body:kindName==='faq'?'Resposta':''};
  if(copy){delete a.label;delete a.removed;a.x=clamp(a.x+12,0,width-a.w);a.y=Math.min(20000,a.y+12)}
  if(!copy&&['shape','card'].includes(kindName))Object.assign(a.style,{color:'#dce6ff',opacity:.75,blur:12,border:1,radius:14});
  change(()=>{layout[id]=a;selected.clear();selected.add(id)});$('#layers').parentElement.open=true;
}
function copyOf(id){
  const a=clone(active()[id]);delete a.label;delete a.removed;
  if(a.kind)return a;
  const block=content.blocks.find(b=>'block_'+b.id===id);
  if(block){
    return {...a,kind:block.type,text:block.type==='button'?block.label:(block.body || block.title || 'Perguntas frequentes'),
      url:block.type==='button'?block.url:'',body:'',heading:block.type==='button'?'':block.title,
      ...(block.type==='faq'?{items:clone(block.items)}:{})};
  }
  const type=kind(id)==='image'?'image':kind(id)==='card'?'card':'text';
  return {...a,kind:type,text:node(id).alt||node(id).textContent.trim()||name(id),url:'',body:''};
}
function duplicate(){
  const id=[...selected][0];if(!id||active()[id].locked||essential(id))return;
  const copy=copyOf(id);add(copy.kind,copy);
}
function remove(){
  change(()=>{for(const id of selected){if(layout[id].locked||essential(id))continue;if(spec[id]){layout[id].visible=false;layout[id].removed=true}else delete layout[id]}selected.clear()});
}
function reorder(delta){
  change(()=>{for(const id of selected){const a=layout[id];if(!a.locked)a.z=clamp(a.z+delta,0,99)}});
}
function inspector(){
  const panel=$('#props'),list=$('#layers');panel.replaceChildren();list.replaceChildren();
  for(const id of Object.keys(active()).sort((a,b)=>active()[b].z-active()[a].z)){
    const a=active()[id];if(a.removed)continue;
    const row=element('div');row.className='layer-row';list.append(row);
    const b=button(row,name(id)+(a.locked?' · travada':'')+(!a.visible?' · oculta':''),e=>pick(id,e.shiftKey));
    b.setAttribute('aria-pressed',String(selected.has(id)));
    const options=element('details');options.className='layer-options';
    const menu=element('summary','⋯');menu.title='Opções de '+name(id);menu.setAttribute('aria-label',menu.title);options.append(menu);row.append(options);
    const actions=element('div');options.append(actions);
    button(actions,a.locked?'Destravar':'Travar',()=>change(()=>layout[id].locked=!a.locked));
    if(!a.locked){
      if(!essential(id))button(actions,a.visible?'Ocultar':'Mostrar',()=>change(()=>layout[id].visible=!a.visible));
      for(const [delta,label] of [[1,'Subir camada'],[-1,'Descer camada']])
        button(actions,label,()=>change(()=>bounded(layout[id],'z',layout[id].z+delta,id)));
    }
  }
  const chosen=[...selected].filter(id=>active()[id]);
  $('#undo').disabled=!past.length;$('#redo').disabled=!future.length;
  $('#generate').hidden=!mobile||!!layout;
  if(!chosen.length){
    panel.append(element('p','Clique em um elemento para editar.'));
    field(panel,'Fundo desta página',content.theme.board_backgrounds?.[key]||'#edf2ff',v=>change(()=>setBackground(v)),'color');
    const options=element('details');options.append(element('summary','Tema do site'));panel.append(options);
    const titles={primary:'Cor primária',secondary:'Cor secundária',background:'Fundo global',text:'Cor do texto',accent:'Destaque'};
    function theme(prop,v){remember();content.theme[prop]=v;mark();refreshStyle().catch(report)}
    for(const [prop,title] of Object.entries(titles))field(options,title,content.theme[prop],v=>theme(prop,v),'color');
    for(const [prop,title] of [['heading_font','Fonte dos títulos'],['body_font','Fonte do corpo']]){
      const label=element('label',title),select=element('select');
      for(const f of fonts)select.add(new Option(f,f));
      select.value=content.theme[prop];select.onchange=()=>theme(prop,select.value);label.append(select);options.append(label);
    }
    const link=element('a','Alterar logo ou consultar histórico');link.href='/admin/site?modo=classico';options.append(link);return;
  }
  if(chosen.length>1){
    for(const [axis,title] of [['x','Alinhar à esquerda'],['y','Alinhar ao topo']])
      button(panel,title,()=>change(()=>{const min=Math.min(...chosen.map(id=>layout[id][axis]));for(const id of chosen)if(!layout[id].locked)bounded(layout[id],axis,min,id)}));
    if(chosen.length>2)for(const [axis,size,title] of [['x','w','Distribuir na horizontal'],['y','h','Distribuir na vertical']]){
      button(panel,title,()=>change(()=>{
        const sorted=chosen.filter(id=>!layout[id].locked).sort((a,b)=>layout[a][axis]-layout[b][axis]);
        if(sorted.length<3)return;
        const first=layout[sorted[0]],last=layout[sorted.at(-1)];
        const gap=(last[axis]+last[size]-first[axis]-sorted.reduce((v,id)=>v+layout[id][size],0))/(sorted.length-1);
        let pos=first[axis];for(const id of sorted){bounded(layout[id],axis,pos,id);pos+=layout[id][size]+gap}
      }));
    }return;
  }
  const id=chosen[0],a=active()[id],type=kind(id);panel.append(element('strong',name(id)));
  button(panel,a.locked?'Destravar':'Travar',()=>change(()=>layout[id].locked=!a.locked));
  if(a.locked)return;
  if(!essential(id))button(panel,a.visible?'Ocultar':'Mostrar',()=>change(()=>layout[id].visible=!a.visible));
  if((a.kind&&!a.items)||(['text','image','action','functional'].includes(type)&&id!=='status')){
    field(panel,type==='image'?'Texto alternativo':'Texto',a.text??a.label??(type==='image'?node(id).alt:(type==='functional'?node(id).querySelector('button')||node(id):node(id)).textContent.trim()),v=>{
      if(v.trim()&&v.length<=(a.kind==='text'||a.kind==='notice'?3000:500))change(()=>layout[id][a.kind?'text':'label']=v);
    });
  }
  if(type==='block')button(panel,'Editar conteúdo',()=>{
    const copy=copyOf(id),newId='item_'+crypto.randomUUID().replaceAll('-','');
    change(()=>{layout[id].visible=false;layout[id].removed=true;layout[newId]=copy;selected.clear();selected.add(newId)});
  });
  if(a.heading!==undefined)field(panel,'Título do bloco',a.heading,v=>change(()=>layout[id].heading=v.slice(0,120)));
  if(a.items){
    a.items.forEach((pair,i)=>{
      field(panel,'Pergunta '+(i+1),pair.question,v=>{if(v.trim())change(()=>layout[id].items[i].question=v.slice(0,200))});
      field(panel,'Resposta '+(i+1),pair.answer,v=>{if(v.trim())change(()=>layout[id].items[i].answer=v.slice(0,2000))});
    });
    if(a.items.length<12)button(panel,'Adicionar pergunta',()=>change(()=>layout[id].items.push({question:'Pergunta',answer:'Resposta'})));
  }
  if(type==='faq'&&!a.items)field(panel,'Resposta',a.body,v=>change(()=>layout[id].body=v.slice(0,2000)));
  if(type==='button')field(panel,'Destino',a.url,v=>{
    if(!(/^https?:\/\//i.test(v)||/^\/(?:$|#(?:dashboard|profile|jobs|courses|resume|account)$|termos-de-uso$|politica-de-privacidade$|cookies$)/.test(v)))return report(Error('Use um link permitido.'));
    change(()=>layout[id].url=v);
  });
  if(['card','shape','notice','button','action','functional'].includes(type)){
    const presets=element('div');presets.className='presets';panel.append(presets);
    for(const [title,values] of Object.entries({Vidro:{color:'#dce6ff',opacity:.56,blur:18,border:1,radius:16},Sólido:{color:'#e8edff',opacity:1,blur:0,border:0,radius:12},Contorno:{color:'#ffffff',opacity:0,blur:0,border:2,radius:12}}))
      button(presets,title,()=>change(()=>Object.assign(layout[id].style,values)));
    field(panel,'Cor do fundo',(a.style.color||'#ffffff').slice(0,7),v=>style('color',v),'color');
    field(panel,'Opacidade (%)',Math.round((a.style.opacity??1)*100),v=>style('opacity',v/100),'number',[0,100]);
  }
  const details=element('details'),summary=element('summary','Mais opções');details.append(summary);panel.append(details);
  details.open=sessionStorage.getItem('editor-advanced')==='1';
  summary.onclick=()=>{sessionStorage.setItem('editor-advanced',details.open?'0':'1')};
  for(const [prop,title] of Object.entries({x:'Horizontal',y:'Vertical',w:'Largura',h:type==='text'?'Altura mínima':'Altura',z:'Camada'}))
    field(details,title,a[prop],v=>change(()=>bounded(layout[id],prop,v,id)),'number');
  function style(prop,v){change(()=>{layout[id].style[prop]=v;if(['color','opacity','blur','radius','borderOpacity','line'].includes(prop)){layout[id].style.color??='#ffffff';layout[id].style.border??=1}})}
  if(type!=='image'){
    field(details,'Cor do texto',(a.style.ink||'#111943').slice(0,7),v=>style('ink',v),'color');
    field(details,'Tamanho da fonte',a.style.font??16,v=>style('font',v),'number',[12,96]);
    const select=element('select');select.setAttribute('aria-label','Alinhamento');
    for(const [v,t] of [['left','À esquerda'],['center','Centralizado'],['right','À direita']])select.add(new Option(t,v));
    select.value=a.style.align||'left';select.onchange=()=>style('align',select.value);details.append(select);
  }
  if(['card','shape','notice','button','action','functional'].includes(type)){
    for(const [prop,title,max] of [['blur','Desfoque',40],['radius','Cantos',48],['border','Espessura da borda',12],['borderOpacity','Opacidade da borda',100],['shadow','Sombra',3]])
      field(details,title,prop==='borderOpacity'?Math.round((a.style[prop]??.45)*100):a.style[prop]??0,v=>style(prop,prop==='borderOpacity'?v/100:v),'number',[0,max]);
    field(details,'Cor da borda',(a.style.line||'#ffffff').slice(0,7),v=>style('line',v),'color');
  }
}
function cssRule(selector,declarations){
  sheet.insertRule(selector+'{'+declarations+'}',sheet.cssRules.length);
}
function paint(){
  while(sheet.cssRules.length)sheet.deleteRule(0);
  for(const n of doc.querySelectorAll('.edit-decoration'))n.remove();
  if(layout){
    if(content.theme.board_backgrounds?.[key])cssRule('[data-layout-board]','background:'+content.theme.board_backgrounds[key]);
    for(const [id,a] of Object.entries(layout)){
      const sel='[data-layout-board]>[data-layer="'+id+'"]',s=a.style,u=v=>(100*v/width)+'cqw';
      const auto=!['image','dynamic','shape'].includes(kind(id))&&id!=='glass';
      const alpha=(color,p)=>color.slice(0,7)+Math.round(parseInt(color.slice(7)||'ff',16)*p).toString(16).padStart(2,'0');
      cssRule(sel,'margin:'+u(a.y)+' 0 0 '+u(a.x)+';width:'+u(a.w)+';min-height:'+u(a.h)+';z-index:'+a.z+';'+(auto?'':'height:'+u(a.h)+';')+
        (kind(id)==='dynamic'?'overflow:auto;min-height:80px;':'')+(!a.visible?'display:none!important;':'')+
        (s.color&&(kind(id)==='card'||kind(id)==='shape'||s.border!=null)?'background:'+alpha(s.color,s.opacity??1)+';border-radius:'+(s.radius??0)+'px;border:'+(s.border??1)+'px solid '+alpha(s.line||'#ffffff',s.borderOpacity??.45)+';backdrop-filter:blur('+(s.blur??0)+'px);':'')+
        (s.shadow!=null?'box-shadow:'+['none','0 2px 6px #10184222','0 6px 18px #10184233','0 12px 32px #10184244'][s.shadow]+';':''));
      const typography=(s.ink?'color:'+s.ink+';':'')+(s.font?'font-size:'+s.font+'px;':'')+(s.align?'text-align:'+s.align+';':'');
      if(typography)cssRule(sel+','+sel+' :is(h1,h2,p,a,summary,button)',typography);
    }
  }
  if(preview)return;
  for(const id of Object.keys(active())){
    const n=node(id);if(!n||active()[id].removed)continue;
    n.dataset.pick=id;n.title=name(id);
  }
  cssRule('[data-pick]:hover','outline:2px dashed #778aff;outline-offset:-2px;cursor:move');
  cssRule('[data-pick]','touch-action:none');
  cssRule('.protected-label','display:inline-block;background:#e4e9fb;color:#1d3063;border:1px solid #b5c3e4;padding:2px 6px;border-radius:4px;font:12px sans-serif;pointer-events:none');
  for(const target of doc.querySelectorAll('.auth-panel,.sidebar,.site-footer,.account-sections,#cookie-banner,#cookie-preferences')){
    const r=target.getBoundingClientRect();if(!r.width||!r.height)continue;
    const badge=decoration('span',r.left+3,Math.max(0,r.top-16));badge.classList.add('protected-label');badge.textContent='Área protegida';
  }
  for(const id of selected){
    const n=node(id),a=active()[id];if(!n||!a.visible)continue;
    cssRule('[data-pick="'+id+'"]','outline:3px solid #6077ff;outline-offset:-3px');
    const r=n.getBoundingClientRect();
    if(!a.locked)for(const [dir,x,y] of [['nw',0,0],['n',.5,0],['ne',1,0],['e',1,.5],['se',1,1],['s',.5,1],['sw',0,1],['w',0,.5]]){
      const h=decoration('i',r.left+x*r.width,r.top+y*r.height);
      h.dataset.handle=dir;h.dataset.target=id;h.title='Redimensionar';h.style.cssText+=';width:12px;height:12px;background:white;border:2px solid #4052ac;transform:translate(-50%,-50%);cursor:'+dir+'-resize';
    }
    if(selected.size===1&&!drag){
      const bar=decoration('div',clamp(r.left,2,Math.max(2,doc.documentElement.clientWidth-194)),Math.max(2,r.top-33));
      bar.classList.add('mini-tools');bar.style.cssText+=';background:white;color:#121b46;display:flex;border:1px solid #b5c1de;border-radius:6px';
      const tools=[['↑','Trazer para frente',()=>reorder(1)],['↓','Enviar para trás',()=>reorder(-1)],['◇',a.locked?'Destravar':'Travar',()=>change(()=>layout[id].locked=!a.locked)]];
      if(!essential(id)&&!a.locked){tools.unshift(['×','Excluir',remove]);tools.unshift(['＋','Duplicar',duplicate])}
      for(const [glyph,title,fn] of tools){const b=button(bar,glyph,fn,title);b.setAttribute('aria-label',title);b.style.cssText='padding:4px 7px;background:white;color:#192456;border:0';}
    }
  }
}
function decoration(tag,x,y){
  const n=doc.createElement(tag);n.className='edit-decoration';doc.body.append(n);
  Object.assign(n.style,{position:'absolute',left:x+'px',top:(y+doc.defaultView.scrollY)+'px',zIndex:'110',touchAction:'none'});
  return n;
}
function draw(){
  for(const id of selected)if(!active()[id])selected.delete(id);
  scene.apply(layout);paint();inspector();
}
function measure(){
  const area=(page==='login'?doc.querySelector('.auth-intro'):scene.host).getBoundingClientRect();
  const boxes=[...scene.sources.values()].map(s=>s.node.getBoundingClientRect()).filter(r=>r.height>0);
  const top=Math.min(...boxes.map(r=>r.top),area.bottom),unit=width/Math.max(1,area.width);
  const result={};
  for(const [id,[,,type]] of Object.entries(spec)){
    const r=scene.sources.get(id)?.node.getBoundingClientRect(),hidden=!r?.height;
    const x=hidden?0:clamp((r.left-area.left)*unit,0,width-16);
    result[id]={x,y:hidden?0:clamp((r.top-top)*unit,0,20000),w:hidden?Math.min(width,480):clamp(r.width*unit,16,width-x),
      h:hidden?180:clamp(r.height*unit,type==='dynamic'?80:16,12000),z:type==='card'?0:1,visible:!hidden||essential(id),locked:false,
      style:type==='card'?{color:'#ffffff',opacity:.24,blur:14,radius:24}:{}};
  }
  return result;
}
function rectPoint(e){return [e.clientX,e.clientY]}
function pointerDown(e){
  if(preview||e.target.closest('.mini-tools,[contenteditable]')||e.button!==0)return;
  const id=e.target.dataset.target||e.target.closest('[data-pick]')?.dataset.pick;
  if(!id){
    if(!e.shiftKey)selected.clear();draw();
    if(!e.target.closest('form,nav,header,footer,button,a')){marquee=rectPoint(e);doc.documentElement.setPointerCapture(e.pointerId)}
    return;
  }
  const handle=e.target.dataset.handle;
  if(!selected.has(id)||e.shiftKey)pick(id,e.shiftKey);
  if(!selected.has(id)||active()[id].locked)return;
  e.preventDefault();(handle?doc.documentElement:e.target).setPointerCapture(e.pointerId);
  drag={id,handle,x:e.clientX,y:e.clientY,start:clone(active()),moved:false};
}
function inline(id){
  if(active()[id].locked||!(kind(id)==='text'&&id!=='heading'||kind(id)==='action'||active()[id].kind==='button'))return;
  const n=node(id).querySelector('h1')||node(id);const original=Array.from(n.childNodes,n=>n.cloneNode(true));n.contentEditable='plaintext-only';n.focus();
  n.onkeydown=e=>{if(e.key==='Escape'){e.stopPropagation();n.onblur=null;n.onkeydown=null;n.removeAttribute('contenteditable');n.replaceChildren(...original);selected.clear();draw()}};
  n.onblur=()=>{const value=n.textContent.trim();n.removeAttribute('contenteditable');n.onblur=null;n.onkeydown=null;n.replaceChildren(...original);
    if(value&&value.length<=500)change(()=>layout[id][layout[id].kind?'text':'label']=value);else draw()};
}
function move(e){
  if(marquee){
    paint();const [x,y]=marquee;const box=decoration('div',Math.min(x,e.clientX),Math.min(y,e.clientY));
    Object.assign(box.style,{width:Math.abs(x-e.clientX)+'px',height:Math.abs(y-e.clientY)+'px',background:'#526eff22',border:'1px solid #526eff',pointerEvents:'none'});return;
  }
  if(!drag)return;
  const d=drag,orig=d.start[d.id],unit=width/Math.max(1,scene.board.isConnected?scene.board.clientWidth:(page==='login'?doc.querySelector('.auth-intro'):scene.host).clientWidth);
  let dx=Math.round((e.clientX-d.x)*unit),dy=Math.round((e.clientY-d.y)*unit);
  if(!dx&&!dy&&!d.moved)return;
  if(!d.moved){doc.documentElement.setPointerCapture(e.pointerId);remember();d.moved=true}
  layout=clone(d.start);const a=layout[d.id],guides=[];
    function snap(axis,size,delta,targets,offsets){
      for(const [id,b] of Object.entries(layout))if(!selected.has(id)&&b.visible)targets.push(b[axis],b[axis]+b[size]/2,b[axis]+b[size]);
      for(const offset of offsets){
        const near=targets.find(v=>Math.abs(orig[axis]+delta+offset-v)<5);
        if(near!==undefined){guides.push([axis,near]);return Math.round(near-orig[axis]-offset)}
      }return delta;
    }
  const dir=d.handle||'';
  const offsets=(size,low,high)=>!dir?[0,size/2,size]:dir.includes(low)?[0]:dir.includes(high)?[size]:[];
  dx=snap('x','w',dx,[0,16,width/2,width-16,width],offsets(orig.w,'w','e'));
  dy=snap('y','h',dy,[0,16],offsets(orig.h,'n','s'));
  if(d.handle){
    if(dir.includes('w')){a.x=clamp(orig.x+dx,0,orig.x+orig.w-16);a.w=orig.w+orig.x-a.x}
    if(dir.includes('e'))bounded(a,'w',orig.w+dx,d.id);
    if(dir.includes('n')){a.y=clamp(orig.y+dy,0,orig.y+orig.h-(kind(d.id)==='dynamic'?80:16));bounded(a,'h',orig.h+orig.y-a.y,d.id)}
    if(dir.includes('s'))bounded(a,'h',orig.h+dy,d.id);
    if(e.shiftKey){
      const sx=a.w/orig.w,sy=a.h/orig.h;
      const desired=Math.abs(sx-1)>Math.abs(sy-1)?sx:sy;
      const minH=kind(d.id)==='dynamic'?80:16;
      const maxW=dir.includes('w')?orig.x+orig.w:width-orig.x;
      const maxH=dir.includes('n')?Math.min(12000,orig.y+orig.h):12000;
      const factor=Math.max(16/orig.w,minH/orig.h,Math.min(desired,maxW/orig.w,maxH/orig.h));
      a.w=Math.round(orig.w*factor);a.h=Math.round(orig.h*factor);
      if(dir.includes('w'))a.x=orig.x+orig.w-a.w;
      if(dir.includes('n'))a.y=orig.y+orig.h-a.h;
    }
  }else{
    for(const id of selected)if(!layout[id].locked){
      bounded(layout[id],'x',d.start[id].x+dx,id);bounded(layout[id],'y',d.start[id].y+dy,id);
    }
  }
  if(!scene.board.isConnected)scene.apply(layout);
  paint();const r=scene.board.getBoundingClientRect();
  for(const [axis,v] of guides){
    const g=decoration('i',r.left+(axis==='x'?v*r.width/width:0),r.top+(axis==='y'?v*r.width/width:0));
    g.classList.add('canvas-guide');Object.assign(g.style,{width:axis==='x'?'2px':r.width+'px',height:axis==='y'?'2px':r.height+'px',background:'#ffbd36',pointerEvents:'none'});
  }
}
function finish(e){
  if(marquee){
    const [x,y]=marquee;marquee=null;
    for(const id of Object.keys(active())){
      const r=node(id)?.getBoundingClientRect();if(r?.height&&r.left<=Math.max(x,e.clientX)&&r.right>=Math.min(x,e.clientX)&&r.top<=Math.max(y,e.clientY)&&r.bottom>=Math.min(y,e.clientY))selected.add(id);
    }draw();return;
  }
  if(!drag)return;
  const moved=drag.moved;drag=null;if(moved){mark();draw()}
}
function keyboard(e){
  if(e.target.closest('input,select,textarea,[contenteditable]')||preview||$('#dialog').open)return;
  const ctrl=e.ctrlKey||e.metaKey,k=e.key.toLowerCase(),id=[...selected][0];
  if(ctrl&&['z','y','d','c','v'].includes(k)){
    e.preventDefault();
    if(k==='z'&&!e.shiftKey)step(past,future);else if(k==='y'||k==='z')step(future,past);
    else if(k==='d')duplicate();else if(k==='c'&&id&&!essential(id)){
      clipboard=copyOf(id);
    }else if(k==='v'&&clipboard)add(clipboard.kind,clipboard);
    return;
  }
  if(k==='escape'){selected.clear();draw();return}
  if(!selected.size)return;
  if(k==='delete'){e.preventDefault();remove();return}
  if(!e.key.startsWith('Arrow'))return;
  e.preventDefault();const horizontal=['ArrowLeft','ArrowRight'].includes(e.key);
  const prop=e.altKey?(horizontal?'w':'h'):(horizontal?'x':'y');
  const delta=(['ArrowLeft','ArrowUp'].includes(e.key)?-1:1)*(e.shiftKey?10:1);
  change(()=>{for(const id of selected)if(!layout[id].locked)bounded(layout[id],prop,layout[id][prop]+delta,id)});
}
function dialog(title){
  $('#dialog-title').textContent=title;const body=$('#dialog-body');body.replaceChildren();
  if(!$('#dialog').open)$('#dialog').showModal();return body;
}
function tour(i=0){
  const steps=['Escolha a página e o dispositivo na barra superior.','Clique no elemento ou encontre seu nome em Camadas.','Arraste para mover. Use as alças para redimensionar e Propriedades para ajustar.','Confira a prévia e publique quando estiver pronto. O rascunho é salvo automaticamente.'];
  const body=dialog('Conheça o editor · '+(i+1)+'/4');body.append(element('p',steps[i]));
  button(body,i===3?'Concluir':'Próximo',()=>i===3?$('#dialog').close():tour(i+1));
}
function fit(){
  const base=mobile?390:1280,scale=Math.min(1,$('.workspace').clientWidth/base*.96);
  frame.style.width=base+'px';frame.style.height=(mobile?844:850)+'px';frame.style.transform='scale('+scale+')';
  stage.style.width=(base*scale+2)+'px';stage.style.height=((mobile?844:850)*scale+2)+'px';
}
async function start(){
  const state=await api('state');content=state.draft;revision=state.revision;publicValue=state.published;
  globalKeys=[...state.catalog.colors,'heading_font','body_font'];fonts=state.catalog.fonts;
  page=Object.hasOwn(state.layers,params.get('page'))?params.get('page'):'login';
  key=page+'_'+device;spec=state.layers[page];width=page==='login'?560:1280;
  for(const [id,label] of Object.entries(state.catalog.pages))$('#page').add(new Option(label,id));
  $('#page').value=page;$('#device').value=device;
  const initial=clone(content);delete initial.theme[key];delete initial.theme[page+'_desktop'];if(initial.theme.board_backgrounds){delete initial.theme.board_backgrounds[key];delete initial.theme.board_backgrounds[page+'_desktop']}
  const response=await api('render',{content:initial,page});
  await new Promise(resolve=>{frame.onload=resolve;frame.srcdoc=response.html});doc=frame.contentDocument;
  themeLink=doc.querySelector('[href="/site-theme.css"]');
  async function setCSS(css){
    const old=themeURL;themeURL=URL.createObjectURL(new Blob([css],{type:'text/css'}));
    await new Promise(resolve=>{themeLink.onload=resolve;themeLink.href=themeURL});if(old)URL.revokeObjectURL(old);
  }
  refreshStyle=async()=>{
    const serial=++themeSerial;
    const draft=clone(content);delete draft.theme[key];if(draft.theme.board_backgrounds)delete draft.theme.board_backgrounds[key];
    const result=await api('render',{content:draft,page});if(serial!==themeSerial)return;
    currentStyle=result.css;await setCSS(currentStyle);
  };
  currentStyle=response.css;await setCSS(currentStyle);await doc.fonts.ready;
  scene=SiteLayout.makeBoard(doc,page,spec);
  frame.style.width='1280px';desktopBaseline=measure();fit();if(mobile)width=390;
  baseline=measure();layout=content.theme[key]?{...clone(baseline),...clone(content.theme[key])}:null;
  sheet=new doc.defaultView.CSSStyleSheet();doc.adoptedStyleSheets=[sheet];

  doc.addEventListener('click',e=>{if(e.target.closest('button,a')||(!preview&&e.target.closest('summary')))e.preventDefault()});
  doc.addEventListener('submit',e=>e.preventDefault());
  doc.addEventListener('pointerdown',pointerDown);doc.addEventListener('pointermove',move);doc.addEventListener('pointerup',finish);doc.addEventListener('pointercancel',finish);
  doc.addEventListener('dragstart',e=>e.preventDefault());doc.addEventListener('keydown',keyboard);document.addEventListener('keydown',keyboard);
  doc.addEventListener('dblclick',e=>{const id=e.target.closest('[data-pick]')?.dataset.pick;if(id&&!e.target.isContentEditable&&!preview)inline(id)});
  new ResizeObserver(fit).observe($('.workspace'));
  $('#undo').onclick=()=>step(past,future);$('#redo').onclick=()=>step(future,past);
  if(page==='login'){const b=button($('#add'),'Card de vidro',()=>change(()=>{layout.glass.visible=true;delete layout.glass.removed;selected.clear();selected.add('glass');$('#layers').parentElement.open=true}));b.id='glass'}
  for(const [kindName,title] of Object.entries(kinds))button($('#add'),title,()=>add(kindName));
  $('#generate').onclick=()=>change(()=>{
    const desktop=content.theme[page+'_desktop']||desktopBaseline;let y=0;layout={};
    for(const [id,v] of Object.entries(desktop).sort((a,b)=>a[1].y-b[1].y||a[1].x-b[1].x)){
      const a=clone(v);a.x=0;a.y=y;a.w=width;a.h=clamp(a.h*Math.min(1,width/v.w),spec[id]?.[2]==='dynamic'?80:16,12000);
      if(a.visible)y+=a.h+16;layout[id]=a;
    }
  });
  $('#reset').onclick=()=>change(()=>{layout=null;setBackground(null);selected.clear()});
  $('#preview').onclick=async()=>{
    try{
      if(!preview){const rendered=await api('render',{content,page});await setCSS(rendered.css)}
      else await setCSS(currentStyle);
      preview=!preview;$('#preview').textContent=preview?'Voltar à edição':'Pré-visualizar';
      $('main').classList.toggle('preview',preview);
      draw();if(preview)while(sheet.cssRules.length)sheet.deleteRule(0);
    }catch(e){report(e)}
  };
  $('#collapse').onclick=()=>{const hide=!$('#library-body').hidden;$('#library-body').hidden=hide;$('#collapse').setAttribute('aria-expanded',String(!hide));$('main').classList.toggle('collapsed',hide)};
  $('#help').onclick=()=>{const body=dialog('Atalhos do editor');body.append(element('p','Setas movem 1 px. Shift + seta move 10 px. Alt + seta redimensiona. Shift mantém proporção ao redimensionar. Shift + clique ou arraste no fundo para selecionar vários. Ctrl+C/V/D copia, cola ou duplica. Delete exclui. Ctrl+Z/Y desfaz ou refaz. Esc desmarca.'));button(body,'Tour rápido',()=>tour())};
  async function switchPage(){
    try{await save();location.assign('?'+new URLSearchParams({page:$('#page').value,device:$('#device').value}))}catch(e){report(e);$('#page').value=page;$('#device').value=device}
  }
  $('#page').onchange=switchPage;$('#device').onchange=switchPage;
  window.addEventListener('beforeunload',e=>{if(dirty||saving){e.preventDefault();e.returnValue=''}});
  $('#publish').onclick=async()=>{
    try{
      await save();const s=await api('state');if(s.revision!==revision)throw Error('O rascunho mudou em outra aba. Recarregue.');
      const issues=s.issues;
      if(scene.board.isConnected){
        const boundary=scene.board.getBoundingClientRect();
        const protectedAreas=[...doc.querySelectorAll('.auth-panel,.sidebar,.site-footer,.account-sections')]
          .map(n=>n.getBoundingClientRect()).filter(r=>r.width&&r.height);
        for(const n of scene.board.children){
          const r=n.getBoundingClientRect();if(!r.width||!r.height)continue;
          const outside=r.left<boundary.left-1||r.right>boundary.right+1||r.bottom>boundary.bottom+1;
          const covered=protectedAreas.some(p=>r.left<p.right-1&&r.right>p.left+1&&r.top<p.bottom-1&&r.bottom>p.top+1);
          if(outside||covered)issues.push({critical:true,message:name(n.dataset.layer)+(outside?' — fora da tela.':' — sobre uma área protegida.')});
        }
      }
      if(issues.length||s.contrast<4.5){
        const body=dialog('Problemas encontrados');
        for(const issue of issues)body.append(element('p',issue.message));
        if(s.contrast<4.5)body.append(element('p','Tema do site — contraste abaixo de 4,5:1.'));
        if(issues.some(i=>i.fix)||s.contrast<4.5)button(body,'Corrigir automaticamente',async()=>{
          remember();
          if(s.contrast<4.5)content.theme.text=s.contrast_fix;
          for(const issue of issues.filter(i=>i.fix)){const a=content.theme[issue.layout][issue.layer];if(issue.fix==='font')a.style.font=14;else a.style.ink=issue.suggestion}
          layout=content.theme[key]||null;mark();draw();refreshStyle().catch(report);$('#dialog').close();
        });
        if(!issues.some(i=>i.critical))button(body,'Publicar com aviso',()=>publish(true).catch(report));
      }else if(confirm('Publicar o rascunho atual?'))await publish(false);
    }catch(e){report(e);dialog('Problemas encontrados').append(element('p',e.message))}
  };
  async function publish(warnings){await api('publish',{revision,confirm:true,confirm_low_contrast:warnings});publicValue=clone(content);$('#dialog').close();status.textContent='Publicado'}
  draw();status.textContent=state.changes.length?(state.saved_at?'Rascunho salvo às '+new Date(state.saved_at).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}):'Rascunho')+' · Não publicado':'Publicado';
  if(!localStorage.getItem('site-editor-tour-v2')){localStorage.setItem('site-editor-tour-v2','1');tour()}
}
try{await start()}catch(error){report(error)}
})();
