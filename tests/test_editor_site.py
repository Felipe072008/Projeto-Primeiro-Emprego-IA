"""Editor com bancos e imagens descartáveis, sem usuários reais na prévia."""
import copy
import io
import json
import time
import unittest
from unittest.mock import patch

from PIL import Image
import app as site
import editor_site as editor
from conteudo_editavel import defaults, validate
import test_admin


class EditorTests(unittest.TestCase):
    setUp=test_admin.AdminTests.setUp
    login=test_admin.AdminTests.login
    post=test_admin.AdminTests.post

    def state(self):
        return self.staff.get('/admin-api/site/state').json

    def save(self,value):
        return self.post('/admin-api/site/draft',{'content':value,'revision':self.state()['revision']})

    def publish(self,**extra):
        return self.post('/admin-api/site/publish',dict(revision=self.state()['revision'],confirm=True,**extra))

    def test_allowlist_and_limits(self):
        self.login()
        mutations=[lambda v:v['texts'].update({'unknown':'x'}),lambda v:v['theme'].update(primary='red'),
                   lambda v:v['theme'].update(body_font='https://outside.test/font'),
                   lambda v:v['texts'].update({'jobs.title':'x'*121}),lambda v:v['texts'].update({'jobs.title':[]}),
                   lambda v:v['layout']['jobs'][0].update(visible=False),lambda v:v['layout']['jobs'].reverse()]
        for mutation in mutations:
            value=defaults(); mutation(value)
            self.assertEqual(self.save(value).status_code,400)
        self.assertEqual(self.save(defaults()).status_code,200)
        stale=self.post('/admin-api/site/draft',{'content':defaults(),'revision':'old'})
        self.assertEqual(stale.status_code,409)

    def test_draft_publish_restore_undo_and_contrast(self):
        self.login(); value=defaults(); value['texts']['login.title']='Texto novo'
        self.assertEqual(self.save(value).status_code,200)
        self.assertNotIn('Texto novo',self.client.get('/').text)
        self.assertEqual(self.publish().status_code,200)
        self.assertIn('Texto novo',self.client.get('/').text)
        first=self.state()['history'][0]['id']
        value['texts']['login.title']='Segunda publicação'; self.save(value); self.publish()
        self.assertEqual(self.post('/admin-api/site/undo',{'revision':self.state()['revision']}).status_code,200)
        self.assertIn('Texto novo',self.client.get('/').text)
        self.post('/admin-api/site/restore',{'revision':self.state()['revision'],'version':'original'})
        self.assertIn('Texto novo',self.client.get('/').text)
        self.assertEqual(self.state()['draft'],defaults())
        self.post('/admin-api/site/restore',{'revision':self.state()['revision'],'version':first})
        value=self.state()['draft']; value['theme']['text']=value['theme']['background']; self.save(value)
        self.assertEqual(self.publish().status_code,400)
        self.assertEqual(self.publish(confirm_low_contrast=True).status_code,200)
        css=self.client.get('/site-theme.css'); self.assertIn('--ink:',css.text)
        self.assertEqual(self.client.get('/site-theme.css',headers={'If-None-Match':css.headers['ETag']}).status_code,304)

    def test_security_preview_and_audit(self):
        for route in ('/admin/site','/admin-assets/editor_site.js','/admin-api/site/state'):
            self.assertEqual(self.client.get(route).status_code,401)
        self.login()
        self.assertEqual(self.staff.post('/admin-api/site/draft',json={}).status_code,403)
        value=defaults(); value['texts']['login.title']='<script>alert(1)</script><img src=x onerror=alert(2)>'
        self.save(value); self.save(value)
        with patch.object(site,'get_user',side_effect=AssertionError('Usuários reais proibidos')),patch.object(site,'get_profile',side_effect=AssertionError('Perfil real proibido')),patch.object(site,'db_connection',side_effect=AssertionError('Banco de usuários proibido na prévia')):
            preview=self.post('/admin-api/site/render',{'content':value,'page':'account'})
        self.assertEqual(preview.status_code,200)
        html=preview.json['html']; self.assertNotIn('<script',html)
        self.assertIn('&lt;script&gt;',html); self.assertNotIn('Pessoa de Teste',html)
        self.assertIn('exemplo@example.test',html)
        import admin
        with admin.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM admin_audit_log WHERE action='site_draft'").fetchone()[0],1)
        self.assertIn("script-src 'self'",self.client.get('/').headers['Content-Security-Policy'])

    def test_logo_validation_and_draft_privacy(self):
        self.login()
        def upload(raw,name='logo.png',alt='Marca de teste'):
            return self.staff.post('/admin-api/site/logo',data={'alt':alt,'file':(io.BytesIO(raw),name)},headers={'X-CSRF-Token':self.csrf})
        stream=io.BytesIO(); Image.new('RGB',(16,16),'blue').save(stream,'PNG'); png=stream.getvalue()
        for raw,name,alt in [(b'<svg onload="alert(1)"></svg>','x.svg','x'),(b'<script>x</script>','x.png','x'),
                             (png+b'<script>x</script>','x.png','x'),(b'x'*1048577,'x.png','x'),(png,'x.png','')]:
            self.assertEqual(upload(raw,name,alt).status_code,400)
        result=upload(png); self.assertEqual(result.status_code,200,result.json)
        logo=result.json['logo']; self.assertEqual(self.client.get('/site-logo/'+logo['name']).status_code,404)
        value=defaults(); value['theme']['logo']=logo; self.save(value); self.publish()
        response=self.client.get('/site-logo/'+logo['name'])
        self.assertEqual(response.mimetype,'image/png'); self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff'); response.close()
        self.assertIn(logo['name'],self.client.get('/').text)
        (editor.logo_dir(site)/logo['name']).unlink()
        self.assertNotIn(logo['name'],self.client.get('/').text)

    def test_corruption_fallback_migration_and_retention(self):
        self.login()
        with site.db_connection() as db:
            count=db.execute('SELECT count(*) FROM users').fetchone()[0]
            editor.init_schema(db); editor.init_schema(db)
            self.assertEqual(count,db.execute('SELECT count(*) FROM users').fetchone()[0])
            db.execute("INSERT INTO site_texts VALUES ('published','broken')")
        editor.CACHE.clear()
        self.assertEqual(self.client.get('/api/site-content').json,defaults())
        for index in range(32):
            with patch('editor_site.time.time',return_value=time.time()+index*601):
                self.assertEqual(self.publish(note=str(index)).status_code,200)
        self.assertEqual(len(self.state()['history']),30)

    def test_sections_blocks_xss_and_urls(self):
        self.login(); value=defaults(); value['layout']['dashboard'].reverse()
        value['layout']['dashboard'][0]['visible']=False
        value['blocks']=[{'id':'one','slot':'jobs','type':'button','visible':True,'title':'','body':'',
                          'label':'<img onerror=x>','url':'https://example.test/','style':'info','items':[]}]
        for url in ('javascript:alert(1)','data:text/html,x','//evil.test','/admin','https://a.test\\@b.test'):
            invalid=copy.deepcopy(value); invalid['blocks'][0]['url']=url
            self.assertEqual(self.save(invalid).status_code,400,url)
        invalid=copy.deepcopy(value); invalid['blocks']=[dict(value['blocks'][0],id=str(i)) for i in range(31)]
        self.assertEqual(self.save(invalid).status_code,400)
        self.save(value); self.publish(); html=self.client.get('/').text
        self.assertIn('rel="noopener noreferrer"',html); self.assertIn('&lt;img onerror=x&gt;',html)
        self.assertLess(html.index('data-section-key="dashboard.guidance"'),html.index('data-section-key="dashboard.intro"'))

    def test_upload_publish_limits_persist(self):
        self.login()
        for _ in range(10): self.assertEqual(self.publish().status_code,200)
        self.assertEqual(self.publish().status_code,429)
        with site.db_connection() as db:
            self.assertEqual(db.execute("SELECT count FROM request_limits WHERE key LIKE 'site-editor:publish:%'").fetchone()[0],10)
        for _ in range(10):
            response=self.staff.post('/admin-api/site/logo',data={'alt':'Teste','file':(io.BytesIO(b'fake'),'x.png')},headers={'X-CSRF-Token':self.csrf})
            self.assertEqual(response.status_code,400)
        response=self.staff.post('/admin-api/site/logo',data={},headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(response.status_code,429)
