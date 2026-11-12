import unittest
import os
from unittest.mock import patch
from urllib.error import HTTPError
from datetime import datetime
from zoneinfo import ZoneInfo
from adaptador_jooble import convert_job, fetch_jobs
from sincronizacao_catalogo import ImportFailure
from catalogo_oportunidades import detect_areas, normalized


class JoobleTests(unittest.TestCase):
    def test_api_error_does_not_expose_key(self):
        with patch.dict(os.environ, {'JOOBLE_API_KEY': 'secret-test-key'}), patch('adaptador_jooble.build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError('https://br.jooble.org/api/secret-test-key', 429, 'rate limit', {}, None)
            with self.assertRaises(ImportFailure) as caught:
                fetch_jobs()
        self.assertNotIn('secret-test-key', str(caught.exception))
        self.assertEqual(caught.exception.code, 'jooble_http_error')

    def test_exact_identifier_and_location(self):
        row = {'id': 8863316138076319222, 'title': 'Jovem Aprendiz em Informática',
               'snippet': 'Ensino médio completo.', 'location': 'Curitiba, PR',
               'link': 'https://br.jooble.org/jdp/8863316138076319222'}
        now = datetime.now(ZoneInfo('America/Sao_Paulo'))
        result = convert_job(row, now, detect_areas, normalized)
        self.assertEqual(result['source_item_id'], '8863316138076319222')
        self.assertIsNone(convert_job(dict(row, title='Jovem Aprendiz Joinville'), now, detect_areas, normalized))
        self.assertIsNone(convert_job(dict(row, snippet=''), now, detect_areas, normalized))
