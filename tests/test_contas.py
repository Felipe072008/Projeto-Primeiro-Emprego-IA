import io
import json
import sqlite3
import time
import unittest
import zipfile
from unittest.mock import patch

import app as site
import admin
import test_aplicacao


class AccountTests(unittest.TestCase):
    setUp = test_aplicacao.SiteTests.setUp

    def send(self, endpoint, data, method='POST', client=None):
        return (client or self.client).open('/api/account/'+endpoint,method=method,json=data)

    def other_session(self):
        client=site.app.test_client()
        client.environ_base['HTTP_X_REQUESTED_WITH']='FirstJob'
        client.post('/api/auth/login',json={'email':'teste@example.com','password':'teste1234'})
        return client

    def test_name_email_dates_and_no_admin_access(self):
        with patch.object(admin,'connection',side_effect=AssertionError('Must not access admin.db')):
            self.assertEqual(self.send('profile',{'name':'Nome novo'},'PATCH').status_code,200)
            data=self.client.get('/api/account/profile').json
            self.assertEqual(data['user']['name'],'Nome novo')
            self.assertIsNone(data['user']['last_login_at'])
            self.assertEqual(data['terms'][0]['terms_version'],site.TERMS_VERSION)
            response=self.send('email',{'email':'NEW@EXAMPLE.TEST','email_confirmation':'new@example.test','current_password':'teste1234'})
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['user']['email'],'new@example.test')

    def test_password_keeps_current_session_revokes_others_and_logout_all(self):
        other=self.other_session()
        data={'current_password':'teste1234','new_password':'Nova senha segura','password_confirmation':'Nova senha segura'}
        self.assertEqual(self.send('password',data).status_code,200)
        self.assertEqual(self.client.get('/api/account/profile').status_code,200)
        self.assertEqual(other.get('/api/account/profile').status_code,401)
        self.assertEqual(self.send('sessions',{}).status_code,200)
        self.assertEqual(self.client.get('/api/account/profile').status_code,401)

    def test_invalid_inputs_duplicates_and_legacy_login(self):
        for payload in [[],None,{'name':123},{'name':' '},{'name':'x'*121}]:
            self.assertEqual(self.send('profile',payload,'PATCH').status_code,400)
        with site.db_connection() as db:
            db.execute('INSERT INTO users (name,email,password_hash,created_at) VALUES (?,?,?,?)',('Outra','other@example.test',site.generate_password_hash('legacy'),site.timestamp()))
        for email,confirmation,status in [('other@example.test','other@example.test',409),('bad','bad',400),('a@b.com','b@b.com',400)]:
            self.assertEqual(self.send('email',{'email':email,'email_confirmation':confirmation,'current_password':'teste1234'}).status_code,status)
        for password,confirmation in [('short','short'),('x'*257,'x'*257),('teste1234','teste1234'),('newpass88','newpass99')]:
            self.assertEqual(self.send('password',{'current_password':'teste1234','new_password':password,'password_confirmation':confirmation}).status_code,400)
        for password in ['1234567','x'*257,123456789]:
            self.assertEqual(self.client.post('/api/auth/register',json={'name':'Test','email':'new@example.test','password':password,'terms_accepted':True,'terms_version':site.TERMS_VERSION}).status_code,400)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':'other@example.test','password':'legacy'}).status_code,200)

    def test_rate_limit_shared_actions_persistent_user_ip_and_expiry(self):
        now=time.time()
        with patch('contas.time.time',return_value=now):
            for index in range(5):
                response=self.send('export',{'current_password':'wrong'})
                self.assertEqual(response.status_code,429 if index==4 else 401)
            self.assertEqual(self.send('export',{'current_password':'teste1234'}).status_code,429)
            with site.db_connection() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM request_limits WHERE key LIKE 'account:%' AND count=5").fetchone()[0],2)
            response=self.client.post('/api/account/delete',json={'current_password':'teste1234','confirmation':'EXCLUIR'},environ_overrides={'REMOTE_ADDR':'192.0.2.4'})
            self.assertEqual(response.status_code,429)
        with patch('contas.time.time',return_value=now+901):
            response=self.send('export',{'current_password':'teste1234'})
            self.assertEqual(response.status_code,200); response.close()

    def seed_files(self):
        from pathlib import Path
        own=Path(site.UPLOAD_DIR)/'own.pdf';own.write_bytes(b'own fixture')
        other=Path(site.UPLOAD_DIR)/'other.pdf';other.write_bytes(b'other fixture')
        with site.db_connection() as db:
            db.execute('INSERT INTO users (id,name,email,password_hash,created_at) VALUES (2,?,?,?,?)',('Outra','other@example.test','unused',site.timestamp()))
            for uid,name in [(1,own.name),(2,other.name)]:
                db.execute("INSERT INTO resumes(user_id,kind,saved_name,created_at,updated_at) VALUES (?,'uploaded',?,?,?)",(uid,name,site.timestamp(),site.timestamp()))
            db.execute("INSERT INTO resumes(user_id,kind,content_json,created_at,updated_at) VALUES (1,'generated',?,?,?)",(json.dumps({'name':'Meu conteúdo'}),site.timestamp(),site.timestamp()))
        return own,other

    def test_export_owned_data_only_and_delete_cascade_without_admin(self):
        own,other=self.seed_files()
        with patch.object(admin,'connection',side_effect=AssertionError('Must not access admin.db')):
            response=self.send('export',{'current_password':'teste1234'})
            self.assertEqual(response.status_code,200)
            with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
                data=json.loads(archive.read('dados.json'))
                self.assertEqual(len(data['resumes']),2)
                self.assertNotIn('password_hash',json.dumps(data));self.assertNotIn('session_version',json.dumps(data))
                files=[name for name in archive.namelist() if name!='dados.json']
                self.assertEqual(len(files),1);self.assertEqual(archive.read(files[0]),b'own fixture')
            response.close()
            self.assertEqual(self.send('delete',{'current_password':'teste1234','confirmation':'wrong'}).status_code,400)
            self.assertEqual(self.send('delete',{'current_password':'teste1234','confirmation':'EXCLUIR'}).status_code,200)
        self.assertFalse(own.exists());self.assertTrue(other.exists())
        with site.db_connection() as db:
            for table in ['profiles','profile_sections','resumes','terms_acceptances']:
                self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table} WHERE user_id=1').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users WHERE id=2').fetchone()[0],1)
        self.assertEqual(self.client.get('/api/account/profile').status_code,401)

    def test_delete_rollback_restores_files(self):
        own,other=self.seed_files()
        with site.db_connection() as db:
            db.execute("CREATE TRIGGER stop_delete BEFORE DELETE ON users BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.send('delete',{'current_password':'teste1234','confirmation':'EXCLUIR'})
        self.assertTrue(own.exists());self.assertTrue(other.exists())
        self.assertEqual(self.client.get('/api/account/profile').status_code,200)

    def test_auth_status_and_csrf_on_every_action(self):
        other=site.app.test_client()
        for path in ['email','password','sessions','export','delete']:
            self.assertEqual(other.post('/api/account/'+path,json={},headers={'X-Requested-With':'FirstJob'}).status_code,401)
            self.assertEqual(self.client.post('/api/account/'+path,json={},headers={'Origin':'https://other.test'}).status_code,403)
        with site.db_connection() as db: db.execute("UPDATE users SET status='deactivated'")
        self.assertEqual(self.client.get('/api/account/profile').status_code,401)


    def test_ip_limit_applies_to_another_user_and_isolated_other_ip(self):
        with site.db_connection() as db:
            db.execute('INSERT INTO users (name,email,password_hash,created_at) VALUES (?,?,?,?)',('Outra','other@example.test',site.generate_password_hash('OutraSenha123'),site.timestamp()))
        other=site.app.test_client();other.environ_base['HTTP_X_REQUESTED_WITH']='FirstJob'
        other.post('/api/auth/login',json={'email':'other@example.test','password':'OutraSenha123'})
        for _ in range(5): self.send('export',{'current_password':'wrong'})
        self.assertEqual(self.send('export',{'current_password':'OutraSenha123'},client=other).status_code,429)
        response=other.post('/api/account/export',json={'current_password':'OutraSenha123'},environ_overrides={'REMOTE_ADDR':'192.0.2.7'})
        self.assertEqual(response.status_code,200);response.close()
