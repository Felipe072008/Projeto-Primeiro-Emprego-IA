"""Seleciona vagas e cursos revisados conforme as áreas de interesse do perfil."""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from sincronizacao_catalogo import read_state, public_sources

DATA_DIR = Path(__file__).resolve().parent / "data"
CAREER_OPTIONS = Path(__file__).resolve().parent / "static" / "areas_profissionais.json"
AREAS = {
    "tecnologia": ("Tecnologia", ("tecnologia", "informatica", "sistemas", "programacao", "desenvolvimento", "desenvolvedor", "software", "ti", "python", "dados", "computacao", "programador", "suporte tecnico")),
    "administracao": ("Administração", ("administracao", "administrativo", "administrativa", "escritorio", "secretariado", "gestao empresarial", "adm")),
    "financeiro": ("Finanças e contabilidade", ("financeiro", "financeira", "financas", "contabilidade", "contabil", "economia", "fiscal")),
    "comercial": ("Comércio e atendimento", ("vendas", "vendedor", "comercio", "comercial", "atendimento", "recepcao", "caixa", "varejo", "cliente")),
    "marketing": ("Marketing e Comunicação", ("marketing", "design", "publicidade", "comunicacao", "social media", "midias", "audiovisual")),
    "logistica": ("Logística", ("logistica", "estoque", "almoxarifado", "expedicao", "transportes", "transporte", "suprimentos")),
    "rh": ("Recursos humanos", ("recursos humanos", "rh", "recrutamento", "gestao de pessoas", "departamento pessoal")),
    "industria": ("Indústria e Engenharia", ("industria", "industrial", "mecanica", "eletrica", "eletrotecnica", "manutencao", "producao", "automacao", "engenharia")),
    "saude": ("Saúde", ("saude", "enfermagem", "farmacia", "farmaceutico", "biomedicina", "nutricao", "clinica", "hospital")),
    "educacao": ("Educação e Pedagogia", ("educacao", "pedagogia", "escolar", "escola", "auxiliar de sala")),
}
RELATED = {
    "tecnologia": {"marketing", "industria"},
    "administracao": {"financeiro", "rh", "logistica", "comercial"},
    "financeiro": {"administracao"},
    "comercial": {"administracao", "marketing"},
    "marketing": {"comercial", "tecnologia"},
    "logistica": {"administracao", "industria"},
    "rh": {"administracao"},
    "industria": {"tecnologia", "logistica"},
    "saude": set(),
    "educacao": set(),
}


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value).lower()) if not unicodedata.combining(c))


def career_selection(value):
    """Resolve the curated label before aliases (e.g. clinical reception)."""
    key = normalized(value).strip()
    options = json.loads(CAREER_OPTIONS.read_text(encoding="utf-8"))["occupations"]
    return next((option for option in options if normalized(option["title"]) == key), None)


def detect_areas(value):
    selection = career_selection(value)
    if selection:
        return set(selection["areas"])
    value = normalized(value)
    return {key for key, (_, aliases) in AREAS.items() if any(re.search(r"\b" + re.escape(alias) + r"\b", value) for alias in aliases)}


def valid_record(row, kind, today, *, check_dates=True):
    """Validação comum à leitura e à importação; não corrige dados inválidos por suposição."""
    if kind not in {'jobs', 'courses'} or not isinstance(row, dict):
        return False
    try:
        url = urlparse(row.get('original_url', ''))
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.path in {'', '/'} or url.port not in {None, 443}):
            return False
        checked = date.fromisoformat(row['checked_on'])
        review = date.fromisoformat(row['review_by'])
        expires = date.fromisoformat(row['expires_on']) if row.get('expires_on') else review
        if checked > review or (check_dates and (checked > today or min(review, expires) < today)):
            return False
    except (ValueError, KeyError, TypeError, AttributeError):
        return False
    if row.get('status') != 'published':
        return False
    if not all(isinstance(row.get(k), str) and row[k].strip() for k in ('id', 'title', 'source', 'description')):
        return False
    if kind == 'jobs' and (row.get('city') != 'Curitiba' or row.get('state') != 'PR'
            or row.get('entry_level') is not True or row.get('contract_type') not in {'aprendiz', 'estagio', 'clt'}):
        return False
    if kind == 'courses' and not row.get('certificate'):
        return False
    areas = row.get('areas')
    if not isinstance(areas, list) or not areas or any(not isinstance(a, str) or a not in AREAS for a in areas):
        return False
    return True


