"""Persistência, renderização segura e rotas do editor visual."""
import copy
import io
import json
import re
import secrets
import sqlite3
import time
import warnings
from html import escape
from html.parser import HTMLParser
from pathlib import Path

from flask import Response, abort, g, jsonify, render_template, request, send_file
from PIL import Image, UnidentifiedImageError

from canvas_login import LAYOUT_KEYS, layer_catalog, DEVICES, canvas_css, migrate_saved_layout, problems

from conteudo_editavel import (COLORS, PAGES, TEXTS, catalog, changes, contrast, defaults,
                              digest, plain, validate)

CACHE = {}
PARTS = ('theme','texts','layout','blocks')


def init_schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS site_editor_meta (id INTEGER PRIMARY KEY CHECK(id=1), saved_at TEXT NOT NULL)')
    for part in PARTS:
        db.execute(f'CREATE TABLE IF NOT EXISTS site_{part} (state TEXT PRIMARY KEY CHECK(state IN (\'draft\',\'published\')), payload TEXT NOT NULL)')
    db.execute('''CREATE TABLE IF NOT EXISTS site_versions (id INTEGER PRIMARY KEY,
        created_at TEXT NOT NULL, note TEXT NOT NULL, snapshot TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'published')''')


def read(db, state, strict=False):
    result = defaults()
    found = 0
    try:
        for part in PARTS:
            row = db.execute(f'SELECT payload FROM site_{part} WHERE state=?',(state,)).fetchone()
            if row:
                result[part] = json.loads(row[0]); found += 1
        if found not in (0,4):
            raise ValueError('Registro incompleto.')
        migrate_saved_layout(result)
        try:
            return validate(result)
        except (ValueError, TypeError):
            if state != 'published' or not isinstance(result['theme'],dict):
                raise
            # Um quadro inválido não descarta o conteúdo nem os outros dispositivos.
            theme = result['theme']
            layouts = {key:theme.pop(key) for key in LAYOUT_KEYS & theme.keys()}
            backgrounds = theme.pop('board_backgrounds',{})
            valid = validate(result)
            for key, layout in layouts.items():
                candidate = copy.deepcopy(valid)
                candidate['theme'][key] = layout
                if isinstance(backgrounds,dict) and key in backgrounds:
                    candidate['theme'].setdefault('board_backgrounds',{})[key] = backgrounds[key]
                try:
                    valid = validate(candidate)
                except (ValueError,TypeError):
                    continue
            return valid
    except (ValueError, TypeError, sqlite3.DatabaseError):
        if strict:
            raise ValueError('Rascunho inválido. Restaure uma versão antes de publicar.')
        return defaults()


def write(db, state, value):
    for part in PARTS:
        db.execute(f'INSERT INTO site_{part} VALUES (?,?) ON CONFLICT(state) DO UPDATE SET payload=excluded.payload',
                   (state,json.dumps(value[part],ensure_ascii=False)))


def published(site):
    path = Path(site.DATABASE).resolve()
    try:
        # Também detecta publicações feitas por outro worker do WSGI.
        stamp = (path.stat().st_mtime_ns, path.stat().st_size,
                 Path(str(path)+'-wal').stat().st_mtime_ns if Path(str(path)+'-wal').exists() else 0)
        cached = CACHE.get(str(path))
        if not cached or cached[0]!=stamp:
            with site.db_connection() as db:
                value = read(db,'published')
            CACHE.clear(); CACHE[str(path)] = (stamp,value)
        value=copy.deepcopy(CACHE[str(path)][1])
        logo=value['theme']['logo']
        if logo and not (Path(site.UPLOAD_DIR)/'site-logos'/logo['name']).is_file():
            value['theme']['logo']=None
        return value
    except OSError:
        return defaults()


