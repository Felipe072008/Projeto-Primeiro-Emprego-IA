"""Regressões do catálogo revisado e do perfil de Administração; sem rede e sem usuários reais."""
import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import app as site
import catalogo_oportunidades as catalog
from fontes_catalogo import sources
import test_aplicacao

ROOT = Path(__file__).resolve().parents[1]
REVIEW = json.loads((ROOT/'docs/catalogo/revisao-vagas-2026-11-09.json').read_text(encoding='utf-8'))
TODAY = date.fromisoformat(REVIEW['reviewed_at'][:10])


class RevisedCatalogTests(unittest.TestCase):
    def setUp(self):
        test_aplicacao.SiteTests.setUp(self)
        self.catalog_patch.stop()  # Estes cenários exercitam os arquivos atuais, não o acervo de outubro.

    def test_only_open_reviewed_records_are_exposed_and_archive_is_preserved(self):
        archive = json.loads((ROOT/'data/historico/catalogo-antes-revisao-2026-11-09.json').read_text(encoding='utf-8'))
        self.assertEqual(len(archive['jobs']),17)
        records = json.loads((ROOT/'data/jobs.json').read_text(encoding='utf-8'))
        self.assertTrue({r['id'] for r in archive['jobs']} <= {r['id'] for r in records})
        visible = catalog.load_catalog('jobs',TODAY)
        self.assertEqual(len(visible), REVIEW['published_total'])
        self.assertEqual({r['contract_type'] for r in visible},{'aprendiz','estagio','clt'})
        reviewed_open = {r['id'] for r in REVIEW['items'] if r['result'] in {'open','open_new'}}
        self.assertEqual({r['id'] for r in visible},reviewed_open)
        for row in visible:
            self.assertEqual(row['availability_status'],'open')
            self.assertEqual((row['city'],row['state']),('Curitiba','PR'))
            self.assertTrue(row['availability_evidence'])
            self.assertTrue(row['last_verified_at'])
        for row in records:
            if row['id'] not in reviewed_open:
                before = next(r for r in archive['jobs'] if r['id']==row['id'])
                self.assertEqual(row['checked_on'],before['checked_on'])
                self.assertEqual(row['review_by'],before['review_by'])

    def test_administration_courses_and_area_change_use_saved_profile(self):
        results=[]
        with patch('app.now_sp',return_value=site.datetime.combine(TODAY,site.datetime.min.time(),tzinfo=site.BRAZIL_TZ)):
            for label, area in [('Administração','administracao'),('Tecnologia','tecnologia')]:
                goals=self.client.get('/api/me').json['profile']['sections']['goals']
                goals.update(desired_area=label,sector=label,target_role='',secondary_areas=[],contracts=[])
                response=self.client.patch('/api/profile/goals',json=goals)
                self.assertEqual(response.status_code,200,response.json)
                response=self.client.get('/api/courses')
                self.assertEqual(response.status_code,200)
                data=response.json
                self.assertEqual(data['recognized_areas'],[label])
                self.assertEqual(data['interest'],label)
                self.assertTrue(data['personalized'])
                self.assertGreater(data['total'],0)
                self.assertTrue(all(area in c['areas'] for c in data['courses']))
                results.append({c['id'] for c in data['courses']})
        self.assertNotEqual(*results)

    def test_previous_sources_remain_and_meu_emprego_is_not_configured(self):
        registered={s['id'] for s in sources()}
        self.assertTrue({'gupy','central_estagios_pr','destro','fundacao_bradesco','senai_sp',
                         'ciee_pr','infojobs','catho','indeed','evg','aprenda_mais','sebrae',
                         'prime_cursos','coursera'} <= registered)
        self.assertNotIn('meu_emprego',registered)
        data=catalog.recommendations('jobs',{},show_all=True,today=TODAY)
        self.assertNotIn('meu_emprego',{s['id'] for s in data['sources']})
        self.assertEqual(data['catalog_status'],'available')


if __name__=='__main__':
    unittest.main()