def canonical_url(value):
    url = urlparse(value)
    query = [(k, v) for k, v in parse_qsl(url.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'fbclid', 'gclid', 'jobboardsource'}]
    return urlunparse((url.scheme, url.netloc.lower(), url.path.rstrip('/'), '', urlencode(sorted(query)), ''))


def catalog_records(kind):
    if kind not in {'jobs', 'courses'}:
        raise ValueError('Tipo de catálogo inválido.')
    path = DATA_DIR / f'{kind}.json'
    manual = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    imported, runs = read_state(kind)
    return imported + manual, runs


def enrich_record(row, kind):
    row = dict(row)
    row.setdefault('source_id', 'manual')
    row.setdefault('source_item_id', row['id'])
    row.setdefault('verification_method', 'manual')
    # O acervo antigo só registrava o dia: não inventar hora nem uma nova confirmação.
    row.setdefault('last_verified_at', None)
    row.setdefault('availability_status', 'unknown')
    row.setdefault('closed_at', None)
    if kind == 'courses':
        row.setdefault('enrollment_status', 'unknown')
        row.setdefault('access_status', 'free_full' if row.get('free') is True else 'unknown')
        row.setdefault('certificate_status', 'free' if normalized(row.get('certificate_cost', '')) == 'gratuito' else 'unknown')
        row.setdefault('duration_hours', None)
    return row


def select_valid(records, kind, today):
    result, seen = [], set()
    # Um encerramento importado não pode reaparecer pela cópia do acervo manual.
    for row in records:
        if isinstance(row, dict) and row.get('verification_method') == 'sync' and row.get('status') == 'closed':
            if valid_record(dict(row, status='published'), kind, today, check_dates=False):
                seen.add(canonical_url(row['original_url']))
    for row in records:
        if not valid_record(row, kind, today):
            continue
        key = canonical_url(row['original_url'])
        if key not in seen:
            seen.add(key)
            result.append(enrich_record(row, kind))
    return result


# Os dados anteriores permanecem em disco; os prazos continuam limitando a exibição.
def load_catalog(kind, today=None):
    records, _ = catalog_records(kind)
    return select_valid(records, kind, today or date.today())


