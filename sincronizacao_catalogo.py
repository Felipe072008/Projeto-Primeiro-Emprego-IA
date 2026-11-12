"""Importação atômica por fonte, sem executar tarefas dentro do servidor Flask."""
import json
import math
import os
import sqlite3
from contextlib import closing
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fontes_catalogo import sources, source_by_id

BRAZIL_TZ = ZoneInfo('America/Sao_Paulo')
DEFAULT_DB = Path(__file__).resolve().parent / 'data' / 'catalogo_sync.db'
# Nenhum adaptador pode publicar antes da confirmação de licença, esquema e evidências.
from adaptador_jooble import fetch_jobs
ADAPTERS = {'jooble': fetch_jobs}


class ImportFailure(ValueError):
    def __init__(self, code, message, status='error'):
        super().__init__(message)
        self.code, self.status = code, status


def database_path():
    return Path(os.environ.get('FIRST_JOB_CATALOG_DATABASE', DEFAULT_DB)).resolve()


def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS catalog_items (
            source_id TEXT NOT NULL, item_id TEXT NOT NULL, kind TEXT NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(source_id, item_id));
        CREATE TABLE IF NOT EXISTS catalog_runs (
            source_id TEXT PRIMARY KEY, last_attempt_at TEXT NOT NULL,
            last_success_at TEXT, sync_status TEXT NOT NULL,
            error_code TEXT, message TEXT NOT NULL, imported_count INTEGER NOT NULL DEFAULT 0);
    ''')
    return connection


def read_state(kind):
    """A leitura das rotas não cria banco nem inicia consultas a sites externos."""
    path = database_path()
    if not path.exists():
        return [], {}
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
        db.row_factory = sqlite3.Row
        records = [json.loads(row['payload']) for row in db.execute(
            'SELECT payload FROM catalog_items WHERE kind=? ORDER BY source_id,item_id', (kind,))]
        runs = {row['source_id']: dict(row) for row in db.execute('SELECT * FROM catalog_runs')}
    return records, runs


def public_sources(kind, runs):
    result = []
    for source in sources(kind):
        run = runs.get(source['id'], {})
        result.append({**source, 'sync_status': run.get('sync_status', 'never'),
                       'last_attempt_at': run.get('last_attempt_at'),
                       'last_success_at': run.get('last_success_at'),
                       'error_code': run.get('error_code'),
                       'message': run.get('message', source['reason']),
                       'imported_count': run.get('imported_count', 0)})
    return result


def schedule_slot(kind, now):
    """Vagas diariamente às 06h; cursos às segundas às 06h30, em Brasília."""
    local = now.astimezone(BRAZIL_TZ)
    day = local.date()
    if kind == 'courses':
        day -= timedelta(days=day.weekday())
    slot = datetime.combine(day, time(6, 30 if kind == 'courses' else 0), BRAZIL_TZ)
    if slot > local:
        slot -= timedelta(days=7 if kind == 'courses' else 1)
    return slot


def validate_snapshot(source, snapshot, now):
    """Rejeita o lote inteiro: uma linha ruim não pode renovar as demais silenciosamente."""
    from catalogo_oportunidades import valid_record, normalized
    if not isinstance(snapshot, dict) or snapshot.get('complete') is not True:
        raise ImportFailure('partial_response', 'Lista parcial; os últimos dados foram preservados.', 'partial')
    rows = snapshot.get('items')
    if not isinstance(rows, list) or type(snapshot.get('total')) is not int or snapshot['total'] != len(rows):
        raise ImportFailure('invalid_total', 'Quantidade ou formato da resposta não confirmado.')
    # Uma lista vazia precisa de evidência explícita do adaptador, não basta HTTP 200.
    if not rows and snapshot.get('empty_confirmed') is not True:
        raise ImportFailure('unconfirmed_empty', 'Lista vazia sem confirmação de completude.')
    result, ids, urls = [], set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ImportFailure('invalid_item', 'Registro inválido na resposta.')
        row = dict(row)
        item_id = row.get('source_item_id')
        if not isinstance(item_id, str) or not item_id.strip() or len(item_id) > 200:
            raise ImportFailure('missing_identity', 'Registro sem identificador estável na fonte.')
        url = row.get('original_url')
        if item_id in ids or url in urls:
            raise ImportFailure('duplicate_item', 'IDs ou links duplicados no lote; revisão necessária.')
        ids.add(item_id)
        urls.add(url)
        if any(not isinstance(row.get(key), str) or not row[key].strip()
               for key in ('title', 'description', 'review_by', 'availability_evidence')):
            raise ImportFailure('missing_evidence', 'Faltam campos obrigatórios ou evidência de disponibilidade.')
        if row.get('availability_status') != 'open' or row.get('is_individual') is not True:
            raise ImportFailure('not_open', 'Não é uma oferta individual comprovadamente aberta.')
        if any(term in normalized(row['title']) for term in ('banco de talentos', 'cadastro reserva')):
            raise ImportFailure('talent_pool', 'Bancos de talentos não entram no catálogo.')
        requirements = row.get('requirements')
        if not isinstance(requirements, list) or any(not isinstance(value, str) for value in requirements):
            raise ImportFailure('invalid_requirements', 'Requisitos devem ser uma lista de textos confirmados.')
        if source['kind'] == 'jobs' and (not requirements or not isinstance(row.get('requirements_evidence'), str)
                                         or not row['requirements_evidence'].strip()):
            raise ImportFailure('missing_requirements', 'A vaga não tem evidência dos requisitos.')
        if source['kind'] == 'courses':
            if (row.get('enrollment_status') != 'open' or row.get('access_status') != 'free_full'
                    or row.get('certificate_status') not in {'free', 'paid', 'unknown'}
                    or not isinstance(row.get('institution'), str) or not row['institution'].strip()
                    or not isinstance(row.get('access_evidence'), str) or not row['access_evidence'].strip()
                    or (row['certificate_status'] != 'unknown' and not row.get('certificate_source'))):
                raise ImportFailure('course_conditions', 'Inscrição, acesso integral ou certificado não confirmados.')
            hours = row.get('duration_hours')
            if hours is not None and (type(hours) not in {int, float} or not math.isfinite(hours) or hours <= 0):
                raise ImportFailure('invalid_duration', 'Carga horária inválida; use null quando não informada.')
            if row.get('free') is False or (normalized(row.get('certificate_cost', '')) == 'gratuito'
                                          and row['certificate_status'] != 'free'):
                raise ImportFailure('conflicting_conditions', 'Condições de acesso/certificado contraditórias.')
            row['free'] = True
            row.setdefault('certificate', {'free': 'Certificado gratuito; confira as condições na fonte.',
                                          'paid': 'Certificado pago; confira as condições na fonte.',
                                          'unknown': 'Condições de certificação não informadas na fonte.'}[row['certificate_status']])
            row.setdefault('certificate_cost', {'free': 'Gratuito', 'paid': 'Pago', 'unknown': 'Não informado'}[row['certificate_status']])
        row.update(id=f"{source['id']}:{item_id}", source_id=source['id'], source=source['name'],
                   status='published', verification_method='sync',
                   checked_on=now.date().isoformat(), last_verified_at=now.isoformat(), closed_at=None)
        if not valid_record(row, source['kind'], now.date()):
            raise ImportFailure('invalid_item', 'Registro fora do recorte, vencido ou com campos inválidos.')
        # A revisão nunca ultrapassa um ciclo; a data é política local, não prazo inventado da oferta.
        limit = now.date() + timedelta(days=1 if source['kind'] == 'jobs' else 7)
        row['review_by'] = min(row['review_by'], limit.isoformat())
        result.append(row)
    return result


def apply_snapshot(db, source, snapshot, now):
    rows = validate_snapshot(source, snapshot, now)
    old = {r['item_id']: json.loads(r['payload']) for r in db.execute(
        'SELECT item_id,payload FROM catalog_items WHERE source_id=?', (source['id'],))}
    current = {r['source_item_id'] for r in rows}
    for item_id, row in old.items():
        if snapshot.get('close_missing', True) and item_id not in current and row.get('status') == 'published':
            row.update(status='closed', availability_status='closed', closed_at=now.isoformat())
            if source['kind'] == 'courses':
                row['enrollment_status'] = 'closed'
            db.execute('UPDATE catalog_items SET payload=? WHERE source_id=? AND item_id=?',
                       (json.dumps(row, ensure_ascii=False), source['id'], item_id))
    for row in rows:
        db.execute('INSERT INTO catalog_items VALUES (?,?,?,?) ON CONFLICT(source_id,item_id) '
                   'DO UPDATE SET payload=excluded.payload,kind=excluded.kind',
                   (source['id'], row['source_item_id'], source['kind'], json.dumps(row, ensure_ascii=False)))
    return len(rows)


def update_source(source_id, *, due=False, now=None):
    now = (now or datetime.now(BRAZIL_TZ)).astimezone(BRAZIL_TZ)
    source = source_by_id(source_id)
    with closing(connect()) as db, db:
        # Serializa execuções concorrentes, inclusive manual + agendador.
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT * FROM catalog_runs WHERE source_id=?', (source_id,)).fetchone()
        if due and previous and datetime.fromisoformat(previous['last_attempt_at']) >= schedule_slot(source['kind'], now):
            return {'source_id': source_id, 'sync_status': 'skipped', 'message': 'Ciclo já tentado.'}
        last_success = previous['last_success_at'] if previous else None
        count = previous['imported_count'] if previous else 0
        db.execute('SAVEPOINT source_update')
        try:
            if source['classification'] != 'verified_sync' or source_id not in ADAPTERS:
                raise ImportFailure('source_pending', source['reason'], 'blocked')
            snapshot = ADAPTERS[source_id]()
            count = apply_snapshot(db, source, snapshot, now)
            last_success, status, code = now.isoformat(), 'success', None
            message = 'Lote validado; ausências preservadas.' if snapshot.get('close_missing') is False else 'Lista completa validada.'
        except Exception as exc:
            db.execute('ROLLBACK TO source_update')
            status = exc.status if isinstance(exc, ImportFailure) else 'error'
            code = exc.code if isinstance(exc, ImportFailure) else 'source_error'
            message = str(exc) if isinstance(exc, ImportFailure) else 'Falha ao consultar ou validar a fonte; dados anteriores preservados.'
        db.execute('RELEASE source_update')
        db.execute('INSERT INTO catalog_runs VALUES (?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET '
                   'last_attempt_at=excluded.last_attempt_at,last_success_at=excluded.last_success_at,'
                   'sync_status=excluded.sync_status,error_code=excluded.error_code,message=excluded.message,'
                   'imported_count=excluded.imported_count',
                   (source_id, now.isoformat(), last_success, status, code, message, count))
        return dict(db.execute('SELECT * FROM catalog_runs WHERE source_id=?', (source_id,)).fetchone())


def update_catalog(kind='all', *, source_id=None, due=False, now=None):
    selected = [source_by_id(source_id)] if source_id else sources(None if kind == 'all' else kind)
    return [update_source(source['id'], due=due, now=now) for source in selected]


def receive_jooble(payload, now=None):
    """Revalida a entrega e grava lote e recibo na mesma transação."""
    now = now or datetime.now(BRAZIL_TZ)
    try:
        collected = datetime.fromisoformat(payload['collected_at'])
        snapshot = payload['snapshot']
        if collected.tzinfo is None or not 0 <= (now - collected).total_seconds() <= 900:
            raise ValueError()
        if snapshot.get('close_missing') is not False or len(snapshot['items']) > 100:
            raise ValueError()
        for row in snapshot['items']:
            if row['original_url'] != 'https://br.jooble.org/jdp/' + row['source_item_id']:
                raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ImportFailure('invalid_delivery', 'Entrega inválida ou fora da janela de 15 minutos.') from None
    source = source_by_id('jooble')
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT * FROM catalog_runs WHERE source_id=?', ('jooble',)).fetchone()
        if previous and previous['last_success_at'] and collected <= datetime.fromisoformat(previous['last_success_at']):
            return {'sync_status': 'skipped', 'imported_count': previous['imported_count'],
                    'collected_at': previous['last_success_at']}
        count = apply_snapshot(db, source, snapshot, collected)
        db.execute('INSERT INTO catalog_runs VALUES (?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET '
                   'last_attempt_at=excluded.last_attempt_at,last_success_at=excluded.last_success_at,'
                   'sync_status=excluded.sync_status,error_code=NULL,message=excluded.message,'
                   'imported_count=excluded.imported_count',
                   ('jooble', now.isoformat(), collected.isoformat(), 'success', None,
                    'Lote recebido do GitHub Actions; ausências preservadas.', count))
    return {'sync_status': 'success', 'imported_count': count, 'collected_at': collected.isoformat()}