def css(value):
    theme = value['theme']; original = defaults()['theme']
    variables = {'primary':'--blue','secondary':'--blue-deep','background':'--cream',
                 'text':'--ink','accent':'--orange'}
    rules = [variables[k]+':'+theme[k] for k in COLORS if theme[k].lower()!=original[k]]
    result = ':root {'+';'.join(rules)+'}' if rules else ''
    if theme['background'].lower()!=original['background']:
        footer_color = '#000000' if contrast(dict(theme, text='#000000')) >= 4.5 else '#ffffff'
        result += f'.site-footer{{--footer-color:{footer_color}}}'
        result += 'body,body:has(.auth-view:not(.hidden)){background:var(--cream)}.page-wrap,.auth-card{background:var(--cream)}.intro-copy h1{color:var(--ink)}.sidebar{background:var(--blue-deep)}'
    if theme['text'].lower()!=original['text']:
        result += '.auth-card,.page-wrap{color:var(--ink)}'
    if theme['primary'].lower()!=original['primary']:
        result += '.button.button--primary,#login-form .button.button--primary{background:var(--blue);color:white}.button.button--primary:hover,#login-form .button.button--primary:hover{background:var(--blue);filter:brightness(.9)}'
    if theme['secondary'].lower()!=original['secondary']:
        result += '.button.button--dark,.sidebar{background:var(--blue-deep);color:white}.button.button--dark:hover{background:var(--blue-deep);filter:brightness(.9)}'
    if theme['body_font']!=original['body_font']:
        result += 'body{font-family:"'+theme['body_font']+'",sans-serif}'
    if theme['heading_font']!=original['heading_font']:
        result += 'body :is(h1,h2,h3){font-family:"'+theme['heading_font']+'",sans-serif!important}'
    for page in PAGES:
        for device in DEVICES:
            key = page+'_'+device
            result += canvas_css(theme.get(key),page,device,value['blocks'])
            bg = theme.get('board_backgrounds',{}).get(key)
            if bg and theme.get(key):
                media = '(min-width:900px)' if device=='desktop' else '(width < 900px)'
                result += f'@media {media}{{[data-layout-board="{page}"]{{background:{bg}}}}}'
    return result


class Node:
    def __init__(self, tag='', attrs=(), raw=''):
        self.tag, self.attrs, self.raw, self.children = tag,dict(attrs),raw,[]