def recommendations(kind, profile, *, show_all=False, query="", course_type="", free_only=False, certificate_free=False, today=None):
    goals = profile.get('sections', {}).get('goals', {})
    interest = str(goals.get('sector') or profile.get("desired_area", "")).strip()
    direct = detect_areas(interest)
    selection = career_selection(interest)
    contract_type = selection["contract_type"] if selection else None
    goals = profile.get('sections', {}).get('goals', {})
    secondary_choices = goals.get('secondary_areas', [])
    secondary = set().union(*(detect_areas(value) for value in secondary_choices)) - direct
    all_areas = direct | secondary
    inferred = {option['contract_type'] for value in [interest, *secondary_choices] if (option := career_selection(value))}
    contracts = set(goals.get('contracts', [])) or inferred
    related = set().union(*(RELATED.get(area, set()) for area in all_areas)) - all_areas if all_areas else set()
    rows = []
    today = today or date.today()
    records, runs = catalog_records(kind)
    available = select_valid(records, kind, today)
    study_context = normalized(' '.join(str(profile.get(k, '')) for k in ('skills', 'objective')) + ' ' + goals.get('target_role', ''))
    for item in available:
        if kind == "jobs" and not show_all and contracts and item["contract_type"] not in contracts:
            continue
        areas = set(item["areas"])
        if direct & areas:
            match, priority = "direct", 0
            reason = "Na sua área de interesse: " + ", ".join(AREAS[a][0] for a in sorted(direct & areas)) + "."
        elif secondary & areas:
            match, priority = 'direct', 1
            reason = 'Em uma das suas áreas adicionais: ' + ', '.join(AREAS[a][0] for a in sorted(secondary & areas)) + '.'
        elif related & areas:
            match, priority = "related", 2
            reason = "Área correlata a " + ", ".join(AREAS[a][0] for a in sorted(direct)) + ". Confira os requisitos."
        else:
            match, priority = "explore", 3
            reason = "Explore esta oportunidade e confira os requisitos."
        if kind == 'courses' and match == 'related':
            match, priority = 'explore', 3
            reason = 'Outra área de estudo; confira se atende ao seu objetivo.'
        terms = []
        if kind == 'courses':
            content = normalized(item['title'] + ' ' + item['description'])
            terms = [term for term in ('python','excel','hardware','redes','atendimento','contabilidade','logistica','marketing','recrutamento') if re.search(r'\b'+term+r'\b', study_context) and re.search(r'\b'+term+r'\b', content)]
            if terms:
                match, priority = 'direct', 0
                reason = 'Conteúdo sobre ' + ', '.join(terms) + ', presente nas suas habilidades, cargo-alvo ou objetivo.'
        if kind == 'courses' and 'suporte' in normalized(interest + ' ' + goals.get('target_role', '')):
            useful = any(term in normalized(item['title'] + ' ' + item['description']) for term in ('hardware', 'redes de computadores', 'suporte', 'sistemas operacionais'))
            if not useful and not terms:
                match, priority, reason = 'explore', 3, 'Explore este conteúdo se fizer parte do seu plano de estudo.'
            elif useful:
                reason = 'Fundamentos de computadores e sistemas úteis para iniciar em suporte de TI.'
        if interest and not show_all and match == "explore":
            continue
        if query and normalized(query) not in normalized(" ".join(str(item.get(k, "")) for k in ("title", "company", "institution", "description"))):
            continue
        if kind == "courses" and ((course_type and item.get("course_type") != course_type) or (free_only and not item.get("free"))):
            continue
        if kind == 'courses' and certificate_free and item.get('certificate_status') != 'free':
            continue
        item.update(match=match, match_reason=reason, area_labels=[AREAS[a][0] for a in item["areas"]])
        rows.append((priority, item))
    rows.sort(key=lambda pair: (pair[0], -(date.fromisoformat(pair[1]["checked_on"]).toordinal()), pair[1]["title"]))
    source_states = public_sources(kind, runs)
    expired = sum(valid_record(row, kind, today, check_dates=False)
                  and row['checked_on'] <= today.isoformat()
                  and min(row['review_by'], row.get('expires_on') or row['review_by']) < today.isoformat()
                  for row in records)
    return {
        "schema_version": 2,
        "data_status": 'fresh' if available else ('stale' if expired else 'unavailable'),
        "result_status": 'results' if rows else ('no_matches' if available else 'no_data'),
        "stale_count": expired,
        "sources": source_states,
        "external_links": [{"source_id": s['id'], "name": s['name'], "url": s['official_url'],
                            "classification": s['classification'], "note": s['reason']}
                           for s in source_states if s['classification'] != 'verified_sync' and s['official_url']],
        kind: [item for _, item in rows],
        "interest": interest,
        "recognized_areas": [AREAS[a][0] for a in sorted(all_areas)],
        "contract_type": contract_type if kind == "jobs" else None,
        "contract_types": sorted(contracts) if kind == 'jobs' else [],
        "personalized": bool(interest) and not show_all,
        "total": len(rows),
        "catalog_total": len(available),
        "catalog_status": 'available' if available else 'unavailable',
        "location": "Curitiba - PR" if kind == "jobs" else "Curitiba e opções online",
        "notice": ("Vagas filtradas também pelos tipos de oportunidade escolhidos. " if kind == "jobs" and contracts and not show_all else "") + "Datas refletem a última verificação válida, não uma tentativa de atualização. Confira disponibilidade e condições na fonte antes de se inscrever.",
    }
