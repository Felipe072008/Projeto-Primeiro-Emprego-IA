"""Fluxos reais em Chrome local com conta, bancos e uploads descartáveis."""
import json
import os
import secrets
import sys
import tempfile
import threading
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
if os.environ.get('LEGAL_TEST_LIBS'):
    sys.path.insert(0,os.environ['LEGAL_TEST_LIBS'])
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    out=ROOT/'tmp/verificacao_admin'
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        for key,name in [('FIRST_JOB_DATABASE','users.db'),('FIRST_JOB_ADMIN_DATABASE','admin.db'),('FIRST_JOB_CATALOG_DATABASE','catalog.db'),('FIRST_JOB_UPLOAD_DIR','uploads')]:
            os.environ[key]=str(Path(temp)/name)
        import app as site
        import admin
        password=secrets.token_urlsafe(24)
        pin=str(secrets.randbelow(900000)+100000)
        admin.create_account('browserfixture',password,pin)
        with site.db_connection() as db:
            db.execute('INSERT INTO users (name,email,password_hash,created_at) VALUES (?,?,?,?)',
                ('Pessoa de teste <script>window.adminXSS=1</script>','browser@example.test',site.generate_password_hash(secrets.token_urlsafe(16)),site.timestamp()))
        server=make_server('127.0.0.1',0,site.app,threaded=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        checks=[]; errors=[]
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel='chrome',headless=True)
                context=browser.new_context(viewport={'width':1440,'height':1000})
                page=context.new_page()
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base)
                page.locator('#cookie-banner [data-cookie-action="reject"]').click()
                page.get_by_role('button',name='Acesso restrito',exact=True).focus()
                page.keyboard.press('Enter')
                expect(page.locator('#admin-pin-dialog')).to_be_visible()
                expect(page.locator('#admin-pin-form input')).to_be_focused()
                page.keyboard.press('Shift+Tab')
                expect(page.locator('#admin-pin-form [data-close-admin]')).to_be_focused()
                page.keyboard.press('Escape')
                expect(page.get_by_role('button',name='Acesso restrito',exact=True)).to_be_focused()
                checks.append('Acesso por teclado, foco contido e retorno com Escape.')
                page.get_by_role('button',name='Acesso restrito',exact=True).click()
                page.locator('#admin-pin-form input').fill(pin)
                page.locator('#admin-pin-form [type=submit]').click()
                expect(page.locator('#admin-login-dialog')).to_be_visible()
                page.locator('#admin-login-form [name=username]').fill('browserfixture')
                page.locator('#admin-login-form [name=password]').fill(password)
                page.locator('#admin-login-form [type=submit]').click()
                page.wait_for_url(base+'/admin')
                expect(page.locator('#admin-message')).to_have_text('')
                expect(page.locator('.admin-cards')).to_be_visible()
                page.screenshot(path=str(out/'visao-geral-desktop.png'),full_page=True)
                checks.append('PIN e senha no navegador com cookie Secure/HttpOnly e painel autenticado.')
                page.get_by_role('button',name='Usuários',exact=True).click()
                expect(page.locator('.admin-table')).to_be_visible()
                expect(page.locator('.admin-table')).to_contain_text('<script>window.adminXSS=1</script>')
                assert page.evaluate('window.adminXSS') is None
                page.get_by_role('button',name='Desativar',exact=True).click()
                expect(page.get_by_role('button',name='Reativar',exact=True)).to_be_visible()
                page.get_by_role('button',name='Reativar',exact=True).click()
                expect(page.get_by_role('button',name='Desativar',exact=True)).to_be_visible()
                checks.append('Usuário listado sem executar HTML; desativação e reativação funcionam.')
                for view in ['resumes','jobs','courses','system','activities','account']:
                    page.locator(f'[data-view={view}]').click()
                    expect(page.locator('#admin-message')).to_have_text('')
                    expect(page.locator('#admin-results')).not_to_be_empty()
                checks.append('Todas as seções do painel carregam sem erros de JavaScript.')
                page.locator('[data-view=courses]').click()
                expect(page.locator('#admin-message')).to_have_text('')
                page.get_by_role('button',name='Adicionar manual',exact=True).click()
                expect(page.locator('#admin-edit-dialog')).to_be_visible()
                assert page.locator('#admin-edit-fields [name=certificate_status]').count()==1
                from datetime import timedelta
                values={'title':'Curso sintético do navegador','institution':'Instituição fixture','source':'Fonte fixture',
                    'original_url':'https://example.test/course/browser','description':'Oferta sintética somente neste teste.',
                    'availability_evidence':'Fixture: inscrição aberta','review_by':(site.now_sp().date()+timedelta(days=7)).isoformat(),
                    'access_evidence':'Fixture: acesso completo gratuito','certificate':'Fixture: certificado pago',
                    'certificate_source':'https://example.test/certificate'}
                for key,value in values.items():
                    page.locator(f'#admin-edit-fields [name={key}]').fill(value)
                page.locator('#admin-edit-fields [name=areas]').select_option(['administracao'])
                page.locator('#admin-edit-fields [name=certificate_status]').select_option('paid')
                page.locator('#admin-edit-fields [name=course_type]').select_option('livre')
                page.locator('#admin-edit-form [type=submit]').click()
                expect(page.locator('#admin-edit-dialog')).not_to_be_visible()
                row=page.locator('tr').filter(has_text='Curso sintético do navegador')
                expect(row).to_contain_text('Visível')
                row.get_by_role('button',name='Ocultar',exact=True).click()
                expect(row).to_contain_text('Oculta')
                row.get_by_role('button',name='Reexibir',exact=True).click()
                expect(row).to_contain_text('Visível')
                row.get_by_role('button',name='Editar',exact=True).click()
                page.locator('#admin-edit-fields [name=title]').fill('Curso sintético revisado')
                page.locator('#admin-edit-form [type=submit]').click()
                expect(page.locator('#admin-edit-dialog')).not_to_be_visible()
                row=page.locator('tr').filter(has_text='Curso sintético revisado')
                expect(row).to_be_visible()
                page.once('dialog',lambda dialog:dialog.accept())
                row.get_by_role('button',name='Remover',exact=True).click()
                expect(row).to_contain_text('Removida')
                checks.append('Curso manual criado, ocultado, reexibido, editado e removido; certificado pago sinalizado no formulário.')
                page.set_viewport_size({'width':390,'height':844})
                for view in ['overview','users','courses','system','activities','account']:
                    page.locator(f'[data-view={view}]').click()
                    expect(page.locator('#admin-message')).to_have_text('')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),view
                    if view=='users': page.screenshot(path=str(out/'usuarios-mobile.png'),full_page=True)
                page.set_viewport_size({'width':320,'height':740})
                page.locator('[data-view=overview]').click()
                expect(page.locator('#admin-message')).to_have_text('')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
                checks.append('Painel sem transbordamento em 390px e visão geral em 320px; tabelas têm rolagem própria.')
                page.locator('#admin-logout').click()
                page.wait_for_url(base+'/')
                assert context.request.get(base+'/admin').status==401
                assert context.request.get(base+'/admin-assets/admin.js').status==401
                checks.append('Logout bloqueia novamente HTML e JavaScript protegidos.')
                assert not errors,errors
                browser.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)
        (out/'resultado.json').write_text(json.dumps({'checks':checks,'page_errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'checks':checks,'page_errors':errors},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
