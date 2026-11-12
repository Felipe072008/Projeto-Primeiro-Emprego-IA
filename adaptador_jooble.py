"""Consulta limitada à API brasileira; chave somente no ambiente."""
import html
import json
import os
import re
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zoneinfo import ZoneInfo


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_jobs():
    from sincronizacao_catalogo import ImportFailure
    from catalogo_oportunidades import detect_areas, normalized
    key = os.environ.get('JOOBLE_API_KEY', '').strip()
    if not key:
        raise ImportFailure('missing_credential', 'Configure JOOBLE_API_KEY.')
    now = datetime.now(ZoneInfo('America/Sao_Paulo'))
    accepted = {}
    for query in ('jovem aprendiz', 'estágio', 'sem experiência CLT'):
        request = Request('https://br.jooble.org/api/' + key,
                          data=json.dumps({'keywords': query, 'location': 'Curitiba', 'radius': '0', 'page': 1}).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with build_opener(NoRedirect).open(request, timeout=25) as response:
                content = response.read(2_000_001)
                if len(content) > 2_000_000:
                    raise ImportFailure('response_too_large', 'Resposta Jooble excedeu o limite.')
                data = json.loads(content)
        except HTTPError as exc:
            raise ImportFailure('jooble_http_error', f'Jooble respondeu HTTP {exc.code}.') from None
        except (URLError, TimeoutError, ValueError):
            raise ImportFailure('jooble_response_error', 'Falha de rede ou resposta inválida do Jooble.') from None
        if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
            raise ImportFailure('invalid_schema', 'Formato Jooble inesperado.')
        for item in data['jobs']:
            row = convert_job(item, now, detect_areas, normalized)
            if row:
                accepted[row['source_item_id']] = row
    # shortcut: primeira página por consulta; ampliar paginação ao avaliar cobertura e quota.
    return {'items': list(accepted.values()), 'total': len(accepted), 'complete': True,
            'close_missing': False, 'empty_confirmed': True}


def convert_job(item, now, detect_areas, normalized):
    from sincronizacao_catalogo import ImportFailure
    if not isinstance(item, dict):
        raise ImportFailure('invalid_schema', 'Registro Jooble inválido.')
    if any(not isinstance(item.get(field, ''), str) for field in ('title', 'snippet', 'location', 'link', 'company')):
        raise ImportFailure('invalid_schema', 'Campos Jooble inesperados.')
    title = item.get('title', '')
    snippet = html.unescape(re.sub('<[^>]+>', '', item.get('snippet', ''))).replace('\\r\\n', ' ')
    text = normalized(title + ' ' + snippet)
    if item.get('location') != 'Curitiba, PR' or not title:
        return None
    if any(word in text for word in ('banco de talentos', 'cadastro reserva', 'joinville', 'sao jose dos pinhais', 'colombo', 'pinhais')):
        return None
    title_key = normalized(title)
    if 'aprendiz' in title_key:
        contract = 'aprendiz'
    elif 'estagio' in title_key or 'estagiario' in title_key:
        contract = 'estagio'
    elif 'clt' in text and ('sem experiencia' in text or 'nao e necessario experiencia' in text):
        contract = 'clt'
    else:
        return None
    # Benefícios como vale-transporte não são evidência da área profissional.
    duties = re.split(r'beneficios|vale[- ]transporte|oferecemos', normalized(snippet))[0]
    areas = sorted(detect_areas(title) or detect_areas(duties))
    requirements = re.search(r'(?:ensino (?:medio|fundamental|superior)(?: completo| incompleto| cursando)?|cursando[^.;\n]{1,100}|nao e necessario ter conhecimento previo)', text)
    link = item.get('link', '')
    if not areas or not requirements or not re.fullmatch(r'https://br\.jooble\.org/jdp/-?\d+', link):
        return None
    if type(item.get('id')) is not int or str(item['id']) != link.rsplit('/', 1)[-1]:
        raise ImportFailure('invalid_identity', 'Identificador Jooble inconsistente.')
    return {'source_item_id': str(item['id']), 'title': title, 'original_url': link,
            'description': snippet, 'company': item.get('company') or 'Empresa não informada',
            'areas': areas, 'city': 'Curitiba', 'state': 'PR', 'entry_level': True,
            'contract_type': contract, 'requirements': [requirements.group(0)],
            'requirements_evidence': requirements.group(0), 'is_individual': True,
            'availability_status': 'open', 'availability_evidence': 'Oferta retornada pela API Jooble Brasil.',
            'review_by': (now.date() + timedelta(days=1)).isoformat(), 'expires_on': None}
