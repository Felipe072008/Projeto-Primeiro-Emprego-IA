"""Chrome: editor completo e publicação apenas em bancos descartáveis."""
import io
import json
import os
import secrets
import sys
import tempfile
import threading
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
if os.environ.get('LEGAL_TEST_LIBS'): sys.path.insert(0,os.environ['LEGAL_TEST_LIBS'])
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from PIL import Image


def main():
    out=ROOT/'tmp/verificacao_editor'; out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        for key,name in [('FIRST_JOB_DATABASE','users.db'),('FIRST_JOB_ADMIN_DATABASE','admin.db'),
                         ('FIRST_JOB_CATALOG_DATABASE','catalog.db'),('FIRST_JOB_UPLOAD_DIR','uploads')]:
            os.environ[key]=str(Path(temp)/name)
        import app as site
        import admin
        password=secrets.token_urlsafe(20); admin.create_account('browserfixture',password,'123456')
        server=make_server('127.0.0.1',0,site.app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel='chrome',headless=True)
                context=browser.new_context(viewport={'width':1440,'height':1000})
                result=context.request.get(base+'/admin-access').json();csrf=result['csrf']
                headers={'X-Requested-With':'FirstJob','X-CSRF-Token':csrf}
                result=context.request.post(base+'/admin-access/pin',data={'pin':'123456'},headers=headers).json();headers['X-CSRF-Token']=result['csrf']
                result=context.request.post(base+'/admin-access/login',data={'username':'browserfixture','password':password},headers=headers).json()
                page=context.new_page(); errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base+'/admin');page.get_by_role('link',name='Editar site',exact=True).click()
                expect(page.locator('#editor-status')).to_have_text('Rascunho carregado.')
                def preview(): return page.frame_locator('#editor-frame')
                preview().locator('[data-edit-key="login.title"]').click()
                preview().get_by_role('textbox',name='Editar texto',exact=True).fill('Seu futuro começa aqui — teste')
                preview().get_by_role('button',name='Confirmar texto',exact=True).click()
                expect(preview().locator('[data-edit-key="login.title"]')).to_have_text('Seu futuro começa aqui — teste')
                public=context.new_page();public.goto(base);expect(public.locator('[data-edit-key="login.title"]')).not_to_have_text('Seu futuro começa aqui — teste')
                page.get_by_label('Primária',exact=True).fill('#2452a0');page.get_by_label('Primária',exact=True).dispatch_event('change')
                expect(page.locator('#editor-status')).to_have_text('Há alterações não salvas.')
                page.get_by_label('Fonte dos títulos',exact=True).select_option('DM Sans')
                expect(preview().locator('h1[data-edit-key="login.title"]')).to_have_css('font-family','"DM Sans", sans-serif')
                expect(preview().locator('#login-form [type=submit]')).to_have_css('background-color','rgb(36, 82, 160)')
                page.get_by_label('Secundária',exact=True).fill('#153567')
                page.get_by_label('Secundária',exact=True).dispatch_event('change')
                stream=io.BytesIO();Image.new('RGB',(64,20),'blue').save(stream,'PNG')
                page.locator('#editor-logo-form [name=file]').set_input_files({'name':'marca.png','mimeType':'image/png','buffer':stream.getvalue()})
                page.locator('#editor-logo-form [name=alt]').fill('Marca de exemplo')
                page.get_by_role('button',name='Enviar logo',exact=True).click()
                expect(preview().get_by_role('img',name='Marca de exemplo').first).to_be_visible()
                page.locator('#editor-page').select_option('dashboard')
                expect(preview().locator('[data-section-key="dashboard.intro"]')).to_be_visible()
                expect(preview().locator('.button--dark').first).to_have_css('background-color','rgb(21, 53, 103)')
                rows=page.locator('#editor-sections>.editor-row')
                rows.nth(0).get_by_role('button',name='Descer',exact=True).click()
                expect(rows.nth(0)).to_contain_text('Atalhos')
                rows.nth(2).get_by_role('button',name='Ocultar',exact=True).click()
                expect(preview().locator('[data-section-key="dashboard.guidance"]')).not_to_be_visible()
                checks=['Texto editado na prévia; rascunho invisível ao público; cor, fonte e logo alterados.','Seção ocultada e reordenada com botões.']
                for kind in ('text','notice','button','faq'):
                    page.locator('#editor-block-type').select_option(kind);page.get_by_role('button',name='Adicionar bloco',exact=True).click()
                    dialog=page.locator('#editor-dialog');expect(dialog).to_be_visible()
                    if kind=='button':
                        dialog.get_by_label('Rótulo do botão',exact=True).fill('Ver cursos de exemplo')
                        dialog.get_by_label('Link http/https ou rota interna permitida',exact=True).fill('/#courses')
                    elif kind=='faq':
                        dialog.get_by_label('Pergunta',exact=True).fill('Como começar?');dialog.get_by_label('Resposta',exact=True).fill('Preencha seu perfil.')
                    else: dialog.get_by_label('Título',exact=True).fill('Bloco '+kind)
                    dialog.get_by_role('button',name='Confirmar bloco',exact=True).click();expect(dialog).not_to_be_visible()
                expect(preview().locator('[data-slot=dashboard]>.site-block')).to_have_count(4)
                page.get_by_role('button',name='Salvar rascunho',exact=True).click();expect(page.locator('#editor-status')).to_have_text('Rascunho salvo.')
                page.get_by_role('button',name='Publicar',exact=True).click();expect(page.locator('#editor-dialog')).to_contain_text('Tema, Textos, Seções, Blocos')
                page.get_by_role('button',name='Confirmar publicação',exact=True).click();expect(page.locator('#editor-status')).to_contain_text('Versão publicada')
                public.reload();expect(public.locator('[data-edit-key="login.title"]')).to_have_text('Seu futuro começa aqui — teste')
                expect(public.locator('[data-slot=dashboard]>.site-block')).to_have_count(4)
                expect(public.locator('.site-logo').first).to_have_attribute('alt','Marca de exemplo')
                page.screenshot(path=str(out/'desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844});page.locator('#editor-width').select_option('mobile')
                expect(page.locator('#editor-frame')).to_have_class('mobile')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(out/'mobile.png'),full_page=True)
                page.get_by_role('button',name='Histórico',exact=True).click();page.get_by_role('button',name='Desfazer última publicação',exact=True).click()
                expect(page.locator('#editor-status')).to_have_text('Última publicação desfeita.')
                public.reload();expect(public.locator('[data-edit-key="login.title"]')).not_to_have_text('Seu futuro começa aqui — teste')
                checks.append('Quatro tipos de bloco publicados, conferidos no HTML público e publicação desfeita; editor responsivo em 390px.')
                assert not errors,errors
                (out/'resultado.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
                browser.close()
        finally: server.shutdown();thread.join()
    print('Editor: Chrome desktop/celular aprovado.')


if __name__=='__main__':main()