class Document(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.root = Node(); self.stack = [self.root]; self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = Node(tag,attrs); self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if len(self.stack)>1 and self.stack[-1].tag==tag:
            self.stack.pop()

    def handle_data(self, text):
        self.stack[-1].children.append(Node(raw=text))

    def handle_entityref(self, name):
        self.handle_data('&'+name+';')

    def handle_charref(self, name):
        self.handle_data('&#'+name+';')

    def handle_decl(self, decl):
        self.handle_data('<!'+decl+'>')

    def handle_comment(self, text):
        self.handle_data('<!--'+text+'-->')

    def render(self, node=None):
        node = node or self.root
        content = ''.join(self.render(child) for child in node.children)
        if not node.tag:
            return node.raw+content
        attrs = ''.join(' '+key+('="'+escape(str(value),quote=True)+'"' if value is not None else '') for key,value in node.attrs.items())
        return '<'+node.tag+attrs+'>'+('' if node.tag in self.VOID else content+'</'+node.tag+'>')


def text_html(value):
    return escape(value).replace('\n','<br>')


def block_html(block):
    title = '<h2>'+text_html(block['title'])+'</h2>' if block['title'] else ''
    content = title+'<p>'+text_html(block['body'])+'</p>'
    if block['type']=='button':
        url = block['url']; external = url.startswith(('https://','http://'))
        content = '<a class="button button--primary" href="'+escape(url,quote=True)+'"'+(' target="_blank" rel="noopener noreferrer"' if external else '')+'>'+text_html(block['label'])+'</a>'
    elif block['type']=='faq':
        content = title+''.join('<details><summary>'+text_html(v['question'])+'</summary><p>'+text_html(v['answer'])+'</p></details>' for v in block['items'])
    return '<section class="site-block site-block--'+block['type']+' site-block--'+block['style']+'" data-block-id="'+block['id']+'">'+content+'</section>'


def render_site(source, value, page=None):
    doc = Document(source); preview = page is not None
    sections = {item['key']:item for items in value['layout'].values() for item in items}

    def walk(node):
        attrs = node.attrs
        area = 'login' if 'login-composition' in attrs.get('class','').split() else attrs.get('data-page')
        if area in PAGES:
            layouts = {d:value['theme'].get(area+'_'+d) for d in DEVICES}
            if any(layouts.values()):
                attrs['data-page-design'] = json.dumps(dict(page=area,catalog=layer_catalog(area,value['blocks']),**layouts),ensure_ascii=False)
        if preview and node.tag=='script':
            node.tag=''; node.raw=''; node.children=[]; return
        if attrs.get('data-edit-key') in TEXTS:
            node.children=[Node(raw=text_html(value['texts'][attrs['data-edit-key']]))]
        if attrs.get('data-section-key') in sections and not sections[attrs['data-section-key']]['visible']:
            attrs['hidden']=None
        group = attrs.get('data-section-group')
        if group in value['layout']:
            marked = {child.attrs['data-section-key']:child for child in node.children if 'data-section-key' in child.attrs}
            ordered = iter([marked[item['key']] for item in value['layout'][group] if item['key'] in marked])
            node.children=[next(ordered) if 'data-section-key' in child.attrs else child for child in node.children]
        if attrs.get('data-slot') in PAGES:
            node.children=[Node(raw=block_html(block)) for block in value['blocks'] if block['slot']==attrs['data-slot'] and block['visible']]
        if value['theme']['logo'] and 'brand' in attrs.get('class','').split():
            logo = value['theme']['logo']; prefix = '/admin-api/site/logo/' if preview else '/site-logo/'
            node.children=[Node('img', [('src',prefix+logo['name']),('alt',logo['alt']),('class','site-logo')])]
        if preview:
            if attrs.get('id') in ('auth-view','app-view'):
                hidden = (attrs['id']=='auth-view') != (page=='login')
                classes = attrs.get('class','').split(); classes = [c for c in classes if c!='hidden']
                if hidden: classes.append('hidden')
                attrs['class']=' '.join(classes)
            if 'data-page' in attrs:
                classes = [c for c in attrs.get('class','').split() if c!='active']
                if attrs['data-page']==page: classes.append('active')
                attrs['class']=' '.join(classes)
            examples = {'account-display-name':'Pessoa de exemplo (dados fictícios)', 'account-current-email':'exemplo@example.test',
                        'account-created':'Não registrado', 'account-last-login':'Não registrado',
                        'profile-summary':'Dados de exemplo: Curitiba/PR · Administração · Ensino médio.',
                        'jobs-list':'Exemplo de vaga — nenhum anúncio real é consultado nesta prévia.',
                        'courses-list':'Exemplo de curso — nenhum catálogo real é consultado nesta prévia.',
                        'resume-list':'Currículo de exemplo — nenhum arquivo real é consultado nesta prévia.',
                        'ai-availability':'Prévia com dados fictícios.', 'advice-list':'Complete seu perfil de exemplo.'}
            if attrs.get('id') in examples:
                node.children=[Node(raw=escape(examples[attrs['id']]))]
            if 'id' in attrs and attrs['id'] in ('cookie-banner','cookie-preferences'):
                attrs['hidden']=None
        for child in node.children:
            walk(child)
    walk(doc.root)
    return doc.render()


def register_public(app, site):
    @app.get('/api/site-content')
    def site_content():
        return jsonify(published(site))

    @app.get('/site-theme.css')
    def site_theme():
        value=published(site)
        response = Response(css(value),mimetype='text/css')
        response.add_etag(); response.cache_control.no_cache=True
        return response.make_conditional(request)

    @app.get('/site-logo/<name>')
    def site_logo(name):
        logo = published(site)['theme']['logo']
        if not logo or name!=logo['name']:
            abort(404)
        return logo_response(site,name)

    @app.after_request
    def public_content(response):
        if request.endpoint=='home' and response.status_code==200:
            response.set_data(render_site(response.get_data(as_text=True),published(site)))
            response.headers['Cache-Control']='no-cache'
        if not request.path.startswith('/admin'):
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"
            response.headers['X-Content-Type-Options']='nosniff'
        return response


def logo_dir(site):
    path = Path(site.UPLOAD_DIR)/'site-logos'; path.mkdir(parents=True,exist_ok=True)
    return path


def logo_response(site, name):
    if not re.fullmatch(r'[0-9a-f]{32}\.png',name):
        abort(404)
    path = logo_dir(site)/name
    if not path.is_file() or path.is_symlink():
        abort(404)
    response = send_file(path,mimetype='image/png')
    response.headers['X-Content-Type-Options']='nosniff'
    return response


def register_editor(bp, site, restricted, log):
    from admin import connection as admin_connection, client_ip

    def limited(kind, maximum):
        now = time.time()
        with site.db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("DELETE FROM request_limits WHERE key LIKE 'site-editor:%' AND window<=?",(int(now),))
            key = 'site-editor:'+kind+':'+client_ip()
            row = db.execute('SELECT * FROM request_limits WHERE key=?',(key,)).fetchone()
            if row and row['count']>=maximum:
                abort(429)
            db.execute('INSERT INTO request_limits VALUES (?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1',
                       (key,int(now)+600))

    def payload():
        if request.content_length is None or request.content_length>250000:
            raise ValueError('Rascunho muito grande (limite de 250 KB).')
        value = request.get_json(silent=True)
        if not isinstance(value,dict):
            raise ValueError('Envie um objeto JSON.')
        return value

    def checked(value):
        result = validate(value)
        logo = result['theme']['logo']
        if logo and not (logo_dir(site)/logo['name']).is_file():
            raise ValueError('Envie novamente o logo antes de salvar.')
        return result

    def version(db, value, note):
        db.execute('INSERT INTO site_versions (created_at,note,snapshot) VALUES (?,?,?)',
                   (site.timestamp(),note,json.dumps(value,ensure_ascii=False)))
        db.execute('DELETE FROM site_versions WHERE id NOT IN (SELECT id FROM site_versions ORDER BY id DESC LIMIT 30)')

    @bp.get('/admin/site')
    @restricted
    def editor():
        template = 'editor_site.html' if request.args.get('modo')=='classico' else 'canvas_login.html'
        return render_template(template,csrf=g.admin_session['csrf'])

    @bp.get('/admin-api/site/state')
    @restricted
    def editor_state():
        with site.db_connection() as db:
            draft, public = read(db,'draft'),read(db,'published')
            meta=db.execute('SELECT saved_at FROM site_editor_meta WHERE id=1').fetchone()
            history=[dict(row) for row in db.execute('SELECT id,created_at,note FROM site_versions ORDER BY id DESC')]
        return jsonify(draft=draft, published=public, revision=digest(draft), saved_at=meta[0] if meta else None, catalog=catalog(), layers={p:layer_catalog(p,draft['blocks']) for p in PAGES}, history=history, issues=problems(draft['theme'],draft['blocks']),
                       changes=changes(public,draft), contrast=contrast(draft['theme']),
                       contrast_fix=max(('#000000','#ffffff'),key=lambda c:contrast(dict(draft['theme'],text=c))))

    @bp.post('/admin-api/site/render')
    @restricted
    def preview():
        try:
            data=payload(); value=checked(data.get('content')); page=data.get('page')
            if not isinstance(page,str) or page not in PAGES:
                raise ValueError('Página inválida.')
        except (ValueError,TypeError) as exc:
            return jsonify(error=str(exc)),400
        html=render_site(render_template('pagina_principal.html'),value,page)
        return jsonify(html=html,css=css(value))

    @bp.post('/admin-api/site/<action>')
    @restricted
    def mutate(action):
        if action not in {'draft','publish','restore','undo'}:
            abort(404)
        try:
            data=payload()
            if action in {'publish','undo'}:
                limited('publish',10)
            with site.db_connection() as db:
                db.execute('BEGIN IMMEDIATE')
                draft, public = read(db,'draft',strict=action=='publish'),read(db,'published')
                if data.get('revision')!=digest(draft):
                    return jsonify(error='O rascunho mudou em outra aba. Recarregue antes de continuar.'),409
                if action=='draft':
                    value=checked(data.get('content')); write(db,'draft',value)
                elif action=='restore':
                    identifier=data.get('version')
                    if identifier=='original':
                        value=defaults()
                    elif type(identifier) is int:
                        row=db.execute('SELECT snapshot FROM site_versions WHERE id=?',(identifier,)).fetchone()
                        if not row: raise ValueError('Versão não encontrada.')
                        value=checked(migrate_saved_layout(json.loads(row[0])))
                    else: raise ValueError('Versão inválida.')
                    write(db,'draft',value)
                else:
                    value=draft
                    if action=='undo':
                        rows=db.execute('SELECT snapshot FROM site_versions ORDER BY id DESC LIMIT 2').fetchall()
                        if len(rows)<2: raise ValueError('Não há publicação anterior para desfazer.')
                        value=checked(migrate_saved_layout(json.loads(rows[1][0])))
                    else:
                        if data.get('confirm') is not True: raise ValueError('Confirme a publicação.')
                        issues = problems(checked(value)['theme'],value['blocks'])
                        if any(problem['critical'] for problem in issues):
                            raise ValueError('Corrija os problemas críticos antes de publicar.')
                        if (issues or contrast(value['theme'])<4.5) and data.get('confirm_low_contrast') is not True:
                            raise ValueError('Contraste abaixo de 4,5:1. Confirme o aviso antes de publicar.')
                    if not db.execute('SELECT 1 FROM site_versions').fetchone():
                        version(db,public,'Padrão anterior à primeira publicação')
                    version(db,value,'Desfazer última publicação' if action=='undo' else plain(data.get('note',''),200,empty=True))
                    write(db,'published',value); write(db,'draft',value)
                db.execute('INSERT OR REPLACE INTO site_editor_meta VALUES (1,?)',(site.timestamp(),))
            CACHE.clear()
            with admin_connection() as db:
                from admin import audit
                if action!='draft':
                    audit(db,'site_'+action,'site',details={'parts':changes(public,value)})
                if action=='draft' and draft['theme']['logo']!=value['theme']['logo']:
                    audit(db,'site_logo','site',details={'operation':'draft_change'})
            return jsonify(message='Rascunho salvo.' if action in {'draft','restore'} else 'Publicação atualizada.',revision=digest(value))
        except (ValueError,TypeError) as exc:
            return jsonify(error=str(exc)),400

    @bp.post('/admin-api/site/logo')
    @restricted
    def upload_logo():
        limited('upload',10)
        try:
            if request.content_length is None or request.content_length>1100000:
                raise ValueError('O logo deve ter até 1 MB.')
            alt=plain(request.form.get('alt'),160)
            uploaded=request.files.get('file')
            if not uploaded or Path(uploaded.filename or '').suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
                raise ValueError('Envie PNG, JPG ou WEBP; SVG não é permitido.')
            raw=uploaded.read(1048577)
            if len(raw)>1048576: raise ValueError('O logo deve ter até 1 MB.')
            png=raw.startswith(b'\x89PNG\r\n\x1a\n') and raw.endswith(b'\x00\x00\x00\x00IEND\xaeB`\x82')
            jpg=raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9')
            webp=raw[:4]==b'RIFF' and raw[8:12]==b'WEBP' and int.from_bytes(raw[4:8],'little')+8==len(raw)
            if not (png or jpg or webp): raise ValueError('Conteúdo de imagem inválido ou dados extras no arquivo.')
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format not in {'PNG','JPEG','WEBP'} or image.width*image.height>4000000 or getattr(image,'n_frames',1)!=1:
                        raise ValueError('Use uma imagem estática de até 4 milhões de pixels.')
                    image.load(); clean=image.convert('RGBA'); clean.info.clear()
                    name=secrets.token_hex(16)+'.png'; clean.save(logo_dir(site)/name,format='PNG')
            log('site_logo','site',details={'operation':'upload'})
            return jsonify(logo={'name':name,'alt':alt})
        except (ValueError,TypeError,OSError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:
            return jsonify(error='Imagem inválida. '+str(exc)[:180]),400

    @bp.get('/admin-api/site/logo/<name>')
    @restricted
    def preview_logo(name):
        return logo_response(site,name)
