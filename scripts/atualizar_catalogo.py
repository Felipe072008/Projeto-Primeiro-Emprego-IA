"""Comando manual/agendável; não inicia Flask e não acessa perfis ou currículos."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fontes_catalogo import sources
from sincronizacao_catalogo import ADAPTERS, update_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['all', 'jobs', 'courses'], default='all')
    parser.add_argument('--source', choices=[s['id'] for s in sources()])
    parser.add_argument('--due', action='store_true', help='Executa no máximo uma tentativa por ciclo de Brasília.')
    parser.add_argument('--diagnose', action='store_true', help='Lista a configuração das fontes, sem importar ofertas.')
    args = parser.parse_args()
    if args.diagnose:
        selected = sources(None if args.kind == 'all' else args.kind)
        result = [{'source_id': row['id'], 'classification': row['classification'],
                   'adapter_enabled': row['classification'] == 'verified_sync' and row['id'] in ADAPTERS,
                   'message': row['reason']} for row in selected if not args.source or row['id'] == args.source]
        print(json.dumps({'mode': 'configuration_diagnostic', 'import_performed': False, 'sources': result},
                         ensure_ascii=False, indent=2))
        return 0
    result = update_catalog(args.kind, source_id=args.source, due=args.due)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(any(row['sync_status'] not in {'success', 'skipped'} for row in result))


if __name__ == '__main__':
    sys.exit(main())
