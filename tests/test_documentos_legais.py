"""Páginas públicas, aceite explícito e migração sem fabricar consentimentos anteriores."""
import unittest
from datetime import datetime
from unittest.mock import patch

import app as site
import test_aplicacao


class LegalTests(unittest.TestCase):
    setUp = test_aplicacao.SiteTests.setUp

    def registration(self, **changes):
        return dict({'name':'Pessoa de teste legal','email':'legal@example.test','password':'Teste12345',
                     'terms_accepted':True,'terms_version':site.TERMS_VERSION},**changes)

    def test_public_routes_fixed_revision_and_local_assets(self):
        self.client.post('/api/auth/logout')
        with patch('app.now_sp',return_value=datetime(2027,1,2,tzinfo=site.BRAZIL_TZ)):
            for route, title in [('/termos-de-uso','Termos de Uso'),('/politica-de-privacidade','Política de Privacidade'),('/cookies','Configurações de Cookies')]:
                response=self.client.get(route)
                self.assertEqual(response.status_code,200)
                html=response.get_data(as_text=True)
                self.assertIn(title,html)
                self.assertIn('13/11/2026',html)
                self.assertIn('© 2027',html)
                if route!='/cookies':
                    self.assertIn('Felipe Correia de Oliveira',html)
                self.assertIn('mailto:primeiro.emprego.ia@gmail.com',html)
                self.assertNotIn('gmail.com.br',html)
                self.assertNotIn('fonts.googleapis.com',html)
                self.assertNotIn('fonts.gstatic.com',html)
                self.assertNotIn('Set-Cookie',response.headers)
        for route in ['/static/preferencias_cookies.js','/static/privacidade.css','/static/fontes_locais.css',
                      '/static/fonts/dm-sans.ttf','/static/fonts/plus-jakarta-sans.ttf']:
            self.assertEqual(self.client.get(route).status_code,200)

    def test_explicit_current_terms_required_no_cookies_required(self):
        for choice in [False,None,'true',1]:
            response=self.client.post('/api/auth/register',json=self.registration(terms_accepted=choice))
            self.assertEqual(response.status_code,400)
        for version in [None,'2020-01-01',123]:
            response=self.client.post('/api/auth/register',json=self.registration(terms_version=version))
            self.assertEqual(response.status_code,400)
        with site.db_connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users WHERE email=?',('legal@example.test',)).fetchone()[0],0)
        response=self.client.post('/api/auth/register',json=self.registration())
        self.assertEqual(response.status_code,201,response.json)
        user_id=response.json['user']['id']
        with site.db_connection() as db:
            row=db.execute('SELECT * FROM terms_acceptances WHERE user_id=?',(user_id,)).fetchone()
            self.assertEqual(row['terms_version'],site.TERMS_VERSION)
            self.assertIsNotNone(datetime.fromisoformat(row['accepted_at']))
            user=db.execute('SELECT password_hash FROM users WHERE id=?',(user_id,)).fetchone()
            self.assertNotEqual(user['password_hash'],'Teste12345')

    def test_acceptance_cannot_outlive_failed_registration(self):
        response=self.client.post('/api/auth/register',json=self.registration(email='teste@example.com'))
        self.assertEqual(response.status_code,409)
        with site.db_connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM terms_acceptances').fetchone()[0],1)

    def test_migration_preserves_legacy_accounts_without_fabricating_acceptance(self):
        self.client.post('/api/auth/logout')
        with site.db_connection() as db:
            db.execute('DROP TABLE terms_acceptances')
            before=[tuple(r) for r in db.execute('SELECT * FROM users')]
        site.init_db()
        site.init_db()
        with site.db_connection() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM users')],before)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM terms_acceptances').fetchone()[0],0)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':'teste@example.com','password':'teste1234'}).status_code,200)

    def test_registration_markup_and_cookie_categories_are_separate(self):
        html=self.client.get('/').get_data(as_text=True)
        self.assertIn('name="terms_accepted" value="true"',html)
        self.assertNotIn('name="terms_accepted" value="true" checked',html)
        self.assertIn('name="terms_version" value="'+site.TERMS_VERSION+'"',html)
        self.assertIn('target="_blank" rel="noopener">Termos de Uso',html)
        self.assertIn('id="cookie-functionality"',html)
        self.assertNotIn('id="cookie-functionality" name="functionality" checked',html)


if __name__=='__main__':
    unittest.main()
