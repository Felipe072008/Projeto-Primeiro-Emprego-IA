"""Contratos e falhas com dados sintéticos: nenhum teste confirma uma fonte real."""
import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import catalogo_oportunidades as catalog
import sincronizacao_catalogo as sync
import test_aplicacao


NOW = datetime(2026, 11, 9, 8, tzinfo=sync.BRAZIL_TZ)
SOURCE = {'id': 'fixture', 'name': 'Fonte sintética de teste', 'kind': 'courses',
          'classification': 'verified_sync', 'reason': 'Somente fixture.',
          'official_url': 'https://example.org/courses'}


def course(item_id='1', **changes):
    row = {'source_item_id': item_id, 'title': 'Curso sintético de tecnologia',
           'original_url': f'https://example.org/course/{item_id}', 'areas': ['tecnologia'],
           'institution': 'Instituição fictícia do teste', 'description': 'Fixture sem oferta real.',
           'duration_hours': 10, 'duration': '10 horas', 'requirements': [],
           'availability_status': 'open', 'availability_evidence': 'Fixture: matrícula aberta.',
           'is_individual': True, 'enrollment_status': 'open', 'access_status': 'free_full',
           'access_evidence': 'Fixture: acesso completo gratuito.', 'certificate_status': 'free',
           'certificate_source': 'https://example.org/course/' + item_id,
           'course_type': 'livre', 'review_by': '2026-11-16', 'expires_on': None}
    return dict(row, **changes)


