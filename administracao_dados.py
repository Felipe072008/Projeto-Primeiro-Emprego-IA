"""Migrações aditivas e controles do catálogo, sem acesso ao banco administrativo."""
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def main_path():
    return Path(os.environ.get('FIRST_JOB_DATABASE', BASE_DIR / 'primeiro_emprego.db')).resolve()


def migrate(db):
    columns = {
        'users': {'status': "TEXT NOT NULL DEFAULT 'active'", 'deactivated_at': 'TEXT', 'last_login_at': 'TEXT', 'session_version': 'INTEGER NOT NULL DEFAULT 0'},
        'jobs': {'is_hidden': 'INTEGER NOT NULL DEFAULT 0', 'is_removed': 'INTEGER NOT NULL DEFAULT 0',
                 'removed_at': 'TEXT', 'catalog_source': "TEXT NOT NULL DEFAULT 'manual'",
                 'external_key': 'TEXT', 'payload': 'TEXT', 'is_override': 'INTEGER NOT NULL DEFAULT 0'},
    }
    db.execute('''CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY, external_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
        is_hidden INTEGER NOT NULL DEFAULT 0, is_removed INTEGER NOT NULL DEFAULT 0,
        removed_at TEXT, source TEXT NOT NULL DEFAULT 'manual', is_override INTEGER NOT NULL DEFAULT 0)''')
    for table, additions in columns.items():
        existing = {row[1] for row in db.execute(f'PRAGMA table_info({table})')}
        for name, declaration in additions.items():
            if name not in existing:
                db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {declaration}')
    db.execute('CREATE UNIQUE INDEX IF NOT EXISTS jobs_external_key ON jobs(external_key)')
    for kind in ('jobs', 'courses'):
        path = BASE_DIR / 'data' / (kind + '.json')
        if path.exists():
            mirror(db, kind, json.loads(path.read_text(encoding='utf-8')))


def mirror(db, kind, records):
    from catalogo_oportunidades import canonical_url
    aliases = {canonical_url(json.loads(row['payload'])['original_url']):row['external_key']
               for row in db.execute(f'SELECT external_key,payload FROM {kind} WHERE is_override=1 AND payload IS NOT NULL')}
    for row in records:
        if not isinstance(row, dict) or not row.get('original_url'):
            continue
        url_key = canonical_url(row['original_url'])
        key = aliases.get(url_key, url_key)
        source = 'auto' if row.get('verification_method') == 'sync' else 'manual'
        payload = json.dumps(row, ensure_ascii=False)
        if kind == 'courses':
            db.execute('''INSERT INTO courses (external_key,payload,source) VALUES (?,?,?)
                ON CONFLICT(external_key) DO UPDATE SET payload=excluded.payload,source=excluded.source
                WHERE courses.is_override=0''', (key, payload, source))
        else:
            db.execute('''INSERT INTO jobs (external_key,payload,title,company,location,description,
                requirements,source,original_url,catalog_source) VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(external_key) DO UPDATE SET payload=excluded.payload,catalog_source=excluded.catalog_source
                WHERE jobs.is_override=0''', (key, payload, row.get('title',''), row.get('company',''),
                row.get('location',''), row.get('description',''), json.dumps(row.get('requirements', [])),
                row.get('source',''), row['original_url'], source))


def apply_controls(kind, records):
    """Uma nova importação nunca remove as decisões do administrador sobre a URL."""
    from catalogo_oportunidades import canonical_url
    path = main_path()
    if not path.exists():
        return records
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (kind,)).fetchone():
            return records
        if 'external_key' not in {r[1] for r in db.execute(f'PRAGMA table_info({kind})')}:
            return records
        controls = {r['external_key']: dict(r) for r in db.execute(f'SELECT * FROM {kind} WHERE external_key IS NOT NULL')}
    for control in list(controls.values()):
        if control['payload']:
            controls.setdefault(canonical_url(json.loads(control['payload'])['original_url']), control)
    result, used = [], set()
    for row in records:
        key = canonical_url(row.get('original_url','')) if isinstance(row, dict) else ''
        control = controls.get(key)
        if control and (control['is_hidden'] or control['is_removed']):
            continue
        if control and control['is_override']:
            identity = control['external_key']
            if identity not in used:
                result.append(json.loads(control['payload']))
                used.add(identity)
        else:
            result.append(row)
    for control in controls.values():
        identity = control['external_key']
        if identity not in used and control['is_override'] and not control['is_hidden'] and not control['is_removed']:
            result.append(json.loads(control['payload']))
            used.add(identity)
    return result
