"""Curated public opportunities with explicit provenance and interest matching."""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(__file__).resolve().parent / "data"
AREAS = {
    "tecnologia": ("Tecnologia", ("tecnologia", "informatica", "sistemas", "programacao", "desenvolvimento", "desenvolvedor", "software", "ti", "python", "dados", "computacao", "programador", "suporte tecnico")),
    "administracao": ("Administração", ("administracao", "administrativo", "administrativa", "escritorio", "secretariado", "gestao empresarial", "adm")),
    "financeiro": ("Finanças e contabilidade", ("financeiro", "financeira", "financas", "contabilidade", "contabil", "economia", "fiscal")),
    "comercial": ("Comércio e atendimento", ("vendas", "vendedor", "comercio", "comercial", "atendimento", "recepcao", "caixa", "varejo", "cliente")),
    "marketing": ("Marketing e design", ("marketing", "design", "publicidade", "comunicacao social", "social media", "midias", "audiovisual")),
    "logistica": ("Logística", ("logistica", "estoque", "almoxarifado", "expedicao", "transportes", "transporte", "suprimentos")),
    "rh": ("Recursos humanos", ("recursos humanos", "rh", "recrutamento", "gestao de pessoas", "departamento pessoal")),
    "industria": ("Indústria e manutenção", ("industria", "industrial", "mecanica", "eletrica", "eletrotecnica", "manutencao", "producao", "automacao", "engenharia")),
    "saude": ("Saúde", ("saude", "enfermagem", "farmacia", "farmaceutico", "biomedicina", "nutricao")),
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
}


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value).lower()) if not unicodedata.combining(c))


def detect_areas(value):
    value = normalized(value)
    return {key for key, (_, aliases) in AREAS.items() if any(re.search(r"\b" + re.escape(alias) + r"\b", value) for alias in aliases)}


def load_catalog(kind, today=None):
    today = today or date.today()
    path = DATA_DIR / f"{kind}.json"
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    valid = []
    for row in records:
        url = urlparse(row.get("original_url", ""))
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.path in {"", "/"}:
            continue
        if row.get("status") != "published":
            continue
        try:
            checked = date.fromisoformat(row["checked_on"])
            review_due = date.fromisoformat(row["review_by"])
            expires = date.fromisoformat(row["expires_on"]) if row.get("expires_on") else review_due
        except (ValueError, KeyError):
            continue
        if checked > today or min(review_due, expires) < today:
            continue
        if kind == "jobs" and (row.get("city") != "Curitiba" or row.get("state") != "PR"):
            continue
        if not row.get("areas") or any(area not in AREAS for area in row["areas"]):
            continue
        valid.append(dict(row))
    return valid


def recommendations(kind, profile, *, show_all=False, query="", course_type="", free_only=False, today=None):
    interest = str(profile.get("desired_area", "")).strip()
    direct = detect_areas(interest)
    related = set().union(*(RELATED.get(area, set()) for area in direct)) - direct if direct else set()
    rows = []
    for item in load_catalog(kind, today):
        areas = set(item["areas"])
        if direct & areas:
            match, priority = "direct", 0
            reason = "Na sua área de interesse: " + ", ".join(AREAS[a][0] for a in sorted(direct & areas)) + "."
        elif related & areas:
            match, priority = "related", 1
            reason = "Área correlata a " + ", ".join(AREAS[a][0] for a in sorted(direct)) + ". Confira os requisitos."
        else:
            match, priority = "explore", 2
            reason = "Explore esta oportunidade e confira os requisitos."
        if interest and not show_all and match == "explore":
            continue
        if query and normalized(query) not in normalized(" ".join(str(item.get(k, "")) for k in ("title", "company", "institution", "description"))):
            continue
        if kind == "courses" and ((course_type and item.get("course_type") != course_type) or (free_only and not item.get("free"))):
            continue
        item.update(match=match, match_reason=reason, area_labels=[AREAS[a][0] for a in item["areas"]])
        rows.append((priority, item))
    rows.sort(key=lambda pair: (pair[0], -(date.fromisoformat(pair[1]["checked_on"]).toordinal()), pair[1]["title"]))
    return {
        kind: [item for _, item in rows],
        "interest": interest,
        "recognized_areas": [AREAS[a][0] for a in sorted(direct)],
        "personalized": bool(interest) and not show_all,
        "total": len(rows),
        "location": "Curitiba - PR" if kind == "jobs" else "Curitiba e opções online",
        "notice": "Os resumos foram preparados a partir das páginas originais. A disponibilidade e as condições podem mudar na fonte.",
    }
