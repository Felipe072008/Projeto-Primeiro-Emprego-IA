"""Segurança e migrações com bancos/arquivos temporários; nenhuma conta real é usada."""
import copy
import json
import os
import secrets
import sqlite3
import time
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import admin
import administracao_dados as data
import app as site
import catalogo_oportunidades as catalog
import test_aplicacao


class AdminTests(unittest.TestCase):
    def setUp(self):
        test_aplicacao.SiteTests.setUp(self)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {'FIRST_JOB_ADMIN_DATABASE':str(self.root/'admin.db'),
            'FIRST_JOB_DATABASE':str(site.DATABASE), 'FIRST_JOB_CATALOG_DATABASE':str(self.root/'catalog.db'),
            'ADMIN_TRUST_PYTHONANYWHERE':'0'})
        env.start(); self.addCleanup(env.stop)
        self.password, self.pin = secrets.token_urlsafe(20), str(secrets.randbelow(900000)+100000)
        admin.create_account('testadmin',self.password,self.pin)
        self.staff = site.app.test_client()
        self.staff.environ_base['HTTP_X_REQUESTED_WITH'] = 'FirstJob'
        self.csrf = self.staff.get('/admin-access').json['csrf']

    def post(self,path,payload=None,method='POST',**options):
        return self.staff.open(path,method=method,json=payload or {},headers={'X-CSRF-Token':self.csrf},**options)

    def login(self):
        response=self.post('/admin-access/pin',{'pin':self.pin})
        self.assertEqual(response.status_code,200,response.json)
        self.csrf=response.json['csrf']
        response=self.post('/admin-access/login',{'username':'testadmin','password':self.password})
        self.assertEqual(response.status_code,200,response.json)
        self.csrf=response.json['csrf']
        return response

    def course(self):
        return {'title':'Curso sintético de administração','institution':'Instituição de teste',
            'source':'Fonte sintética','original_url':'https://example.test/course/admin',
            'description':'Somente fixture de teste, não é uma oferta real.',
            'review_by':(site.now_sp().date()+timedelta(days=7)).isoformat(),'expires_on':'',
            'availability_evidence':'Fixture: inscrição aberta','areas':['administracao'],'requirements':[],
            'certificate':'Fixture: certificado pago','certificate_status':'paid',
            'certificate_source':'https://example.test/certificate','access_evidence':'Fixture: acesso completo gratuito',
            'course_type':'livre','duration':''}

    def test_separate_auth_and_protected_panel_assets(self):
        for route in ['/admin','/admin-assets/admin.js','/admin-assets/admin.css','/admin-api/users','/admin-api/resumes','/admin-api/system','/admin-api/activities','/admin-api/overview']:
            self.assertEqual(self.client.get(route).status_code,401,route)
        self.assertEqual(self.client.get('/static/admin.js').status_code,404)
        self.assertEqual(self.client.get('/static/../admin_assets/admin.js').status_code,404)
        cookie=self.login().headers.get('Set-Cookie','')
        for flag in ('Secure','HttpOnly','SameSite=Strict'):
            self.assertIn(flag,cookie)
        for route in ['/admin','/admin-assets/admin.js','/admin-api/overview']:
            response=self.staff.get(route)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            response.close()
        self.assertEqual(self.staff.get('/api/resumes').status_code,401)
        self.assertTrue(self.client.get('/api/me').json['authenticated'])

    def test_pin_is_mandatory_expires_and_errors_are_generic(self):
        response=self.post('/admin-access/login',{'username':'testadmin','password':self.password})
        self.assertEqual(response.status_code,401)
        self.assertEqual(response.json,{'error':'Dados inválidos'})
        response=self.post('/admin-access/pin',{'pin':self.pin})
        self.csrf=response.json['csrf']
        with patch('admin.time.time',return_value=time.time()+301):
            response=self.post('/admin-access/login',{'username':'testadmin','password':self.password})
        self.assertEqual(response.status_code,401)
        self.assertEqual(response.json,{'error':'Dados inválidos'})

    def test_five_errors_are_persisted_and_forwarded_header_cannot_bypass(self):
        for index in range(5):
            response=self.post('/admin-access/pin',{'pin':'wrong'},environ_overrides={'HTTP_X_FORWARDED_FOR':f'198.51.100.{index}'})
            self.assertEqual(response.status_code,429 if index==4 else 401)
        with admin.connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM admin_blocks').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM admin_attempts').fetchone()[0],5)
        admin.init_admin()
        self.assertEqual(self.post('/admin-access/pin',{'pin':self.pin}).status_code,429)
        with patch('admin.time.time',return_value=time.time()+901):
            self.csrf=self.staff.get('/admin-access').json['csrf']
            self.assertEqual(self.post('/admin-access/pin',{'pin':self.pin}).status_code,200)
        with site.app.test_request_context(headers={'X-Real-IP':'203.0.113.4','X-Forwarded-For':'198.51.100.2'},environ_base={'REMOTE_ADDR':'127.0.0.1'}):
            self.assertEqual(admin.client_ip(),'127.0.0.1')
            with patch.dict(os.environ,{'ADMIN_TRUST_PYTHONANYWHERE':'1'}):
                self.assertEqual(admin.client_ip(),'203.0.113.4')

    def test_csrf_expiry_and_logout_revoke_server_session(self):
        self.login()
        self.assertEqual(self.staff.post('/admin-api/users/1/deactivate',json={}).status_code,403)
        self.assertEqual(self.post('/admin-api/users/1/deactivate',{},environ_overrides={'HTTP_ORIGIN':'https://other.test'}).status_code,403)
        with patch('admin.time.time',return_value=time.time()+1801):
            self.assertEqual(self.staff.get('/admin-api/overview').status_code,401)
        token=self.staff.get_cookie(admin.COOKIE).value
        self.assertEqual(self.post('/admin-api/logout').status_code,200)
        self.staff.set_cookie(admin.COOKIE,token)
        self.assertEqual(self.staff.get('/admin-api/overview').status_code,401)

    def test_deactivation_revokes_user_sessions_and_login_then_reactivation(self):
        self.login()
        with site.db_connection() as db:
            user_id=db.execute('SELECT id FROM users').fetchone()[0]
        self.assertEqual(self.post(f'/admin-api/users/{user_id}/deactivate').status_code,200)
        self.assertEqual(self.client.get('/api/profile').status_code,401)
        response=self.client.post('/api/auth/login',json={'email':'teste@example.com','password':'teste1234'})
        self.assertEqual(response.status_code,401)
        self.assertEqual(self.post(f'/admin-api/users/{user_id}/reactivate').status_code,200)
        response=self.client.post('/api/auth/login',json={'email':'teste@example.com','password':'teste1234'})
        self.assertEqual(response.status_code,200)
        with site.db_connection() as db:
            self.assertIsNotNone(db.execute('SELECT last_login_at FROM users WHERE id=?',(user_id,)).fetchone()[0])

    def test_resume_metadata_never_exposes_content_or_paths(self):
        with site.db_connection() as db:
            db.execute("UPDATE profiles SET professional_experience='PRIVATE PROFILE MARKER'")
            db.execute("INSERT INTO resumes (user_id,kind,original_name,saved_name,content_json,created_at,updated_at) VALUES (1,'generated',?,NULL,?,?,?)",('PRIVATE FILENAME',json.dumps({'private':'PRIVATE RESUME MARKER'}),site.timestamp(),site.timestamp()))
        self.login()
        for route in ['/admin-api/users','/admin-api/resumes','/admin-api/overview','/admin-api/activities']:
            response=self.staff.get(route)
            self.assertEqual(response.status_code,200,response.json)
            content=response.get_data(as_text=True)
            for marker in ['PRIVATE PROFILE MARKER','PRIVATE RESUME MARKER','PRIVATE FILENAME','content_json','saved_name','password_hash']:
                self.assertNotIn(marker,content)
        self.assertEqual(self.staff.get('/admin-api/resumes/1/file').status_code,404)
        self.assertEqual(self.staff.get('/api/resumes/1/file').status_code,401)

    def test_delete_requires_deactivation_confirmation_and_cascades(self):
        self.login()
        saved=self.root/'fixture.pdf'; saved.write_bytes(b'test file only')
        with site.db_connection() as db:
            db.execute("INSERT INTO resumes (user_id,kind,saved_name,created_at,updated_at) VALUES (1,'uploaded',?,?,?)",(saved.name,site.timestamp(),site.timestamp()))
        self.assertEqual(self.post('/admin-api/users/1/delete',{'confirmation':'APAGAR 1'}).status_code,400)
        self.assertTrue(saved.exists())
        self.post('/admin-api/users/1/deactivate')
        self.assertEqual(self.post('/admin-api/users/1/delete',{'confirmation':'incorrect'}).status_code,400)
        self.assertEqual(self.post('/admin-api/users/1/delete',{'confirmation':'APAGAR 1'}).status_code,200)
        self.assertFalse(saved.exists())
        with site.db_connection() as db:
            self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0],1)
            for table in ('users','profiles','resumes','terms_acceptances','profile_sections'):
                self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0],0)

    def test_catalog_manual_filters_tombstones_and_paid_certificate(self):
        self.login()
        response=self.post('/admin-api/catalog/courses',self.course())
        self.assertEqual(response.status_code,201,response.json)
        items=self.staff.get('/admin-api/catalog/courses?origin=manual').json['items']
        item=next(r for r in items if r['original_url']==self.course()['original_url'])
        item_id=item['admin_id']
        available=catalog.recommendations('courses',{'desired_area':'Administração'})
        self.assertIn(item['id'],[r['id'] for r in available['courses']])
        self.assertNotIn(item['id'],[r['id'] for r in catalog.recommendations('courses',{'desired_area':'Administração'},certificate_free=True)['courses']])
        self.post(f'/admin-api/catalog/courses/{item_id}',{'action':'hide'},'PATCH')
        for action in ['hide','remove']:
            if action=='remove': self.post(f'/admin-api/catalog/courses/{item_id}',{'action':action},'PATCH')
            refreshed=copy.deepcopy(item); refreshed.update(title='Nova importação',verification_method='sync')
            with site.db_connection() as db: data.mirror(db,'courses',[refreshed])
            self.assertNotIn(item['id'],[r['id'] for r in catalog.load_catalog('courses')])
        self.assertEqual(self.post(f'/admin-api/catalog/courses/{item_id}',{'action':'show'},'PATCH').status_code,400)
        self.assertEqual(self.post('/admin-api/catalog/courses',self.course()).status_code,400)

    def test_migrations_idempotent_hashes_and_rejected_inputs(self):
        with site.db_connection() as db:
            before=db.execute('SELECT COUNT(*) FROM courses').fetchone()[0]
        site.init_db(); site.init_db()
        with site.db_connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM courses').fetchone()[0],before)
        with admin.connection() as db:
            self.assertNotIn(self.password,str(dict(db.execute('SELECT * FROM admin_account').fetchone())))
            self.assertNotIn(self.pin,str(dict(db.execute('SELECT * FROM admin_settings').fetchone())))
        self.login()
        for change in [{'original_url':'javascript:alert(1)'},{'areas':[{}]},{'review_by':'2001-01-01'},{'certificate_status':'invented'},{'requirements':'wrong'}]:
            self.assertEqual(self.post('/admin-api/catalog/courses',dict(self.course(),**change)).status_code,400)
        with self.assertRaises(ValueError): admin.create_account('another',self.password,self.pin)

    def test_credentials_rotate_and_invalidate_sessions(self):
        self.login()
        token=self.staff.get_cookie(admin.COOKIE).value
        new_password=secrets.token_urlsafe(24)
        response=self.post('/admin-api/account',{'current_password':self.password,'new_password':new_password,'new_pin':''})
        self.assertEqual(response.status_code,200,response.json)
        self.staff.set_cookie(admin.COOKIE,token)
        self.assertEqual(self.staff.get('/admin-api/overview').status_code,401)


    def test_reactivation_cannot_restore_an_unused_old_session(self):
        old=self.client.get_cookie(site.app.config['SESSION_COOKIE_NAME']).value
        self.login()
        self.post('/admin-api/users/1/deactivate')
        self.post('/admin-api/users/1/reactivate')
        self.client.set_cookie(site.app.config['SESSION_COOKIE_NAME'],old)
        self.assertEqual(self.client.get('/api/profile').status_code,401)

    def test_real_import_repetition_respects_admin_hide_and_remove(self):
        import sincronizacao_catalogo as sync
        self.login()
        row=self.course()
        row.update(source_item_id='fixture',is_individual=True,availability_status='open',enrollment_status='open',access_status='free_full')
        source={'id':'admin-fixture','kind':'courses','name':'Fonte sintética de teste'}
        snapshot={'items':[row],'complete':True,'total':1}
        from contextlib import closing
        with closing(sync.connect()) as db,db:
            sync.apply_snapshot(db,source,snapshot,site.now_sp())
        listed=self.staff.get('/admin-api/catalog/courses').json['items']
        item=next(r for r in listed if r['original_url']==row['original_url'])
        self.assertEqual(item['origin'],'auto')
        self.assertEqual(self.post(f"/admin-api/catalog/courses/{item['admin_id']}",dict(self.course(),action='edit'),'PATCH').status_code,400)
        for action in ['hide','remove']:
            self.post(f"/admin-api/catalog/courses/{item['admin_id']}",{'action':action},'PATCH')
            with closing(sync.connect()) as db,db:
                sync.apply_snapshot(db,source,snapshot,site.now_sp())
                sync.apply_snapshot(db,source,snapshot,site.now_sp())
            self.assertFalse(any(r['original_url']==row['original_url'] for r in catalog.load_catalog('courses')))

    def test_deletion_failure_restores_file_and_database(self):
        self.login()
        saved=self.root/'fixture.pdf'; saved.write_bytes(b'fixture')
        with site.db_connection() as db:
            db.execute("INSERT INTO resumes (user_id,kind,saved_name,created_at,updated_at) VALUES (1,'uploaded',?,?,?)",(saved.name,site.timestamp(),site.timestamp()))
            db.execute("CREATE TRIGGER prevent_test_delete BEFORE DELETE ON users BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
        self.post('/admin-api/users/1/deactivate')
        with self.assertRaises(sqlite3.IntegrityError):
            self.post('/admin-api/users/1/delete',{'confirmation':'APAGAR 1'})
        self.assertTrue(saved.exists())
        self.assertEqual(saved.read_bytes(),b'fixture')
        with site.db_connection() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM resumes').fetchone()[0],1)


    def test_manual_job_validation_and_real_public_route(self):
        self.login()
        row=self.course()
        row.update(company='Empresa de teste',location='Curitiba/PR',contract_type='estagio',requirements=['Fixture: matrícula em Administração'])
        for change in [{'location':'São Paulo/SP'},{'contract_type':'senior'},{'requirements':[]}]:
            self.assertEqual(self.post('/admin-api/catalog/jobs',dict(row,**change)).status_code,400)
        response=self.post('/admin-api/catalog/jobs',row)
        self.assertEqual(response.status_code,201,response.json)
        public=self.client.get('/api/jobs?all=1').json['jobs']
        self.assertTrue(any(r['original_url']==row['original_url'] for r in public))

    def test_password_confirmation_uses_same_persistent_block(self):
        self.login()
        for index in range(5):
            response=self.post('/admin-api/account',{'current_password':'incorrect','new_pin':self.pin})
            self.assertEqual(response.status_code,429 if index==4 else 401)
            self.assertEqual(response.json,{'error':'Dados inválidos'})
        self.assertEqual(self.post('/admin-api/account',{'current_password':self.password,'new_pin':self.pin}).status_code,429)

    def test_out_of_date_offers_do_not_count_as_visible(self):
        self.login()
        rows=self.staff.get('/admin-api/catalog/jobs').json['items']
        expired=[r for r in rows if r.get('review_by','') < site.now_sp().date().isoformat()]
        self.assertTrue(expired)
        self.assertTrue(all(not r['public_visible'] for r in expired))
        counts=self.staff.get('/admin-api/overview').json['catalogs']['jobs']
        self.assertEqual(counts['total'],counts['visible']+counts['hidden']+counts['removed']+counts['ineligible'])


    def test_nonascii_csrf_is_rejected_without_server_error(self):
        self.login()
        response=self.staff.post('/admin-api/logout',json={},headers={'X-CSRF-Token':'é'*32})
        self.assertEqual(response.status_code,403)
        self.assertEqual(self.staff.get('/admin-api/overview').status_code,200)


    def test_changed_manual_url_keeps_controls_after_import_and_rejects_duplicate(self):
        self.login()
        self.assertEqual(self.post('/admin-api/catalog/courses',self.course()).status_code,201)
        item=next(r for r in self.staff.get('/admin-api/catalog/courses').json['items'] if r['original_url']==self.course()['original_url'])
        changed=dict(self.course(),original_url='https://example.test/course/changed',action='edit')
        self.assertEqual(self.post(f"/admin-api/catalog/courses/{item['admin_id']}",changed,'PATCH').status_code,200)
        self.assertEqual(self.post('/admin-api/catalog/courses',changed).status_code,400)
        self.post(f"/admin-api/catalog/courses/{item['admin_id']}",{'action':'hide'},'PATCH')
        imported=dict(item,original_url=changed['original_url'],verification_method='sync')
        with site.db_connection() as db:
            before=db.execute('SELECT COUNT(*) FROM courses').fetchone()[0]
            data.mirror(db,'courses',[imported])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM courses').fetchone()[0],before)
        self.assertEqual(data.apply_controls('courses',[imported]),[])


    def test_route_ids_are_bounded_before_sqlite(self):
        self.login()
        for user_id in [0,10**30]:
            self.assertEqual(self.post(f'/admin-api/users/{user_id}/deactivate').status_code,400)
            self.assertEqual(self.post(f'/admin-api/resumes/{user_id}',{},'DELETE').status_code,400)
