import io
import json
from datetime import date
from unittest.mock import patch
import unittest
import test_app
import app as site
import catalog
from profile_data import contact_errors, hydrate_profile
from resume_documents import inspect_pdf, MAX_PDF_BYTES
from resume_analysis import local_checks


class AuditTests(unittest.TestCase):
    setUp = test_app.SiteTests.setUp
    pdf = test_app.SiteTests.pdf

    def test_contact_validation_and_legacy_progress(self):
        for age in ('999','-1','abc','','0','121','²'):
            self.assertIn('age', contact_errors({'age':age,'phone':'41987654321'}))
        for phone in ('00000000000','12345678901','419999','41888888888','20987654321','419123456789'):
            self.assertIn('phone', contact_errors({'age':'18','phone':phone}))
        for age in ('1','120'):
            self.assertFalse(contact_errors({'age':age,'phone':'4132345678'}))
        original={'phone':'00000000000','age':'999','city':'Curitiba','state':'PR','desired_area':'Tecnologia','education':'Médio Completo','skills':'Excel','languages':'Português'}
        hydrated=hydrate_profile(original,{})
        self.assertEqual(hydrated['phone'],original['phone'])
        self.assertEqual(site.profile_completion(hydrated),75)
        for endpoint,method in [('/api/profile','put'),('/api/profile/contact','patch')]:
            payload=original if method=='put' else {k:original[k] for k in ('phone','age','city','state')}
            response=getattr(self.client,method)(endpoint,json=payload)
            self.assertEqual(response.status_code,400)
            self.assertIn('phone',response.json['errors'])
        response = self.client.patch('/api/profile/contact', json={
            'phone':'41987654321', 'age':'²', 'city':'Curitiba', 'state':'PR'})
        self.assertEqual(response.status_code,400)
        self.assertIn('age',response.json['errors'])

    def test_csrf_and_authentication(self):
        self.assertEqual(self.client.post('/api/auth/logout',headers={'Origin':'https://invalid.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/auth/logout',headers={'X-Requested-With':''}).status_code,403)
        self.assertEqual(self.client.post('/api/auth/logout').status_code,200)
        self.assertFalse(self.client.get('/api/me').json['authenticated'])
        self.assertEqual(self.client.post('/api/auth/login',json={'email':'teste@example.com','password':'wrong'}).status_code,401)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':'teste@example.com','password':'teste1234'}).status_code,200)

    def test_request_limits(self):
        for _ in range(30):
            response=self.client.post('/api/auth/login',json={})
        self.assertEqual(response.status_code,429)
        self.assertIn('Retry-After',response.headers)

    def test_versions_rename_and_cross_account_access(self):
        created=self.client.post('/api/resumes/generate',json={'objective':'Aprender com atividades reais.','title':'Primeira versão'}).json
        first=created['id']
        content=created['resume']
        self.assertEqual(self.client.patch(f'/api/resumes/{first}',json={'title':'Meu currículo'}).status_code,200)
        revised=dict(content,headline='Suporte de TI', sections=[dict(section, hidden='unexpected') for section in content['sections']])
        second=self.client.post(f'/api/resumes/{first}/version',json={'content':revised})
        self.assertEqual(second.status_code,201)
        self.assertTrue(all(set(section) == {'title', 'content'} for section in second.json['resume']['sections']))
        self.assertEqual(self.client.get(f'/api/resumes/{first}').json['content'],content)
        self.assertEqual(self.client.post(f'/api/resumes/{first}/version',json={'content':dict(content,name='')}).status_code,400)
        pdf=self.client.get(f"/api/resumes/{second.json['id']}/pdf")
        self.assertIn('Suporte de TI',inspect_pdf(pdf.data)['text'])
        uploaded=self.client.post('/api/resumes/upload',data={'file':(io.BytesIO(self.pdf()),'../unsafe.pdf')}).json['id']
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/register',json={'name':'Outra pessoa','email':'other@example.test','password':'safe-test-123'})
        for ident in (first,uploaded):
            for suffix in ('','/pdf','/file'):
                self.assertEqual(self.client.get(f'/api/resumes/{ident}{suffix}').status_code,404)
            for suffix in ('/analyze','/version'):
                self.assertEqual(self.client.post(f'/api/resumes/{ident}{suffix}',json={}).status_code,404)
            self.assertEqual(self.client.patch(f'/api/resumes/{ident}',json={'title':'intrusion'}).status_code,404)
            self.assertEqual(self.client.delete(f'/api/resumes/{ident}').status_code,404)

    def test_upload_boundaries(self):
        for content in (b'',b'%PDF broken',b'x'*(MAX_PDF_BYTES+1)):
            response=self.client.post('/api/resumes/upload',data={'file':(io.BytesIO(content),'test.pdf')})
            self.assertIn(response.status_code,(400,413))
        self.assertEqual(self.client.get('/api/resumes').json['resumes'],[])

    def test_catalog_expiry_empty_and_support_relevance(self):
        rows=catalog.recommendations('jobs',{},show_all=True,today=date(2026,10,28))
        self.assertEqual(rows['total'],1)
        self.assertEqual(rows['jobs'][0]['id'],'bp-infra-estagio')
        empty=catalog.recommendations('jobs',{},show_all=True,today=date(2030,1,1))
        self.assertEqual(empty['catalog_status'],'unavailable')
        courses=catalog.recommendations('courses',{'desired_area':'CLT — Suporte de TI júnior'},today=date(2026,10,28))['courses']
        self.assertTrue(courses)
        self.assertTrue(all('hardware' in c['title'].lower() for c in courses))
        report=local_checks('Texto de exemplo',{}, {'pages':1},[])
        self.assertIn('Não foi possível comparar',report['alignment']['note'])

    def test_compatible_goals_and_long_pdf(self):
        raw={'desired_area':'CLT — Suporte de TI júnior'}
        profile=hydrate_profile(raw,{})
        self.assertEqual(profile['sections']['goals']['contracts'],['clt'])
        self.assertEqual(profile['sections']['goals']['sector'],'Tecnologia')
        self.assertEqual(profile['desired_area'],raw['desired_area'])
        created=self.client.post('/api/resumes/generate',json={'objective':'Organização e comunicação. '*400}).json
        pdf=self.client.get(f"/api/resumes/{created['id']}/pdf")
        metadata=inspect_pdf(pdf.data)
        self.assertGreater(metadata['pages'],1)
        self.assertIn('Organização',metadata['text'])

    def test_generated_resume_above_analysis_page_limit(self):
        created = self.client.post('/api/resumes/generate', json={'objective':'Teste.\n' * 1500})
        self.assertEqual(created.status_code, 201)
        response = self.client.post(f"/api/resumes/{created.json['id']}/analyze?mode=checks")
        self.assertEqual(response.status_code, 422)
        self.assertIn('páginas', response.json['error'])
