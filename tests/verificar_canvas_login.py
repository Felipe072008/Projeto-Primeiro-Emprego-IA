"""Verificação das sete páginas em dois dispositivos, com bancos descartáveis."""
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
if os.getenv('LEGAL_TEST_LIBS'): sys.path.insert(0,os.environ['LEGAL_TEST_LIBS'])
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server

with tempfile.TemporaryDirectory() as tmp:
    for key,name in [('FIRST_JOB_DATABASE','site.db'),('FIRST_JOB_ADMIN_DATABASE','admin.db'),('FIRST_JOB_UPLOAD_DIR','uploads'),('FIRST_JOB_CATALOG_DATABASE','catalog.db')]:
        os.environ[key]=str(Path(tmp)/name)
    import app,admin
    from canvas_login import validate_canvas
    with admin.connection() as db: token,csrf=admin.new_session(db,'admin')
    srv=make_server('127.0.0.1',0,app.app,threaded=True)
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{srv.server_port}'
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='chrome')
            ctx=browser.new_context(viewport={'width':1440,'height':900})
            ctx.add_cookies([{'name':admin.COOKIE,'value':token,'url':url}])
            page=ctx.new_page();page.on('dialog',lambda d:d.accept());page.goto(url+'/admin/site')
            expect(page.locator('#status')).to_have_text('Publicado')
            page.get_by_role('button',name='Fechar',exact=True).click()
            page.locator('summary',has_text='Adicionar').click()
            page.locator('#glass').click()
            expect(page.get_by_label('Opacidade (%)')).to_be_visible()
            page.locator('#props summary').click()
            page.get_by_label('Horizontal').fill('21');page.get_by_label('Horizontal').press('Tab')
            page.locator('#undo').click();expect(page.get_by_label('Horizontal')).to_have_value('0')
            page.locator('#redo').click();expect(page.get_by_label('Horizontal')).to_have_value('21')
            frame=page.frame_locator('#frame')
            frame.locator('[data-canvas="title"]').click()
            expect(page.locator('#props strong')).to_have_text('Título principal')
            title=frame.locator('[data-canvas=title] h1')
            title.dblclick()
            title.fill('Título de teste')
            title.press('Tab')
            expect(title).to_have_text('Título de teste')
            page.locator('#undo').click()
            expect(title).to_contain_text('seu futuro')
            handle=frame.locator('[data-handle=e]').first.bounding_box()
            x=handle['x']+handle['width']/2;y=handle['y']+handle['height']/2
            width=int(page.get_by_label('Largura').input_value())
            page.mouse.move(x,y);page.mouse.down();page.mouse.move(x-30,y,steps=5);page.mouse.up()
            assert int(page.get_by_label('Largura').input_value())<width
            if not page.get_by_label('Largura').is_visible():page.locator('#props summary').click()
            page.get_by_label('Largura').fill('550');page.get_by_label('Largura').press('Tab')
            page.locator('#layers').get_by_role('button',name='Ilustração',exact=True).click()
            art=frame.locator('[data-canvas=art]').bounding_box()
            cx=art['x']+art['width']/2;cy=art['y']+art['height']/2
            page.mouse.move(cx,cy);page.mouse.down();page.mouse.move(cx+2,cy+12,steps=3)
            expect(frame.locator('.canvas-guide').first).to_be_visible()
            page.mouse.up()
            page.get_by_role('button',name='Card de vidro',exact=True).first.click()
            expect(page.locator('#status')).to_contain_text('Rascunho salvo')
            out=ROOT/'tmp/verificacao_canvas';out.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(out/'fase-1.png'))
            page.locator('#publish').click();expect(page.locator('#status')).to_have_text('Publicado')
            value=ctx.request.get(url+'/api/site-content').json()
            layout=value['theme']['login_desktop'];validate_canvas(layout)
            layout['art']['x']=560
            try: validate_canvas(layout)
            except ValueError: pass
            else: raise AssertionError('Coordenada fora da área aceita')
            pub=ctx.new_page()
            for size in (1920,1366,768,390,360):
                pub.set_viewport_size({'width':size,'height':900});pub.goto(url)
                expect(pub.locator('[data-canvas=glass]')).to_have_css('display','block' if size>=900 else 'none')
                assert pub.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#device').select_option('mobile')
            expect(page.locator('#generate')).to_be_visible()
            page.locator('#generate').click()
            page.locator('#layers').get_by_role('button',name='Título principal').click()
            x_before=int(page.get_by_label('Horizontal').input_value())
            page.keyboard.press('Shift+ArrowDown')
            before=int(page.get_by_label('Altura mínima').input_value())
            page.keyboard.press('Alt+ArrowDown')
            expect(page.get_by_label('Altura mínima')).to_have_value(str(before+1))
            page.locator('#layers').get_by_role('button',name='Card de vidro').click(modifiers=['Shift'])
            page.get_by_role('button',name='Alinhar à esquerda').click()
            page.locator('#layers').get_by_role('button',name='Card de vidro').click()
            page.keyboard.press('Control+d')
            page.keyboard.press('Control+c');page.keyboard.press('Control+v')
            assert page.locator('#layers .layer-row>button').count()==5
            page.keyboard.press('Delete')
            assert page.locator('#layers .layer-row>button').count()==4
            page.locator('#undo').click();assert page.locator('#layers .layer-row>button').count()==5
            page.locator('#redo').click()
            page.locator('#preview').click()
            expect(page.locator('#preview')).to_have_text('Voltar à edição')
            assert not frame.locator('.edit-decoration').count()
            page.locator('#preview').click()
            page.screenshot(path=str(out/'celular.png'))
            page.locator('#publish').click();expect(page.locator('#status')).to_have_text('Publicado')
            theme=ctx.request.get(url+'/api/site-content').json()['theme']
            assert theme['login_mobile'] and theme['login_desktop']
            for size in (1920,1366,768,390,360):
                pub.set_viewport_size({'width':size,'height':900});pub.goto(url)
                expect(pub.locator('[data-layout-board="login"]')).to_be_visible()
                assert pub.evaluate("""() => {
                  const b=document.querySelector('[data-layout-board]').getBoundingClientRect();
                  const f=document.querySelector('.auth-panel').getBoundingClientRect();
                  return document.documentElement.scrollWidth<=innerWidth &&
                    (b.right<=f.left+1 || b.bottom<=f.top+1 || f.right<=b.left+1);
                }""")
            page.locator('#reset').click();page.locator('#publish').click()
            expect(page.locator('#status')).to_have_text('Publicado')
            assert ctx.request.get(url+'/api/site-content').json()['theme']['login_mobile'] is None
            page.locator('#device').select_option('desktop');expect(page.locator('#status')).to_have_text('Publicado')
            page.locator('#reset').click();page.locator('#publish').click()
            expect(page.locator('#status')).to_have_text('Publicado')
            assert ctx.request.get(url+'/api/site-content').json()['theme']['login_desktop'] is None
            # As páginas da SPA são exercitadas com uma conta descartável, fora da prévia.
            user=browser.new_context()
            reg=user.request.post(url+'/api/auth/register',headers={'X-Requested-With':'FirstJob'},
                data={'name':'Teste editor','email':'editor@example.test','password':'TesteEditor12345',
                      'terms_accepted':True,'terms_version':app.TERMS_VERSION})
            assert reg.status==201
            public=user.new_page()
            for page_id in ('dashboard','profile','jobs','courses','resume','account'):
                page.locator('#page').select_option(page_id)
                expect(page.locator('#layers .layer-row>button').first).to_be_visible()
                page.locator('#layers .layer-row>button').first.click()
                page.keyboard.press('ArrowDown')
                expect(page.locator('#status')).to_contain_text('Rascunho salvo')
                if page_id=='dashboard':
                    page.screenshot(path=str(out/'visao-geral.png'))
                page.locator('#device').select_option('mobile')
                page.locator('#generate').click()
                expect(page.locator('#status')).to_contain_text('Rascunho salvo')
                page.locator('#publish').click();expect(page.locator('#status')).to_have_text('Publicado')
                public.set_viewport_size({'width':1366,'height':900})
                public.goto(url+'/#'+page_id);public.reload()
                board=public.locator('[data-layout-board="'+page_id+'"]')
                expect(board).to_be_visible()
                for size in (1920,1366,768,390,360):
                    public.set_viewport_size({'width':size,'height':900})
                    expect(board).to_be_visible()
                    assert board.evaluate('b=>[...b.children].every(n=>{const r=n.getBoundingClientRect(),a=b.getBoundingClientRect();return !r.width || (r.left>=a.left-1 && r.right<=a.right+1 && r.bottom<=a.bottom+1)})'),(page_id,size)
                    assert public.evaluate('document.documentElement.scrollWidth<=innerWidth'),(page_id,size)
                page.locator('#device').select_option('desktop')
                expect(page.locator('#status')).to_have_text('Publicado')
                if page_id=='dashboard':
                    public.set_viewport_size({'width':1366,'height':900})
                    board.locator('[data-go=profile]').first.click()
                    expect(public.locator('#page-profile')).to_be_visible()
            user.close()
            browser.close()
    finally:srv.shutdown()
print('Canvas, publicação e restauração verificados nas sete páginas e cinco larguras.')
