import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import app as site
import catalog
from resume_documents import inspect_pdf
import test_app


class ProfileSectionsTests(unittest.TestCase):
    setUp = test_app.SiteTests.setUp

    def save(self, section, **changes):
        data = self.client.get('/api/me').json['profile']['sections'][section]
        data.update(changes)
        response = self.client.patch('/api/profile/' + section, json=data)
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def test_independent_saves_completion_and_first_job(self):
        initial = self.client.get('/api/me').json
        self.assertEqual(initial['completion'], 0)
        self.assertEqual(initial['profile']['sections']['experiences']['items'], [])
        self.save('education', level='Superior Completo')
        self.save('contact', phone='41999999999', age='18', city='Curitiba', state='Paraná')
        self.save('goals', desired_area='Estágio — Tecnologia da Informação')
        self.save('skills', items=[{'name': 'Python'}])
        done = self.save('languages', items=[{'language': 'Português', 'level': 'Nativo'}])
        self.assertEqual(done['completion'], 100)
        self.assertEqual(done['profile']['missing_fields'], [])
        self.save('experiences', no_experience=True)
        self.assertEqual(self.client.get('/api/me').json['completion'], 100)
        self.save('availability', periods=['Manhã'], days=['Segunda'], other_city='Não')
        current = self.client.get('/api/me').json['profile']
        self.assertEqual(current['phone'], '41999999999')
        self.assertEqual(current['education'], 'Superior Completo')
        self.assertEqual(current['professional_experience'], '')
        self.assertIn('Manhã', current['resume_fields']['additional_information'])
        removed = self.save('skills', items=[])
        self.assertLess(removed['completion'], 100)
        self.assertIn('Habilidades', removed['profile']['missing_fields'])

    def test_legacy_text_is_preserved_without_invented_records(self):
        legacy = {'phone':'41999999999','age':'18','city':'Curitiba','state':'Paraná','desired_area':'Tecnologia','education':'Médio Completo','course':'Um curso antigo sem datas','skills':'Texto livre sem lista','languages':'Idioma antigo sem nível','professional_experience':'Participei de uma atividade sem cargo ou empresa informados.'}
        self.assertEqual(self.client.put('/api/profile', json=legacy).status_code, 200)
        before = self.client.get('/api/me').json['profile']
        self.assertEqual(before['sections']['experiences']['items'], [])
        self.assertEqual(before['sections']['experiences']['legacy'], legacy['professional_experience'])
        self.save('contact', phone='41988888888', age='19', city='Curitiba', state='Paraná')
        self.save('skills', items=[{'name':'Git'}])
        after = self.client.get('/api/me').json['profile']
        for field in ('professional_experience','languages','course'):
            self.assertEqual(after[field], legacy[field])
        self.assertIn(legacy['skills'], after['skills'])
        with site.db_connection() as db:
            row = db.execute('SELECT * FROM profiles WHERE user_id=?',(after['user_id'],)).fetchone()
            self.assertEqual(row['skills'], legacy['skills'])
            self.assertEqual(row['phone'], legacy['phone'])
        site.init_db()
        self.assertEqual(self.client.get('/api/me').json['profile']['skills'], after['skills'])

    def test_structured_records_reach_resume_pdf_and_analysis(self):
        experience = {'role':'Aprendiz de suporte','company':'Empresa informada','contract':'Jovem Aprendiz','start':'2025-01-10','end':'2025-12-10','current':False,'description':'Organizei equipamentos e auxiliei usuários.'}
        self.save('experiences', items=[experience,dict(experience,role='Estagiário',start='2026-01-10',end='',current=True)])
        self.save('education', level='Cursando Superior', items=[{'level':'Cursando Superior','course':'Sistemas','institution':'Instituição informada','status':'Cursando','year':'2028','city':'Curitiba','state':'PR'}])
        self.save('courses',items=[{'name':'Curso real','institution':'Instituição do curso','hours':'20','status':'Concluído','year':'2025','certificate_url':'https://example.com/certificado'}])
        self.save('projects',items=[{'title':'Projeto escolar','context':'Minha escola','start':'2025-02-01','end':'2025-03-01','description':'Desenvolvi uma planilha para organizar as tarefas.'}])
        self.save('skills',items=[{'name':'Excel'}])
        self.save('languages',items=[{'language':'Inglês','level':'Básico'}])
        created=self.client.post('/api/resumes/generate',json={})
        self.assertEqual(created.status_code,201,created.json)
        text=inspect_pdf(self.client.get(f"/api/resumes/{created.json['id']}/pdf").data)['text']
        for value in ('Empresa informada','Instituição informada','Previsão: 2028','Curso real','Projeto escolar','Excel','Inglês'):
            self.assertIn(value,text)
        self.assertLess(text.index('Estagiário'),text.index('Aprendiz de suporte'))
        with patch('resume_analysis.ai_status',return_value={'available':False}):
            report=self.client.post(f"/api/resumes/{created.json['id']}/analyze")
        self.assertEqual(report.status_code,200)
        self.assertEqual(report.json['engine'],'document_checks')
        reviewed=self.client.post('/api/resumes/generate',json={'education':'','professional_experience':''})
        self.assertFalse(any(s['title'] in {'Formação acadêmica','Experiência profissional'} for s in reviewed.json['resume']['sections']))

    def test_invalid_sections_never_overwrite_saved_data(self):
        self.save('contact',phone='41999999999',age='18',city='Curitiba',state='Paraná')
        fixtures=[('contact',{'phone':'1'*12,'age':'0','city':'Curitiba','state':'PR'}),('goals',{'desired_area':'Área inventada'}),('skills',{'items':[{'name':'Organização'},{'name':'organizacao'}]}),('languages',{'items':[{'language':'Inglês','level':'Expert'}]}),('courses',{'items':[{'name':'Curso','institution':'Escola','status':'Concluído','certificate_url':'javascript:alert(1)'}]}),('experiences',{'items':[{'role':'Cargo','company':'Empresa','start':'2025-10-10','end':'2024-10-10'}]}),('experiences',{'items':[{'role':'Cargo','company':'Empresa','start':'2099-01-01'}]}),('education',{'level':'Não listado'}),('availability',{'periods':['Madrugada']}),('contact',{'user_id':999})]
        fixtures += [
            ('courses', {'items':[{'name':'Curso','institution':'Escola','status':'Concluído','certificate_url':'https://['}]}),
            ('courses', {'items':[{'name':'Curso','institution':'Escola','status':'Concluído','year':'²²²²'}]}),
        ]
        for section,changes in fixtures:
            with self.subTest(section=section,changes=changes):
                previous=self.client.get('/api/me').json['profile']
                data=dict(previous['sections'][section],**changes)
                response=self.client.patch('/api/profile/'+section,json=data)
                self.assertEqual(response.status_code,400,response.json)
                self.assertTrue(response.json['errors'])
                self.assertEqual(self.client.get('/api/me').json['profile'],previous)
        for payload in (None,[],42,'invalid'):
            self.assertEqual(self.client.patch('/api/profile/contact',json=payload).status_code,400)

    def test_sections_are_private_to_logged_user(self):
        self.save('skills',items=[{'name':'Conhecimento privado'}])
        self.client.post('/api/auth/logout')
        self.assertEqual(self.client.patch('/api/profile/skills',json={'items':[]}).status_code,401)
        self.client.post('/api/auth/register',json={'name':'Outra pessoa','email':'outra@example.test','password':'teste1234'})
        self.assertEqual(self.client.get('/api/me').json['profile']['skills'],'')
        self.save('skills',items=[{'name':'Outro conhecimento'}])
        self.client.post('/api/auth/login',json={'email':'teste@example.com','password':'teste1234'})
        self.assertEqual(self.client.get('/api/me').json['profile']['skills'],'Conhecimento privado')

    def test_secondary_interests_and_explicit_contract_preferences(self):
        self.save('goals',desired_area='Estágio — Tecnologia da Informação',secondary_areas=['CLT — Auxiliar de logística ou estoque'],contracts=['clt'])
        profile=self.client.get('/api/me').json['profile']
        jobs=catalog.recommendations('jobs',profile,today=date(2026,10,8))['jobs']
        self.assertTrue(jobs)
        self.assertTrue(all(item['contract_type']=='clt' for item in jobs))
        self.assertTrue(any(item['id']=='destro-logistica' and item['match']=='direct' for item in jobs))
        courses=catalog.recommendations('courses',profile,today=date(2026,10,8))['courses']
        self.assertTrue(any('tecnologia' in item['areas'] and item['match']=='direct' for item in courses))
        self.assertTrue(any('logistica' in item['areas'] and item['match']=='direct' for item in courses))


if __name__=='__main__': unittest.main()
