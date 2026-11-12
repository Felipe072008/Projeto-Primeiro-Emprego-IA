import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from adaptador_jooble import convert_job
from catalogo_oportunidades import detect_areas, normalized


class JoobleTests(unittest.TestCase):
    def test_exact_identifier_and_location(self):
        row = {'id': 8863316138076319222, 'title': 'Jovem Aprendiz em Informática',
               'snippet': 'Ensino médio completo.', 'location': 'Curitiba, PR',
               'link': 'https://br.jooble.org/jdp/8863316138076319222'}
        now = datetime.now(ZoneInfo('America/Sao_Paulo'))
        result = convert_job(row, now, detect_areas, normalized)
        self.assertEqual(result['source_item_id'], '8863316138076319222')
        self.assertIsNone(convert_job(dict(row, title='Jovem Aprendiz Joinville'), now, detect_areas, normalized))
        self.assertIsNone(convert_job(dict(row, snippet=''), now, detect_areas, normalized))
