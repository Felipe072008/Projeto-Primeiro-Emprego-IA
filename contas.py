"""Dados de login e direitos da própria conta; utiliza somente o banco principal."""
import hashlib
import ipaddress
import json
import os
import re
import sqlite3
import tempfile
import time
import zipfile
from functools import wraps

from flask import Blueprint, jsonify, request, session, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from arquivos_conta import file_path, remove_records


class AccountError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def value(data, key, maximum, minimum=1, strip=False):
    item = data.get(key)
    if not isinstance(item, str) or not minimum <= len(item) <= maximum:
        raise AccountError('Confira os campos e os limites de tamanho informados.')
    return item.strip() if strip else item


def register_accounts(app, site):
    bp = Blueprint('account', __name__, url_prefix='/api/account')

    @bp.after_request
    def private(response):
        response.headers['Cache-Control'] = 'no-store'
        return response

    @bp.errorhandler(AccountError)
    def invalid(error):
        return jsonify(error=str(error)), error.status

    def input_data():
        if request.content_length is None or request.content_length > 8192:
            raise AccountError('Solicitação inválida.')
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise AccountError('Solicitação inválida.')
        return data

    def active(db):
        row = db.execute('SELECT * FROM users WHERE id=?', (session.get('user_id'),)).fetchone()
        if not row or row['status'] != 'active' or row['session_version'] != session.get('user_version', 0):
            session.clear()
            raise AccountError('Entre novamente para continuar.', 401)
        return row

    def password_check(db, data):
        user = active(db)
        password = value(data, 'current_password', 256)
        ip = request.remote_addr or 'unknown'
        if os.environ.get('ADMIN_TRUST_PYTHONANYWHERE') == '1':
            try:
                ip = str(ipaddress.ip_address(request.headers.get('X-Real-IP', ip)))
            except ValueError:
                pass
        keys = ['account:user:' + str(user['id']), 'account:ip:' + hashlib.sha256(ip.encode()).hexdigest()]
        now = int(time.time())
        db.execute("DELETE FROM request_limits WHERE key LIKE 'account:%' AND window<=?", (now,))
        limits = [db.execute('SELECT window,count FROM request_limits WHERE key=?', (key,)).fetchone() for key in keys]
        if any(row and row['count'] >= 5 for row in limits):
            raise AccountError('Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.', 429)
        if not check_password_hash(user['password_hash'], password):
            # O quinto erro inicia 15 minutos de bloqueio, sem reiniciar em cada tentativa.
            blocked = False
            for key, row in zip(keys, limits):
                count = row['count'] + 1 if row else 1
                expires = now + 900 if not row or count >= 5 else row['window']
                db.execute('INSERT INTO request_limits VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET window=excluded.window,count=excluded.count', (key, expires, count))
                blocked |= count >= 5
            # Persistir os erros antes de retornar a resposta, mesmo com rollback da operação.
            db.commit()
            raise AccountError('Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.' if blocked else 'Senha atual incorreta.', 429 if blocked else 401)
        return user

    def protected(view):
        @wraps(view)
        @site.login_required
        def wrapped(*args, **kwargs):
            return view(*args, **kwargs)
        return wrapped

    @bp.get('/profile')
    @protected
    def profile():
        with site.db_connection() as db:
            user = active(db)
            terms = [dict(row) for row in db.execute('SELECT terms_version,accepted_at FROM terms_acceptances WHERE user_id=? ORDER BY accepted_at DESC', (user['id'],))]
        return jsonify(user={key:user[key] for key in ('name','email','created_at','last_login_at')}, terms=terms)

    @bp.patch('/profile')
    @protected
    def name():
        name = value(input_data(), 'name', 120, strip=True)
        if not name:
            raise AccountError('Informe seu nome.')
        with site.db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            user = active(db)
            db.execute('UPDATE users SET name=? WHERE id=?', (name,user['id']))
        return jsonify(message='Nome atualizado.', user=site.get_user(user['id']))

    @bp.post('/email')
    @protected
    def email():
        data = input_data()
        email = value(data,'email',254,strip=True).lower()
        confirmation = value(data,'email_confirmation',254,strip=True).lower()
        if email != confirmation or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):
            raise AccountError('Informe um e-mail válido e repita o mesmo endereço.')
        try:
            with site.db_connection() as db:
                db.execute('BEGIN IMMEDIATE')
                user = password_check(db,data)
                if db.execute('SELECT 1 FROM users WHERE lower(email)=? AND id<>?',(email,user['id'])).fetchone():
                    raise AccountError('Este e-mail já está em uso.',409)
                db.execute('UPDATE users SET email=? WHERE id=?',(email,user['id']))
        except sqlite3.IntegrityError:
            raise AccountError('Este e-mail já está em uso.',409) from None
        return jsonify(message='E-mail atualizado. Use este endereço no próximo login.', user=site.get_user(user['id']))

    @bp.post('/password')
    @protected
    def password():
        data = input_data()
        password = value(data,'new_password',256,8)
        if password != value(data,'password_confirmation',256,8):
            raise AccountError('As novas senhas não coincidem.')
        with site.db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            user = password_check(db,data)
            if check_password_hash(user['password_hash'],password):
                raise AccountError('A nova senha deve ser diferente da atual.')
            db.execute('UPDATE users SET password_hash=?,session_version=session_version+1 WHERE id=?', (generate_password_hash(password),user['id']))
            version = user['session_version'] + 1
        session['user_version'] = version
        return jsonify(message='Senha atualizada. As outras sessões foram encerradas.')

    @bp.post('/sessions')
    @protected
    def sessions():
        input_data()
        with site.db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            user = active(db)
            db.execute('UPDATE users SET session_version=session_version+1 WHERE id=?',(user['id'],))
        session.clear()
        return jsonify(message='Você saiu de todos os dispositivos.')

    @bp.post('/export')
    @protected
    def export():
        data = input_data()
        stream = tempfile.SpooledTemporaryFile(max_size=8*1024*1024,mode='w+b')
        try:
            with site.db_connection() as db:
                db.execute('BEGIN IMMEDIATE')
                user = password_check(db,data)
                user_id = user['id']
                profile = db.execute('SELECT * FROM profiles WHERE user_id=?',(user_id,)).fetchone()
                sections = {row['section']:json.loads(row['data_json']) for row in db.execute('SELECT section,data_json FROM profile_sections WHERE user_id=?',(user_id,))}
                terms = [dict(row) for row in db.execute('SELECT terms_version,accepted_at FROM terms_acceptances WHERE user_id=?',(user_id,))]
                resumes = db.execute('SELECT * FROM resumes WHERE user_id=?',(user_id,)).fetchall()
                output = {'account':{key:user[key] for key in ('name','email','created_at','last_login_at')},'terms':terms,'profile':dict(profile) if profile else {},'sections':sections,'resumes':[]}
                with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
                    for row in resumes:
                        item = {key:row[key] for key in ('id','kind','original_name','created_at','updated_at')}
                        if row['kind'] == 'generated':
                            item['content'] = json.loads(row['content_json']) if row['content_json'] else None
                        else:
                            path = file_path(site.UPLOAD_DIR,row['saved_name'])
                            item['file'] = None
                            if path and path.is_file():
                                item['file'] = f'arquivos/curriculo-{row["id"]}.pdf'
                                archive.write(path,item['file'])
                            else:
                                item['file_status'] = 'Arquivo não disponível no servidor.'
                        output['resumes'].append(item)
                    archive.writestr('dados.json',json.dumps(output,ensure_ascii=False,indent=2))
            stream.seek(0)
            response = send_file(stream,mimetype='application/zip',as_attachment=True,download_name='meus-dados.zip')
            response.call_on_close(stream.close)
            return response
        except Exception:
            stream.close()
            raise

    @bp.post('/delete')
    @protected
    def delete():
        data = input_data()
        if value(data,'confirmation',20) != 'EXCLUIR':
            raise AccountError('Digite EXCLUIR para confirmar.')
        user_id = site.current_user_id()
        try:
            pending = remove_records(site.db_connection,site.UPLOAD_DIR,user_id=user_id,require_deactivated=False,
                                     authorize=lambda db:password_check(db,data))
        except AccountError:
            raise
        except ValueError as exc:
            raise AccountError(str(exc)) from None
        session.clear()
        message = 'Sua conta foi excluída.'
        if pending:
            message += ' Alguns arquivos temporários precisam de limpeza pelo responsável. Entre em contato pelo canal de privacidade.'
        return jsonify(message=message, cleanup_pending=bool(pending))

    app.register_blueprint(bp)
