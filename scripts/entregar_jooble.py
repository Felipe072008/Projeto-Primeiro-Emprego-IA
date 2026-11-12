"""Coleta, valida e entrega; nunca registra credenciais ou conteúdo das vagas."""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adaptador_jooble import fetch_jobs, NoRedirect
from sincronizacao_catalogo import BRAZIL_TZ, ImportFailure, validate_snapshot
from fontes_catalogo import source_by_id


def main():
    token = os.environ.get('CATALOG_SYNC_TOKEN', '')
    if not token:
        raise ImportFailure('missing_credential', 'Configure CATALOG_SYNC_TOKEN.')
    snapshot = fetch_jobs()
    collected = datetime.now(BRAZIL_TZ)
    validate_snapshot(source_by_id('jooble'), snapshot, collected)
    payload = {'collected_at': collected.isoformat(), 'snapshot': snapshot}
    req = Request('https://PrimeiroEmpregoIA.pythonanywhere.com/api/catalogo/sync',
                  data=json.dumps(payload, ensure_ascii=False).encode(),
                  headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
                           'X-Requested-With': 'FirstJob'}, method='POST')
    try:
        with build_opener(NoRedirect).open(req, timeout=60) as response:
            receipt = json.load(response)
    except HTTPError as exc:
        raise ImportFailure('delivery_http_error', f'Hospedagem respondeu HTTP {exc.code}.') from None
    except (URLError, TimeoutError, ValueError):
        raise ImportFailure('delivery_error', 'Falha de rede ou recibo inválido.') from None
    if (not isinstance(receipt, dict) or receipt.get('sync_status') != 'success'
            or receipt.get('imported_count') != snapshot['total']
            or receipt.get('collected_at') != payload['collected_at']):
        raise ImportFailure('invalid_receipt', 'A hospedagem não confirmou este lote.')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except ImportFailure as exc:
        print(json.dumps({'error': exc.code, 'message': str(exc)}, ensure_ascii=False))
        sys.exit(1)
