"""Fontes avaliadas: um link público não equivale a permissão de sincronização."""
from pathlib import Path
import json

REGISTRY = Path(__file__).resolve().parent / 'data' / 'fontes_catalogo.json'


def sources(kind=None):
    rows = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return [row for row in rows if kind is None or row['kind'] == kind]


def source_by_id(source_id):
    return next(row for row in sources() if row['id'] == source_id)
