"""Comando manual/agendável; não inicia Flask e não acessa perfis ou currículos."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fontes_catalogo import sources
from sincronizacao_catalogo import update_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['all', 'jobs', 'courses'], default='all')
    parser.add_argument('--source', choices=[s['id'] for s in sources()])
    parser.add_argument('--due', action='store_true', help='Executa no máximo uma tentativa por ciclo de Brasília.')
    parser.add_argument('--probe', action='store_true', help='Diagnostica o CSV público da EV.G sem publicar dados.')
    args = parser.parse_args()
    if args.probe and args.source != 'evg':
        parser.error('--probe exige --source evg')
    result = update_catalog(args.kind, source_id=args.source, due=args.due, probe=args.probe)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(any(row['sync_status'] not in {'success', 'skipped'} for row in result))


if __name__ == '__main__':
    sys.exit(main())
