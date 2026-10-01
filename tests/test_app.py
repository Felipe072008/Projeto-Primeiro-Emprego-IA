import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import app as site
import catalog
import resume_analysis
from pypdf import PdfWriter
from resume_documents import build_resume_pdf, inspect_pdf, InvalidPDF


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        self.db_patch = patch.object(site, 'DATABASE', directory / 'test.db')
        self.files_patch = patch.object(site, 'UPLOAD_DIR', directory)
        self.db_patch.start(); self.files_patch.start()
        self.addCleanup(self.db_patch.stop); self.addCleanup(self.files_patch.stop)
        site.app.config.update(TESTING=True)
        site.init_db()
        self.client = site.app.test_client()
        self.client.post('/api/auth/register', json={'name':'Pessoa de Teste', 'email':'teste@example.com', 'password':'teste1234'})

    def pdf(self):
        return build_resume_pdf({'name':'Pessoa de Teste', 'headline':'Tecnologia', 'contacts':['teste@example.com'], 'sections':[{'title':'Formação', 'content':'Ensino médio concluído em 2025. Desenvolvi um projeto escolar com Python e Git.'}]}).getvalue()

    def test_pdf_only_and_content(self):
        for name, content in [('curriculo.docx', b'PK fake'), ('falso.pdf', b'not pdf'), ('corrompido.pdf', b'%PDF-1.7 invalid')]:
            response = self.client.post('/api/resumes/upload', data={'file':(io.BytesIO(content), name)})
            self.assertEqual(response.status_code, 400, response.json)
        response = self.client.post('/api/resumes/upload', data={'file':(io.BytesIO(self.pdf()), 'cv.PDF')})
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(len(self.client.get('/api/resumes').json['resumes']), 1)

    def test_limits_password_and_scan(self):
        writer = PdfWriter(); writer.add_blank_page(595,842)
        stream=io.BytesIO(); writer.write(stream)
        self.assertFalse(inspect_pdf(stream.getvalue())['readable'])
        writer.encrypt('secret'); stream=io.BytesIO(); writer.write(stream)
        with self.assertRaises(InvalidPDF): inspect_pdf(stream.getvalue())
        with self.assertRaises(InvalidPDF): inspect_pdf(b'%PDF-'+b'x'*(8*1024*1024))
        writer=PdfWriter()
        for _ in range(21): writer.add_blank_page(595,842)
        stream=io.BytesIO(); writer.write(stream)
        with self.assertRaises(InvalidPDF): inspect_pdf(stream.getvalue())

    def test_resume_fields_escaping_and_ownership(self):
        self.client.put('/api/profile',json={'city':'Curitiba','state':'PR','course':'Técnico em Informática','desired_area':'Tecnologia'})
        created=self.client.post('/api/resumes/generate',json={'location':'','email':'','objective':'Aprender <b> & colaborar em projetos reais.'})
        self.assertEqual(created.status_code,201,created.json)
        id=created.json['id']
        pdf=self.client.get(f'/api/resumes/{id}/pdf')
        self.assertEqual(pdf.status_code,200)
        text=inspect_pdf(pdf.data)['text']
        self.assertIn('Técnico em Informática',text)
        self.assertIn('<b> &',text)
        self.assertNotIn('Curitiba',text)
        self.assertNotIn('teste@example.com',text)
        self.assertIn('inline',self.client.get(f'/api/resumes/{id}/pdf?inline=1').headers['Content-Disposition'])
        self.client.post('/api/auth/logout')
        self.assertEqual(self.client.get(f'/api/resumes/{id}/pdf').status_code,401)
        self.client.post('/api/auth/register',json={'name':'Outra Pessoa','email':'outra@example.com','password':'teste1234'})
        self.assertEqual(self.client.get(f'/api/resumes/{id}/pdf').status_code,404)
        self.assertEqual(self.client.post(f'/api/resumes/{id}/analyze').status_code,404)

    def test_analysis_unavailable_is_honest(self):
        created=self.client.post('/api/resumes/upload',data={'file':(io.BytesIO(self.pdf()),'cv.pdf')})
        with patch('resume_analysis.ai_status',return_value={'available':False}):
            report=self.client.post(f"/api/resumes/{created.json['id']}/analyze").json
        self.assertEqual(report['engine'],'document_checks')
        self.assertIsNone(report['contextual'])
        self.assertGreaterEqual(len(report['checks']),6)


class CatalogTests(unittest.TestCase):
    def test_live_catalog_matching(self):
        today=date(2026,9,25)
        result=catalog.recommendations('jobs',{'desired_area':'Tecnologia'},today=today)
        self.assertTrue(any(j['match']=='direct' for j in result['jobs']))
        self.assertTrue(any(j['match']=='related' for j in result['jobs']))
        self.assertTrue(all(j['city']=='Curitiba' and j['state']=='PR' for j in result['jobs']))
        self.assertEqual(catalog.recommendations('jobs',{'desired_area':'Astronomia'},today=today)['total'],0)
        self.assertGreater(catalog.recommendations('jobs',{'desired_area':'Astronomia'},show_all=True,today=today)['total'],0)
        self.assertEqual(catalog.load_catalog('jobs',date(2027,1,1)),[])
        free=catalog.recommendations('courses',{},free_only=True,today=today)['courses']
        self.assertTrue(free and all(c['free'] for c in free))
        technical=catalog.recommendations('courses',{},course_type='tecnico',today=today)['courses']
        self.assertTrue(technical and all(c['course_type']=='tecnico' for c in technical))

    def test_rejects_nonindividual_wrong_city_and_stale(self):
        records=json.loads(Path('data/jobs.json').read_text(encoding='utf-8'))
        fixtures=[dict(records[0],original_url='https://example.com/'),dict(records[0],city='São Paulo'),dict(records[0],review_by='2026-09-01'),dict(records[0],status='closed')]
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'jobs.json').write_text(json.dumps(fixtures),encoding='utf-8')
            with patch.object(catalog,'DATA_DIR',Path(tmp)):
                self.assertEqual(catalog.load_catalog('jobs',date(2026,9,25)),[])


class AITests(unittest.TestCase):
    def test_valid_response_and_fabricated_rewrite_filter(self):
        text='Desenvolvi um projeto escolar com Python em 2025.'
        model={'summary':'Revisar a descrição do projeto.', 'strengths':[{'title':'Projeto','evidence':text,'explanation':'Há uma experiência concreta.'}], 'improvements':[{'priority':'alta','title':'Contexto','evidence':'Falta instituição.','suggestion':'Informe a escola real.'},{'priority':'media','title':'Objetivo','evidence':'Objetivo ausente.','suggestion':'Informe o cargo desejado.'}], 'rewrites':[{'original':text,'suggested':'Desenvolvi 50 projetos e aumentei vendas em 90%.','reason':'Métricas'}], 'next_steps':['Conferir datas.','Detalhar ferramentas.']}
        with patch('resume_analysis.ai_status',return_value={'available':True,'model':'test'}), patch('resume_analysis._request',return_value={'done':True,'response':json.dumps(model)}):
            result=resume_analysis.analyze(text,{}, {'pages':1},[])
        self.assertEqual(result['engine'],'ollama_local')
        self.assertEqual(result['contextual']['rewrites'],[])
        with patch('resume_analysis.ai_status',return_value={'available':True,'model':'test'}), patch('resume_analysis._request',return_value={'done':True,'response':'broken'}):
            self.assertEqual(resume_analysis.analyze(text,{}, {'pages':1},[])['engine'],'document_checks')


if __name__=='__main__': unittest.main()
