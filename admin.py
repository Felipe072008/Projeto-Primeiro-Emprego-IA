"""Área administrativa isolada: autenticação, auditoria e metadados permitidos."""
import hashlib
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from flask import Blueprint, abort, g, jsonify, make_response, render_template, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
COOKIE = 'peia_admin'


def database_path():
    return Path(os.environ.get('FIRST_JOB_ADMIN_DATABASE', BASE_DIR / 'admin.db')).resolve()


@contextmanager
def connection():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def init_admin():
    with connection() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS admin_account (
                id INTEGER PRIMARY KEY CHECK(id=1), username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, created_at TEXT NOT NULL, last_login_at TEXT);
            CREATE TABLE IF NOT EXISTS admin_settings (id INTEGER PRIMARY KEY CHECK(id=1), pin_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS admin_attempts (
                id INTEGER PRIMARY KEY, ip TEXT NOT NULL, kind TEXT NOT NULL,
                success INTEGER NOT NULL, created_at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS admin_attempt_window ON admin_attempts(ip,created_at);
            CREATE TABLE IF NOT EXISTS admin_access_calls (ip TEXT NOT NULL, created_at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS admin_access_window ON admin_access_calls(ip,created_at);
            CREATE TABLE IF NOT EXISTS admin_blocks (ip TEXT PRIMARY KEY, blocked_until REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, action TEXT NOT NULL,
                target_type TEXT, target_id TEXT, details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, stage TEXT NOT NULL,
                last_seen REAL NOT NULL, expires_at REAL NOT NULL);
        ''')
    try:
        database_path().chmod(0o600)
    except OSError:
        pass


def audit(db, action, target_type='', target_id='', details=None):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    db.execute('INSERT INTO admin_audit_log (created_at,action,target_type,target_id,details) VALUES (?,?,?,?,?)',
               (datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(), action, target_type,
                str(target_id), json.dumps(details or {}, ensure_ascii=False)))


def create_account(username, password, pin):
    if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{3,80}', username):
        raise ValueError('Use um usuário de 3 a 80 caracteres: letras, números, ponto, hífen ou sublinhado.')
    if not isinstance(password, str) or not 12 <= len(password) <= 256:
        raise ValueError('A senha deve ter de 12 a 256 caracteres.')
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9]{6}', pin):
        raise ValueError('O PIN deve ter exatamente 6 dígitos.')
    init_admin()
    with connection() as db:
        if db.execute('SELECT 1 FROM admin_account').fetchone():
            raise ValueError('Já existe um administrador. Use a troca de credenciais no painel.')
        from datetime import datetime, timezone
        db.execute('INSERT INTO admin_account VALUES (1,?,?,?,NULL)',
                   (username, generate_password_hash(password), datetime.now(timezone.utc).isoformat()))
        db.execute('INSERT INTO admin_settings VALUES (1,?)', (generate_password_hash(pin),))
        audit(db, 'account_created', 'admin', 1)


def client_ip():
    # Ativar somente no WSGI do PythonAnywhere, cujo balanceador sobrescreve X-Real-IP.
    value = request.headers.get('X-Real-IP', '') if os.environ.get('ADMIN_TRUST_PYTHONANYWHERE') == '1' else ''
    try:
        return str(ipaddress.ip_address(value or request.remote_addr or '127.0.0.1'))
    except ValueError:
        return request.remote_addr or 'unknown'


def is_blocked(db, ip, now):
    row = db.execute('SELECT blocked_until FROM admin_blocks WHERE ip=?', (ip,)).fetchone()
    return bool(row and row[0] > now)


def attempt(db, ip, kind, ok, now):
    db.execute('INSERT INTO admin_attempts (ip,kind,success,created_at) VALUES (?,?,?,?)', (ip, kind, int(ok), now))
    audit(db, 'access_' + kind, details={'success': bool(ok)})
    if ok or kind == 'blocked':
        return False
    errors = db.execute("SELECT COUNT(*) FROM admin_attempts WHERE ip=? AND success=0 AND kind IN ('pin','login','password') AND created_at>=?", (ip,now-900)).fetchone()[0]
    if errors >= 5:
        db.execute('INSERT INTO admin_blocks VALUES (?,?) ON CONFLICT(ip) DO UPDATE SET blocked_until=excluded.blocked_until', (ip, now+900))
        return True
    return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_session(db, stage, previous=None):
    if previous:
        db.execute('DELETE FROM admin_sessions WHERE token_hash=?', (previous,))
    token, csrf, now = secrets.token_urlsafe(32), secrets.token_urlsafe(32), time.time()
    db.execute('DELETE FROM admin_sessions WHERE expires_at < ?', (now,))
    db.execute('INSERT INTO admin_sessions VALUES (?,?,?,?,?)',
               (token_hash(token), csrf, stage, now, now + (1800 if stage == 'admin' else 300)))
    return token, csrf


def set_cookie(response, token):
    response.set_cookie(COOKIE, token, httponly=True, secure=True, samesite='Strict', path='/')
    return response


def session_row(db):
    token = request.cookies.get(COOKIE, '')
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        return None
    return db.execute('SELECT * FROM admin_sessions WHERE token_hash=? AND expires_at>?',
                      (token_hash(token), time.time())).fetchone()


def csrf_valid(row):
    value = request.headers.get('X-CSRF-Token', '')
    return bool(row and re.fullmatch(r'[A-Za-z0-9_-]{20,100}', value) and secrets.compare_digest(value, row['csrf']))


def invalid(status=401):
    return jsonify(error='Dados inválidos'), status


def body():
    if request.content_length is None or request.content_length > 50000:
        abort(400)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    return data


def text(data, key, limit=300, required=True):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError('Confira os campos e seus limites de tamanho.')
    return value.strip()


def register_admin(app, site):
    init_admin()
    bp = Blueprint('admin', __name__)

    def restricted(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            with connection() as db:
                row = session_row(db)
                if not row or row['stage'] != 'admin':
                    audit(db, 'access_denied')
                    return invalid()
                if request.method != 'GET' and not csrf_valid(row):
                    audit(db, 'csrf_denied')
                    return invalid(403)
                now = time.time()
                db.execute('UPDATE admin_sessions SET last_seen=?,expires_at=? WHERE token_hash=?',
                           (now, now + 1800, row['token_hash']))
                g.admin_session = dict(row)
            if any(type(value) is int and not 1 <= value <= 9223372036854775807 for value in kwargs.values()):
                return invalid(400)
            return view(*args, **kwargs)
        return wrapped

    @bp.after_request
    def private_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        return response

    @bp.errorhandler(400)
    def bad_input(_error):
        return invalid(400)

    @bp.get('/admin-access')
    def access():
        with connection() as db:
            db.execute('BEGIN IMMEDIATE')
            now, ip = time.time(), client_ip()
            db.execute('DELETE FROM admin_access_calls WHERE created_at<=?', (now - 600,))
            count = db.execute('SELECT COUNT(*) FROM admin_access_calls WHERE ip=?', (ip,)).fetchone()[0]
            if count >= 20:
                audit(db, 'access_blocked', details={'endpoint': 'admin-access'})
                return invalid(429)
            db.execute('INSERT INTO admin_access_calls VALUES (?,?)', (ip, now))
            token, csrf = new_session(db, 'initial')
        return set_cookie(jsonify(csrf=csrf), token)

    @bp.post('/admin-access/<kind>')
    def authenticate(kind):
        if kind not in {'pin', 'login'}:
            abort(404)
        data, now, ip = body(), time.time(), client_ip()
        with connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = session_row(db)
            if is_blocked(db, ip, now):
                attempt(db, ip, 'blocked', False, now)
                return invalid(429)
            valid_csrf = csrf_valid(row)
            stage = row['stage'] if row else ''
            ok = False
            if valid_csrf and kind == 'pin' and stage == 'initial':
                pin = data.get('pin')
                settings = db.execute('SELECT pin_hash FROM admin_settings WHERE id=1').fetchone()
                ok = bool(settings and isinstance(pin, str) and re.fullmatch(r'[0-9]{6}', pin)
                          and check_password_hash(settings[0], pin))
            if valid_csrf and kind == 'login' and stage == 'pin':
                username, password = data.get('username'), data.get('password')
                account = db.execute('SELECT * FROM admin_account WHERE id=1').fetchone()
                ok = bool(account and isinstance(username, str) and len(username) <= 80
                          and isinstance(password, str) and len(password) <= 256
                          and check_password_hash(account['password_hash'], password)
                          and secrets.compare_digest(account['username'].encode(), username.encode()))
            blocked = attempt(db, ip, kind, ok, now)
            if not ok:
                return invalid(429 if blocked else 401)
            token, csrf = new_session(db, 'pin' if kind == 'pin' else 'admin', row['token_hash'])
            if kind == 'login':
                db.execute('UPDATE admin_account SET last_login_at=? WHERE id=1', (site.timestamp(),))
        return set_cookie(jsonify(csrf=csrf, next='/admin' if kind == 'login' else 'login'), token)

    @bp.get('/admin')
    @restricted
    def panel():
        return render_template('admin.html', csrf=g.admin_session['csrf'])

    @bp.get('/admin-assets/<name>')
    @restricted
    def assets(name):
        if name not in {'admin.js', 'admin.css'}:
            abort(404)
        return send_from_directory(BASE_DIR / 'admin_assets', name)

    def log(action, target_type='', target_id='', details=None):
        with connection() as db:
            audit(db, action, target_type, target_id, details)

    from arquivos_conta import file_path as safe_file_path, remove_records as shared_remove

    def file_path(name):
        return safe_file_path(site.UPLOAD_DIR, name)

    def remove_records(user_id=None, resume_id=None):
        pending = shared_remove(site.db_connection, site.UPLOAD_DIR, user_id=user_id, resume_id=resume_id)
        if pending:
            log('file_cleanup_pending', 'user' if user_id is not None else 'resume', user_id if user_id is not None else resume_id, {'pending_files':pending})
            raise ValueError('Registros excluídos; há arquivos temporários pendentes de limpeza no servidor. Confira Atividades e o roteiro de operação.')

    def users_data():
        query = request.args.get('q', '')
        status = request.args.get('status', '')
        if len(query) > 120 or status not in {'', 'active', 'deactivated'}:
            abort(400)
        with site.db_connection() as db:
            rows = db.execute('''SELECT u.id,u.name,u.email,u.created_at,u.last_login_at,u.status,
                (SELECT COUNT(*) FROM resumes r WHERE r.user_id=u.id) AS resume_count FROM users u
                WHERE (?='' OR name LIKE ? OR email LIKE ?) AND (?='' OR status=?)
                ORDER BY id DESC LIMIT 200''', (query, '%' + query + '%', '%' + query + '%', status, status)).fetchall()
        return [dict(row, completion=site.profile_completion(site.get_profile(row['id']))) for row in rows]

    def catalog_rows(kind):
        from catalogo_oportunidades import DATA_DIR, valid_record
        from sincronizacao_catalogo import read_state
        from administracao_dados import mirror
        path = DATA_DIR / (kind + '.json')
        records = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        imported, _runs = read_state(kind)
        with site.db_connection() as db:
            mirror(db, kind, records + imported)
            rows = db.execute(f'SELECT * FROM {kind} WHERE payload IS NOT NULL ORDER BY id DESC').fetchall()
        result = []
        for row in rows:
            source = row['catalog_source'] if kind == 'jobs' else row['source']
            result.append(dict(json.loads(row['payload']), admin_id=row['id'], origin=source,
                               is_hidden=bool(row['is_hidden']), is_removed=bool(row['is_removed']),
                               public_visible=not row['is_hidden'] and not row['is_removed'] and valid_record(json.loads(row['payload']),kind,site.now_sp().date())) )
        return result

    @bp.get('/admin-api/users')
    @restricted
    def users():
        return jsonify(items=users_data(), limit=200)

    @bp.post('/admin-api/users/<int:user_id>/<action>')
    @restricted
    def change_user(user_id, action):
        data = body()
        try:
            if action == 'delete':
                if data.get('confirmation') != f'APAGAR {user_id}':
                    raise ValueError(f'Digite APAGAR {user_id} para confirmar.')
                remove_records(user_id=user_id)
            elif action in {'deactivate', 'reactivate'}:
                with site.db_connection() as db:
                    cursor = db.execute('UPDATE users SET status=?,deactivated_at=?,session_version=session_version+1 WHERE id=?',
                        ('deactivated' if action == 'deactivate' else 'active', site.timestamp() if action == 'deactivate' else None, user_id))
                    if not cursor.rowcount:
                        abort(404)
            else:
                abort(404)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        log('user_' + action, 'user', user_id)
        return jsonify(message='Operação concluída.')

    @bp.get('/admin-api/resumes')
    @restricted
    def resumes():
        with site.db_connection() as db:
            rows = db.execute('''SELECT r.id,r.user_id,u.name AS owner,r.kind,r.created_at,r.saved_name,
                length(CAST(r.content_json AS BLOB)) AS generated_bytes
                FROM resumes r JOIN users u ON u.id=r.user_id ORDER BY r.id DESC LIMIT 200''').fetchall()
        result = []
        for row in rows:
            path = file_path(row['saved_name'])
            result.append({key: row[key] for key in ('id','user_id','owner','kind','created_at')} | {
                'size_bytes': path.stat().st_size if path and path.exists() else row['generated_bytes'],
                'storage': 'pdf' if row['kind'] == 'uploaded' else 'json'})
        return jsonify(items=result, limit=200)

    @bp.delete('/admin-api/resumes/<int:resume_id>')
    @restricted
    def delete_resume(resume_id):
        try:
            remove_records(resume_id=resume_id)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        log('resume_deleted', 'resume', resume_id)
        return jsonify(message='Currículo excluído.')

    def validate_offer(data, kind, old=None):
        from datetime import date
        from urllib.parse import urlparse
        from catalogo_oportunidades import AREAS, valid_record
        row = dict(old or {})
        for field, limit in {'title':200,'source':200,'original_url':2048,'description':5000,
                             'review_by':10,'availability_evidence':2000}.items():
            row[field] = text(data, field, limit)
        row['checked_on'] = site.now_sp().date().isoformat()
        row['last_verified_at'] = site.timestamp()
        row['availability_status'] = 'open'
        row['verification_method'] = 'manual'
        row['status'] = 'published'
        row['id'] = old['id'] if old else 'admin-' + secrets.token_hex(12)
        row['is_individual'] = True
        row['expires_on'] = text(data, 'expires_on', 10, False) or None
        areas = data.get('areas')
        requirements = data.get('requirements')
        if not isinstance(areas, list) or not areas or len(areas) > len(AREAS) or any(a not in AREAS for a in areas if isinstance(a,str)) or any(not isinstance(a,str) for a in areas):
            raise ValueError('Selecione ao menos uma área válida.')
        if not isinstance(requirements, list) or len(requirements) > 30 or any(not isinstance(v,str) or len(v)>500 for v in requirements):
            raise ValueError('Informe os requisitos em uma lista de até 30 textos.')
        row.update(areas=areas, requirements=requirements)
        try:
            url = urlparse(row['original_url'])
            if url.scheme not in {'http','https'} or not url.hostname or url.username or url.password or url.port not in {None,80,443}:
                raise ValueError()
            review = date.fromisoformat(row['review_by'])
            if review < site.now_sp().date():
                raise ValueError()
            if row['expires_on'] and date.fromisoformat(row['expires_on']) < site.now_sp().date():
                raise ValueError()
        except ValueError:
            raise ValueError('Confira o link oficial e as datas de revisão/validade.') from None
        if kind == 'jobs':
            row.update(company=text(data,'company',200), location=text(data,'location',200),
                       city='Curitiba', state='PR', entry_level=True, contract_type=text(data,'contract_type',20))
            from catalogo_oportunidades import normalized
            place = normalized(row['location'])
            if not re.search(r'\bcuritiba\b',place) or not re.search(r'\bpr\b',place):
                raise ValueError('O local deve confirmar Curitiba/PR.')
            if not requirements:
                raise ValueError('Registre os requisitos confirmados na fonte.')
            row['contract'] = {'aprendiz':'Jovem Aprendiz','estagio':'Estágio','clt':'CLT de entrada'}.get(row['contract_type'],'')
        else:
            row.update(institution=text(data,'institution',200), certificate=text(data,'certificate',1500),
                       certificate_status=text(data,'certificate_status',20), enrollment_status='open', access_status='free_full',
                       access_evidence=text(data,'access_evidence',1500), free=True,
                       course_type=text(data,'course_type',30), duration=text(data,'duration',100,False))
            if row['certificate_status'] not in {'free','paid','unknown'}:
                raise ValueError('Condição do certificado inválida.')
            row['certificate_cost'] = {'free':'Gratuito','paid':'Pago','unknown':'Não informado'}[row['certificate_status']]
            row['certificate_source'] = text(data,'certificate_source',2048,False)
            if row['certificate_source']:
                try:
                    certificate_url = urlparse(row['certificate_source'])
                    if certificate_url.scheme not in {'http','https'} or not certificate_url.hostname or certificate_url.username or certificate_url.password:
                        raise ValueError()
                except ValueError:
                    raise ValueError('Link das condições do certificado inválido.') from None
            if row['certificate_status'] != 'unknown' and not row['certificate_source']:
                raise ValueError('Informe a fonte das condições do certificado.')
        # O catálogo mantém o requisito HTTPS e anúncio individual já aplicado às ofertas.
        if not valid_record(row, kind, site.now_sp().date()):
            raise ValueError('Oferta fora das validações atuais do catálogo: use HTTPS, página individual e confira os campos.')
        return row

    @bp.route('/admin-api/catalog/<kind>', methods=['GET','POST'])
    @restricted
    def catalog(kind):
        if kind not in {'jobs','courses'}:
            abort(404)
        if request.method == 'GET':
            origin, visibility = request.args.get('origin',''), request.args.get('visibility','')
            if origin not in {'','auto','manual'} or visibility not in {'','visible','hidden','removed'}:
                abort(400)
            rows = catalog_rows(kind)
            return jsonify(items=[r for r in rows if (not origin or r['origin']==origin) and (
                not visibility or (visibility=='removed' and r['is_removed']) or
                (visibility=='hidden' and r['is_hidden'] and not r['is_removed']) or
                (visibility=='visible' and r['public_visible']))])
        try:
            from administracao_dados import mirror
            from catalogo_oportunidades import canonical_url
            row = validate_offer(body(), kind)
            with site.db_connection() as db:
                key = canonical_url(row['original_url'])
                existing = db.execute(f'SELECT external_key,payload FROM {kind} WHERE payload IS NOT NULL').fetchall()
                if any(key in {r['external_key'],canonical_url(json.loads(r['payload'])['original_url'])} for r in existing):
                    raise ValueError('Esta URL já está cadastrada, inclusive se removida.')
                mirror(db, kind, [row])
                db.execute(f'UPDATE {kind} SET is_override=1 WHERE external_key=?', (canonical_url(row['original_url']),))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        log('catalog_added', kind, row['id'])
        return jsonify(message='Oferta cadastrada.'), 201

    @bp.patch('/admin-api/catalog/<kind>/<int:item_id>')
    @restricted
    def change_catalog(kind, item_id):
        if kind not in {'jobs','courses'}:
            abort(404)
        data = body()
        try:
            with site.db_connection() as db:
                db.execute('BEGIN IMMEDIATE')
                item = db.execute(f'SELECT * FROM {kind} WHERE id=?', (item_id,)).fetchone()
                if not item or not item['payload']:
                    abort(404)
                action = data.get('action')
                if action in {'hide','show','remove'}:
                    if item['is_removed']:
                        raise ValueError('Uma oferta removida não pode ser reativada pela importação ou pelo botão de exibição.')
                    if action == 'remove':
                        db.execute(f'UPDATE {kind} SET is_removed=1,removed_at=? WHERE id=?', (site.timestamp(),item_id))
                    else:
                        db.execute(f'UPDATE {kind} SET is_hidden=? WHERE id=?', (int(action=='hide'),item_id))
                elif action == 'edit':
                    source = item['catalog_source'] if kind == 'jobs' else item['source']
                    if source != 'manual' or item['is_removed']:
                        raise ValueError('Somente ofertas manuais não removidas podem ser editadas.')
                    row = validate_offer(data, kind, json.loads(item['payload']))
                    from catalogo_oportunidades import canonical_url
                    key = canonical_url(row['original_url'])
                    others = db.execute(f'SELECT external_key,payload FROM {kind} WHERE id<>? AND payload IS NOT NULL', (item_id,)).fetchall()
                    if any(key in {r['external_key'],canonical_url(json.loads(r['payload'])['original_url'])} for r in others):
                        raise ValueError('Esta URL já está cadastrada.')
                    db.execute(f'UPDATE {kind} SET payload=?,is_override=1 WHERE id=?', (json.dumps(row,ensure_ascii=False),item_id))
                else:
                    raise ValueError('Ação inválida.')
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        log('catalog_' + action, kind, item_id)
        return jsonify(message='Oferta atualizada.')

    @bp.get('/admin-api/overview')
    @restricted
    def overview():
        from datetime import timedelta
        with site.db_connection() as db:
            counts = dict(db.execute('''SELECT COUNT(*) AS total,
                SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN status='deactivated' THEN 1 ELSE 0 END) AS deactivated,
                SUM(CASE WHEN created_at>=? THEN 1 ELSE 0 END) AS registrations_7d,
                SUM(CASE WHEN created_at>=? THEN 1 ELSE 0 END) AS registrations_30d FROM users''',
                ((site.now_sp()-timedelta(days=7)).isoformat(),(site.now_sp()-timedelta(days=30)).isoformat())).fetchone())
            ids = [r[0] for r in db.execute('SELECT id FROM users')]
            resume_counts = {r['kind']:r['n'] for r in db.execute('SELECT kind,COUNT(*) AS n FROM resumes GROUP BY kind')}
        counts['complete_profiles'] = sum(site.profile_completion(site.get_profile(i))==100 for i in ids)
        catalogs = {}
        for kind in ('jobs','courses'):
            rows = catalog_rows(kind)
            catalogs[kind] = {'total':len(rows),'visible':sum(r['public_visible'] for r in rows),
                'ineligible':sum(not r['public_visible'] and not r['is_hidden'] and not r['is_removed'] for r in rows),
                'hidden':sum(r['is_hidden'] and not r['is_removed'] for r in rows), 'removed':sum(r['is_removed'] for r in rows),
                'auto':sum(r['origin']=='auto' for r in rows),'manual':sum(r['origin']=='manual' for r in rows)}
        return jsonify(users=counts,resumes=resume_counts,catalogs=catalogs)

    @bp.get('/admin-api/system')
    @restricted
    def system():
        from sincronizacao_catalogo import read_state, database_path as catalog_path
        from fontes_catalogo import sources
        _items, runs = read_state('jobs')
        updates = {}
        for kind in ('jobs','courses'):
            selected = [r for source in sources(kind) if (r := runs.get(source['id']))]
            latest = max(selected,key=lambda r:r['last_attempt_at']) if selected else None
            updates[kind] = {'last_attempt': latest, 'sources': selected,
                             'last_success_at': max((r['last_success_at'] for r in selected if r['last_success_at']),default=None)}
        def size(path):
            return path.stat().st_size if path.exists() else 0
        return jsonify(time=site.timestamp(),timezone='America/Sao_Paulo',updates=updates,
            database_bytes=size(site.DATABASE),admin_database_bytes=size(database_path()),catalog_database_bytes=size(catalog_path()),
            uploads_bytes=sum(p.stat().st_size for p in site.UPLOAD_DIR.rglob('*') if p.is_file() and not p.is_symlink()),
            scheduling='O histórico registra execuções recebidas; não comprova que o agendador externo está ativo.')

    @bp.get('/admin-api/activities')
    @restricted
    def activities():
        with connection() as db:
            entries = [dict(r) for r in db.execute('SELECT * FROM admin_audit_log ORDER BY id DESC LIMIT 200')]
            attempts = [dict(r) for r in db.execute('SELECT id,ip,kind,success,created_at FROM admin_attempts ORDER BY id DESC LIMIT 200')]
        return jsonify(items=entries,attempts=attempts,limit=200)

    @bp.post('/admin-api/account')
    @restricted
    def account():
        data = body()
        try:
            password = data.get('current_password')
            new_password = data.get('new_password', '')
            if not isinstance(password,str) or not 1 <= len(password) <= 256 or not isinstance(new_password,str) or len(new_password)>256:
                raise ValueError('Confira os campos e seus limites de tamanho.')
            pin = text(data,'new_pin',6,False)
            if (not new_password and not pin) or (new_password and len(new_password)<12) or (pin and not re.fullmatch(r'[0-9]{6}',pin)):
                raise ValueError('Senha: 12 a 256 caracteres. PIN: exatamente 6 dígitos.')
            with connection() as db:
                db.execute('BEGIN IMMEDIATE')
                ip, now = client_ip(), time.time()
                if is_blocked(db, ip, now):
                    attempt(db, ip, 'blocked', False, now)
                    return invalid(429)
                row = db.execute('SELECT password_hash FROM admin_account WHERE id=1').fetchone()
                ok = bool(row and check_password_hash(row[0],password))
                blocked = attempt(db, ip, 'password', ok, now)
                if not ok:
                    return invalid(429 if blocked else 401)
                if new_password:
                    db.execute('UPDATE admin_account SET password_hash=? WHERE id=1',(generate_password_hash(new_password),))
                if pin:
                    db.execute('UPDATE admin_settings SET pin_hash=? WHERE id=1',(generate_password_hash(pin),))
                db.execute('DELETE FROM admin_sessions')
                audit(db,'credentials_changed','admin',1)
        except ValueError as exc:
            return jsonify(error=str(exc)),400
        response = jsonify(message='Credenciais atualizadas. Entre novamente.')
        response.delete_cookie(COOKIE,path='/',secure=True,httponly=True,samesite='Strict')
        return response

    @bp.post('/admin-api/logout')
    @restricted
    def logout():
        with connection() as db:
            db.execute('DELETE FROM admin_sessions WHERE token_hash=?',(g.admin_session['token_hash'],))
            audit(db,'logout','admin',1)
        response = jsonify(message='Sessão encerrada.')
        response.delete_cookie(COOKIE,path='/',secure=True,httponly=True,samesite='Strict')
        return response

    app.register_blueprint(bp)
