import copy
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import app
import sincronizacao_catalogo as sync
from adaptador_jooble import convert_job
from catalogo_oportunidades import detect_areas, normalized


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        env = patch.dict(os.environ, {'CATALOG_SYNC_TOKEN': 'test-only-token',
                         'FIRST_JOB_CATALOG_DATABASE': str(Path(folder.name) / 'catalog.db')})
        env.start()
        self.addCleanup(env.stop)
        self.client = app.app.test_client()
        self.headers = {'X-Requested-With': 'FirstJob', 'Authorization': 'Bearer test-only-token'}
        now = datetime.now(sync.BRAZIL_TZ)
        row = convert_job({'id': 123, 'title': 'Aprendiz em Informática',
                           'snippet': 'Ensino médio completo. Benefícios: vale-transporte.',
                           'location': 'Curitiba, PR', 'link': 'https://br.jooble.org/jdp/123'},
                          now, detect_areas, normalized)
        self.payload = {'collected_at': now.isoformat(), 'snapshot': {
            'items': [row], 'total': 1, 'complete': True, 'close_missing': False}}

    def send(self, payload=None, headers=None):
        return self.client.post('/api/catalogo/sync', json=payload or self.payload,
                                headers=self.headers if headers is None else headers)

    def test_auth_and_atomic_delivery(self):
        self.assertEqual(self.send(headers={'X-Requested-With': 'FirstJob'}).status_code, 401)
        self.assertFalse(sync.database_path().exists())
        response = self.send()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['imported_count'], 1)
        self.assertEqual(self.send().json['sync_status'], 'skipped')
        rows, runs = sync.read_state('jobs')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['areas'], ['tecnologia'])
        bad = copy.deepcopy(self.payload)
        bad['collected_at'] = (datetime.now(sync.BRAZIL_TZ) - timedelta(seconds=1)).isoformat()
        bad['snapshot']['total'] = 2
        # A newer invalid delivery must roll back, not mask the last success.
        with patch('sincronizacao_catalogo.datetime') as clock:
            clock.now.return_value = datetime.now(sync.BRAZIL_TZ) + timedelta(seconds=3)
            clock.fromisoformat.side_effect = datetime.fromisoformat
            bad['collected_at'] = (datetime.now(sync.BRAZIL_TZ) + timedelta(seconds=1)).isoformat()
            self.assertEqual(self.send(bad).status_code, 400)
        self.assertEqual(sync.read_state('jobs'), (rows, runs))

    def test_stale_invalid_and_cross_origin(self):
        bad = copy.deepcopy(self.payload)
        bad['collected_at'] = (datetime.now(sync.BRAZIL_TZ) - timedelta(hours=1)).isoformat()
        self.assertEqual(self.send(bad).status_code, 400)
        self.assertEqual(self.send(headers={**self.headers, 'Origin': 'https://example.org'}).status_code, 403)
        self.assertEqual(self.client.post('/api/catalogo/sync', json=[], headers=self.headers).status_code, 400)
        bad = copy.deepcopy(self.payload)
        bad['snapshot']['items'][0]['original_url'] = 'https://example.org/job'
        self.assertEqual(self.send(bad).status_code, 400)