def snapshot(*rows, **changes):
    return dict({'items': list(rows), 'total': len(rows), 'complete': True}, **changes)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.patch(patch.dict(os.environ, {'FIRST_JOB_CATALOG_DATABASE': str(self.path / 'catalog.db')}))
        self.patch(patch.object(catalog, 'DATA_DIR', self.path))
        self.patch(patch.object(sync, 'source_by_id', return_value=SOURCE))
        self.patch(patch.object(sync, 'sources', return_value=[SOURCE]))

    def patch(self, context):
        value = context.start()
        self.addCleanup(context.stop)
        return value

    def run_source(self, value, now=NOW, **options):
        adapter = lambda: copy.deepcopy(value)
        with patch.dict(sync.ADAPTERS, {'fixture': adapter}, clear=True):
            return sync.update_source('fixture', now=now, **options)

    def test_repeat_updates_one_stable_record(self):
        self.assertEqual(self.run_source(snapshot(course()))['sync_status'], 'success')
        later = NOW + timedelta(hours=1)
        self.run_source(snapshot(course(title='Título revisado')), now=later)
        records, runs = sync.read_state('courses')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], 'fixture:1')
        self.assertEqual(records[0]['title'], 'Título revisado')
        self.assertEqual(runs['fixture']['last_success_at'], later.isoformat())

    def test_complete_absence_closes_without_renewing_verification(self):
        self.run_source(snapshot(course('1'), course('2')))
        self.run_source(snapshot(course('2')), now=NOW + timedelta(hours=1))
        records, _ = sync.read_state('courses')
        closed = next(r for r in records if r['source_item_id'] == '1')
        self.assertEqual(closed['status'], 'closed')
        self.assertEqual(closed['last_verified_at'], NOW.isoformat())
        self.assertEqual([r['source_item_id'] for r in catalog.load_catalog('courses', NOW.date())], ['2'])

    def test_partial_bad_schema_empty_and_network_preserve_last_snapshot(self):
        self.run_source(snapshot(course()))
        before, _ = sync.read_state('courses')
        failures = [snapshot(complete=False), snapshot(), {'items': [], 'complete': True},
                    snapshot(course('2'), course('3', original_url='https://[broken')),
                    snapshot(course(), course()), snapshot(course('2', institution=None))]
        for value in failures:
            with self.subTest(value=value):
                result = self.run_source(value, now=NOW + timedelta(hours=1))
                self.assertIn(result['sync_status'], {'error', 'partial'})
                records, runs = sync.read_state('courses')
                self.assertEqual(records, before)
                self.assertEqual(runs['fixture']['last_success_at'], NOW.isoformat())
                self.assertNotEqual(runs['fixture']['last_attempt_at'], NOW.isoformat())
        with patch.dict(sync.ADAPTERS, {'fixture': lambda: (_ for _ in ()).throw(TimeoutError())}, clear=True):
            result = sync.update_source('fixture', now=NOW + timedelta(days=1))
        self.assertEqual(result['sync_status'], 'error')
        self.assertEqual(sync.read_state('courses')[0], before)

    def test_empty_confirmed_closes_all(self):
        self.run_source(snapshot(course()))
        result = self.run_source(snapshot(empty_confirmed=True), now=NOW + timedelta(days=1))
        self.assertEqual(result['sync_status'], 'success')
        self.assertEqual(catalog.load_catalog('courses', NOW.date()), [])

    def test_paid_certificate_allowed_but_not_free_certificate_filter(self):
        self.run_source(snapshot(course('1', certificate_status='paid'), course('2')))
        all_rows = catalog.recommendations('courses', {}, free_only=True, today=NOW.date())
        self.assertEqual(all_rows['total'], 2)
        only_free = catalog.recommendations('courses', {}, certificate_free=True, today=NOW.date())
        self.assertEqual([r['source_item_id'] for r in only_free['courses']], ['2'])
        self.assertEqual(only_free['result_status'], 'results')

    def test_preview_trial_aid_unknown_access_and_closed_enrollment_rejected(self):
        for access in ('preview', 'trial', 'financial_aid', 'paid', 'unknown'):
            self.assertEqual(self.run_source(snapshot(course(access_status=access)))['sync_status'], 'error')
        self.assertEqual(self.run_source(snapshot(course(enrollment_status='closed')))['sync_status'], 'error')
        self.assertEqual(sync.read_state('courses')[0], [])

    def test_unknown_certificate_allowed_but_excluded_from_free_filter(self):
        self.run_source(snapshot(course(certificate_status='unknown', certificate_source=None)))
        self.assertEqual(catalog.recommendations('courses', {}, today=NOW.date())['total'], 1)
        self.assertEqual(catalog.recommendations('courses', {}, certificate_free=True, today=NOW.date())['total'], 0)

    def test_deadlines_no_matches_and_source_failure_are_distinct(self):
        self.run_source(snapshot(course(expires_on='2026-11-10')))
        unmatched = catalog.recommendations('courses', {}, query='inexistente', today=NOW.date())
        self.assertEqual((unmatched['data_status'], unmatched['result_status']), ('fresh', 'no_matches'))
        stale = catalog.recommendations('courses', {}, today=(NOW + timedelta(days=2)).date())
        self.assertEqual((stale['data_status'], stale['result_status']), ('stale', 'no_data'))
        self.assertEqual(stale['total'], 0)
        self.assertEqual(stale['stale_count'], 1)

    def test_pending_source_never_calls_adapter(self):
        with patch.object(sync, 'source_by_id', return_value=dict(SOURCE, classification='pending')):
            result = self.run_source(snapshot(course()))
        self.assertEqual(result['sync_status'], 'blocked')
        self.assertIsNone(result['last_success_at'])
        self.assertEqual(sync.read_state('courses')[0], [])

    def test_schedule_brasilia_week_boundary_and_repeated_due(self):
        sunday = datetime(2026, 11, 9, 1, tzinfo=timezone.utc)  # domingo 22h em Brasília
        self.assertEqual(sync.schedule_slot('courses', sunday).date().isoformat(), '2026-11-02')
        self.assertEqual(sync.schedule_slot('courses', NOW).isoformat(), '2026-11-09T06:30:00-03:00')
        self.run_source(snapshot(course()), due=True)
        self.assertEqual(self.run_source(snapshot(), due=True)['sync_status'], 'skipped')
        self.assertEqual(self.run_source(snapshot(course()), now=NOW+timedelta(days=7), due=True)['sync_status'], 'success')

    def test_job_scope_requires_confirmed_curitiba_entry_contract(self):
        job_source = dict(SOURCE, kind='jobs')
        row = course(city='Curitiba', state='PR', contract_type='estagio', entry_level=True,
                     requirements=['Matrícula ativa (fixture).'], requirements_evidence='Fixture.', review_by='2026-11-10')
        self.assertEqual(len(sync.validate_snapshot(job_source, snapshot(row), NOW)), 1)
        for change in ({'city':'São Paulo'}, {'entry_level':False}, {'contract_type':'pj'},
                       {'requirements':[]}, {'title':'Banco de talentos'}, {'is_individual':False}):
            with self.subTest(change=change), self.assertRaises(sync.ImportFailure):
                sync.validate_snapshot(job_source, snapshot(dict(row, **change)), NOW)

    def test_deduplicates_manual_and_imported_url(self):
        self.run_source(snapshot(course()))
        item = sync.read_state('courses')[0][0]
        (self.path/'courses.json').write_text(json.dumps([dict(item, id='manual', original_url=item['original_url']+'?utm_source=test')]), encoding='utf-8')
        self.assertEqual(len(catalog.load_catalog('courses', NOW.date())), 1)
        self.run_source(snapshot(empty_confirmed=True), now=NOW+timedelta(hours=1))
        self.assertEqual(catalog.load_catalog('courses', NOW.date()), [])

    def test_configuration_diagnostic_does_not_import(self):
        from scripts.atualizar_catalogo import main
        import contextlib
        import io
        output = io.StringIO()
        with patch('sys.argv', ['atualizar_catalogo.py', '--kind', 'courses', '--diagnose']), \
                patch('scripts.atualizar_catalogo.update_catalog') as update, \
                contextlib.redirect_stdout(output):
            self.assertEqual(main(), 0)
        update.assert_not_called()
        report = json.loads(output.getvalue())
        self.assertFalse(report['import_performed'])
        self.assertTrue(report['sources'])
        self.assertNotIn('evg', {s['source_id'] for s in report['sources']})

    def test_concurrent_due_only_imports_once(self):
        with patch.dict(sync.ADAPTERS, {'fixture': lambda: snapshot(course())}, clear=True):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: sync.update_source('fixture', now=NOW, due=True), range(2)))
        self.assertCountEqual([r['sync_status'] for r in results], ['success', 'skipped'])
        self.assertEqual(len(sync.read_state('courses')[0]), 1)

    def test_one_source_failure_does_not_modify_other_source(self):
        self.run_source(snapshot(course()))
        other = dict(SOURCE, id='second')
        with patch.object(sync, 'source_by_id', return_value=other):
            with patch.dict(sync.ADAPTERS, {'second': lambda: snapshot(course('2'))}, clear=True):
                self.assertEqual(sync.update_source('second', now=NOW)['sync_status'], 'success')
        before = [r for r in sync.read_state('courses')[0] if r['source_id'] == 'second']
        self.run_source(snapshot(complete=False), now=NOW+timedelta(hours=1))
        after = [r for r in sync.read_state('courses')[0] if r['source_id'] == 'second']
        self.assertEqual(before, after)

    def test_optional_hours_and_conflicting_certificate_conditions(self):
        for changes in ({'duration_hours': -1}, {'duration_hours': 'dez'}, {'free': False},
                        {'certificate_status': 'paid', 'certificate_cost': 'Gratuito'}):
            with self.subTest(changes=changes):
                self.assertEqual(self.run_source(snapshot(course(**changes)))['sync_status'], 'error')
        self.assertEqual(self.run_source(snapshot(course(duration_hours=None)))['sync_status'], 'success')


class CatalogRouteTests(unittest.TestCase):
    setUp = test_aplicacao.SiteTests.setUp

    def test_routes_keep_contract_and_separate_external_links(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'FIRST_JOB_CATALOG_DATABASE': str(Path(temp)/'none.db')}):
            for kind in ('jobs', 'courses'):
                response = self.client.get(f'/api/{kind}?all=1&certificate_free=1')
                self.assertEqual(response.status_code, 200)
                data = response.json
                self.assertEqual(data['schema_version'], 2)
                self.assertEqual(data['total'], len(data[kind]))
                self.assertTrue(data['external_links'])
                self.assertTrue(all(s['last_success_at'] is None for s in data['sources']))
                self.assertFalse(any(s['source_id']=='meu_emprego' for s in data['external_links']))


if __name__ == '__main__':
    unittest.main()
