"""Teste de navegador com conta descartável e bancos temporários."""
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
if os.environ.get('LEGAL_TEST_LIBS'): sys.path.insert(0,os.environ['LEGAL_TEST_LIBS'])
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    out=ROOT/'tmp/verificacao_conta';out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        for key,name in [('FIRST_JOB_DATABASE','users.db'),('FIRST_JOB_ADMIN_DATABASE','admin.db'),('FIRST_JOB_CATALOG_DATABASE','catalog.db'),('FIRST_JOB_UPLOAD_DIR','uploads')]:
            os.environ[key]=str(Path(temp)/name)
        import app as site
        server=make_server('127.0.0.1',0,site.app,threaded=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        errors=[];checks=[]
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel='chrome',headless=True)
                context=browser.new_context(viewport={'width':1440,'height':1000})
                response=context.request.post(base+'/api/auth/register',headers={'X-Requested-With':'FirstJob'},data={'name':'Teste conta','email':'conta@example.test','password':'Inicial12345','terms_accepted':True,'terms_version':site.TERMS_VERSION})
                assert response.status==201
                page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base)
                page.locator('#cookie-banner [data-cookie-action="reject"]').click()
                page.get_by_role('button',name='Abrir Minha conta').focus();page.keyboard.press('Space')
                expect(page.locator('#page-account')).to_have_class('page active')
                expect(page.locator('#account-name-form [name=name]')).to_have_value('Teste conta')
                assert page.locator('.sidebar [data-route=account]').count()==0
                page.locator('#account-name-form [name=name]').fill('Nome atualizado')
                page.locator('#account-name-form [type=submit]').click()
                expect(page.locator('#account-name')).to_have_text('Nome atualizado')
                expect(page.locator('#account-initial')).to_have_text('N')
                checks.append('Bloco inteiro acessível por teclado abre a página; nome e inicial atualizam imediatamente.')
                form=page.locator('#account-email-form')
                form.locator('[name=email]').fill('NOVO@example.test');form.locator('[name=email_confirmation]').fill('novo@example.test');form.locator('[name=current_password]').fill('Inicial12345')
                form.locator('[type=submit]').click()
                expect(page.locator('#account-current-email')).to_have_text('novo@example.test')
                form=page.locator('#account-password-form')
                form.locator('[name=current_password]').fill('Inicial12345');form.locator('[name=new_password]').fill('NovaSenha12345');form.locator('[name=password_confirmation]').fill('NovaSenha12345')
                form.locator('[data-password-toggle="account-new_password"]').click()
                expect(form.locator('[name=new_password]')).to_have_attribute('type','text')
                form.locator('[type=submit]').click()
                expect(form.locator('[role=status]')).to_contain_text('Senha atualizada')
                assert context.request.get(base+'/api/account/profile').status==200
                checks.append('E-mail normalizado e senha alterados; mostrar senha e manutenção da sessão funcionam.')
                page.locator('#page-account [data-cookie-open]').click();expect(page.locator('#cookie-dialog')).to_be_visible();page.keyboard.press('Escape')
                form=page.locator('#account-export-form');form.locator('[name=current_password]').fill('NovaSenha12345')
                with page.expect_download() as download: form.locator('[type=submit]').click()
                downloaded=download.value;downloaded.save_as(out/'fixture-dados.zip')
                import zipfile
                with zipfile.ZipFile(out/'fixture-dados.zip') as archive: assert json.loads(archive.read('dados.json'))['account']['email']=='novo@example.test'
                checks.append('Preferências existentes reabrem e exportação ZIP baixa os dados da própria conta.')
                page.screenshot(path=str(out/'desktop.png'),full_page=True)
                for width in [390,320]:
                    page.set_viewport_size({'width':width,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                page.screenshot(path=str(out/'mobile.png'),full_page=True)
                page.locator('#account-end-sessions').click();expect(page.locator('#auth-view')).to_be_visible()
                form=page.locator('#login-form');form.locator('[name=email]').fill('novo@example.test');form.locator('[name=password]').fill('NovaSenha12345');form.locator('[type=submit]').click()
                expect(page.locator('#app-view')).to_be_visible();page.get_by_role('button',name='Abrir Minha conta').click()
                expect(page.locator('#account-current-email')).to_have_text('novo@example.test')
                form=page.locator('#account-delete-form');form.locator('[name=current_password]').fill('NovaSenha12345');form.locator('[name=confirmation]').fill('EXCLUIR');form.locator('[type=submit]').click()
                expect(page.locator('#auth-view')).to_be_visible()
                assert context.request.get(base+'/api/account/profile').status==401
                with site.db_connection() as db: assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0
                checks.append('Sair de todos, novo login e exclusão definitiva funcionam; layout sem transbordamento em 390px e 320px.')
                assert not errors,errors
                browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
        (out/'resultado.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(checks,ensure_ascii=False))


if __name__=='__main__':main()
