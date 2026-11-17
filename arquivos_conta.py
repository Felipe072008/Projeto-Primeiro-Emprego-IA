"""Exclusão transacional de registros e arquivos, sem acesso ao banco administrativo."""
from pathlib import Path
import secrets

def file_path(upload_dir, name):
    if not name:
        return None
    root = upload_dir.resolve()
    candidate = root / name
    if Path(name).name != name or candidate.is_symlink() or candidate.resolve().parent != root:
        raise ValueError('Caminho de arquivo inválido; exclusão interrompida.')
    return candidate

def remove_records(db_connection, upload_dir, user_id=None, resume_id=None, require_deactivated=True, authorize=None):
    staged = []
    try:
        with db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if authorize:
                authorize(db)
            if user_id is not None:
                user = db.execute('SELECT status FROM users WHERE id=?', (user_id,)).fetchone()
                if not user or (require_deactivated and user[0] != 'deactivated'):
                    raise ValueError('Desative a conta antes de apagar definitivamente.')
                for table in ('profiles', 'profile_sections', 'resumes', 'terms_acceptances'):
                    if not any(r[2] == 'users' and r[6] == 'CASCADE' for r in db.execute(f'PRAGMA foreign_key_list({table})')):
                        raise ValueError('A exclusão foi interrompida: confira as chaves estrangeiras.')
                rows = db.execute('SELECT id,saved_name FROM resumes WHERE user_id=?', (user_id,)).fetchall()
            else:
                rows = db.execute('SELECT id,saved_name FROM resumes WHERE id=?', (resume_id,)).fetchall()
                if not rows:
                    raise ValueError('Currículo não encontrado.')
            for row in rows:
                path = file_path(upload_dir, row['saved_name'])
                if path and path.exists():
                    temporary = path.with_name('.admin-delete-' + secrets.token_hex(16))
                    path.rename(temporary)
                    staged.append((path, temporary))
            if user_id is not None:
                db.execute('DELETE FROM users WHERE id=?', (user_id,))
            else:
                db.execute('DELETE FROM resumes WHERE id=?', (resume_id,))
    except Exception:
        for path, temporary in reversed(staged):
            temporary.rename(path)
        raise
    pending = 0
    for _path, temporary in staged:
        try:
            temporary.unlink()
        except OSError:
            pending += 1
    return pending
