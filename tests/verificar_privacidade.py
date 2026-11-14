"""Teste real em Chromium local: armazenamento, cadastro, teclado e telas móveis.

Executar com Playwright disponível no Python de testes (não é dependência do site).
"""
from pathlib import Path
from datetime import datetime
import json
import os
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
if os.environ.get('LEGAL_TEST_LIBS'):
    sys.path.insert(0,os.environ['LEGAL_TEST_LIBS'])
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

OUT=ROOT/'tmp/verificacao_legal'
OUT.mkdir(exist_ok=True,parents=True)
KEY='primeiroemprego.cookie_preferences'


def stored(page):
    return page.evaluate('(key)=>JSON.parse(localStorage.getItem(key))',KEY)


def open_manager(page):
    page.locator('footer [data-cookie-open]').click()
    expect(page.locator('#cookie-dialog')).to_be_visible()


def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')


def main():
    with tempfile.TemporaryDirectory() as temporary:
        for env,filename in [('FIRST_JOB_DATABASE','users.db'),('FIRST_JOB_CATALOG_DATABASE','catalog.db'),('FIRST_JOB_UPLOAD_DIR','uploads')]:
            os.environ[env]=str(Path(temporary)/filename)
        import app as site
        site.app.config.update(TESTING=True,SESSION_COOKIE_SECURE=False)
        server=make_server('127.0.0.1',0,site.app,threaded=True)
        base=f'http://127.0.0.1:{server.server_port}'
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        results=[]
        errors=[]
        urls=[]
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(channel='chrome',headless=True)
                context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                page=context.new_page()
                page.on('pageerror',lambda error:errors.append(str(error)))
                context.on('request',lambda request:urls.append(request.url))
                page.goto(base)
                expect(page.locator('#cookie-banner')).to_be_visible()
                expect(page.locator('#cookie-functionality')).not_to_be_checked()
                page.screenshot(path=str(OUT/'banner-desktop.png'))
                results.append('1. Primeira visita mostra banner; opcionais desativados.')
                page.locator('#cookie-banner [data-cookie-action="accept"]').click()
                assert stored(page)['functionality'] is True
                assert stored(page)['analytics'] is False and stored(page)['marketing'] is False
                expect(page.locator('#cookie-banner')).to_be_hidden()
                results.append('2. Aceitar Todos salva somente a categoria funcional em uso.')
                page.reload()
                expect(page.locator('#cookie-banner')).to_be_hidden()
                assert stored(page)['functionality'] is True
                results.append('5. Preferências persistem após recarga.')
                open_manager(page)
                close=page.locator('[data-cookie-close]')
                expect(close).to_be_focused()
                page.keyboard.press('Shift+Tab')
                expect(page.locator('#cookie-dialog [data-cookie-action="reject"]')).to_be_focused()
                page.keyboard.press('Tab')
                expect(close).to_be_focused()
                page.evaluate("sessionStorage.setItem('filters-jobs','q=temporario');sessionStorage.setItem('filters-courses','q=temporario')")
                page.locator('#cookie-dialog [data-cookie-action="reject"]').click()
                assert stored(page)['functionality'] is False
                assert page.evaluate("sessionStorage.getItem('filters-jobs')") is None
                assert page.evaluate("sessionStorage.getItem('filters-courses')") is None
                expect(page.locator('footer [data-cookie-open]')).to_be_focused()
                results.append('6. Rodapé reabre; revogação remove filtros e devolve foco. Modal contém o foco pelo teclado.')
                open_manager(page)
                page.locator('#cookie-functionality').check()
                page.locator('#cookie-preferences-form button[type="submit"]').click()
                assert stored(page)['functionality'] is True
                open_manager(page)
                page.locator('#cookie-functionality').uncheck()
                page.locator('#cookie-preferences-form button[type="submit"]').click()
                assert stored(page)['functionality'] is False
                results.append('4. Preferência específica é salva pelo formulário.')

                # Outro visitante rejeita antes de ter qualquer conta ou cookie de autenticação.
                guest=browser.new_context(viewport={'width':1440,'height':1000})
                registration=guest.new_page()
                registration.on('pageerror',lambda error:errors.append(str(error)))
                registration.goto(base)
                registration.locator('#cookie-banner [data-cookie-action="reject"]').click()
                assert stored(registration)['functionality'] is False
                assert guest.cookies()==[]
                results.append('3. Rejeitar Opcionais não cria cookie opcional.')
                registration.locator('[data-show-auth="register"]').click()
                form=registration.locator('#register-form')
                expect(form.locator('[name="terms_accepted"]')).not_to_be_checked()
                form.locator('[name="name"]').fill('Perfil sintético de privacidade')
                form.locator('[name="email"]').fill('privacy-browser@example.test')
                form.locator('[name="password"]').fill('TestePrivacidade123!')
                form.locator('button[type="submit"]').click()
                expect(registration.locator('#register-card')).to_be_visible()
                assert form.evaluate('(form)=>form.checkValidity()') is False
                with guest.expect_page() as popup:
                    form.locator('a[href="/termos-de-uso"]').click()
                terms=popup.value
                terms.wait_for_load_state()
                expect(terms.locator('h1')).to_have_text('Termos de Uso — PrimeiroEmprego IA')
                assert '13/11/2026' in terms.locator('main').inner_text()
                terms.close()
                with guest.expect_page() as popup:
                    form.locator('a[href="/politica-de-privacidade"]').click()
                privacy=popup.value
                privacy.wait_for_load_state()
                expect(privacy.locator('h1')).to_have_text('Política de Privacidade — PrimeiroEmprego IA')
                privacy.close()
                results.append('7 e 8. Páginas públicas e links do cadastro abrem sem login; Termos desmarcados impedem cadastro.')
                form.locator('[name="terms_accepted"]').check()
                with registration.expect_response(lambda r:r.url.endswith('/api/auth/register') and r.request.method=='POST') as response:
                    form.locator('button[type="submit"]').click()
                assert response.value.status==201,response.value.text()
                expect(registration.locator('#app-view')).to_be_visible()
                assert stored(registration)['functionality'] is False
                assert {c['name'] for c in guest.cookies()}=={'session'}
                results.append('12. Cadastro funciona com todos os opcionais rejeitados e registra aceite separado.')
                registration.locator('[data-route="jobs"]').click()
                registration.locator('#jobs-filters input[name="q"]').fill('Curitiba')
                with registration.expect_response(lambda r:'/api/jobs?' in r.url):
                    registration.locator('#jobs-filters button:not([type="reset"])').click()
                assert registration.evaluate("sessionStorage.getItem('filters-jobs')") is None
                assert guest.request.get(base+'/api/me').json()['authenticated'] is True
                results.append('9. Perfil, login e busca continuam acessíveis após rejeição; filtros não são gravados.')
                open_manager(registration)
                registration.locator('#cookie-functionality').check()
                registration.locator('#cookie-preferences-form button[type="submit"]').click()
                with registration.expect_response(lambda r:'/api/jobs?' in r.url):
                    registration.locator('#jobs-filters button:not([type="reset"])').click()
                assert 'q=Curitiba' in registration.evaluate("sessionStorage.getItem('filters-jobs')")
                registration.reload()
                expect(registration.locator('#jobs-filters input[name="q"]')).to_have_value('Curitiba')
                open_manager(registration)
                registration.locator('#cookie-dialog [data-cookie-action="reject"]').click()
                assert registration.evaluate("sessionStorage.getItem('filters-jobs')") is None
                assert guest.request.get(base+'/api/me').json()['authenticated'] is True
                results.append('Funcionalidade real: lembrar filtros depende da escolha; revogar preserva autenticação.')

                # Verifica todas as telas e modais principais com o mesmo perfil em largura de celular.
                registration.set_viewport_size({'width':390,'height':844})
                for route in ('dashboard','profile','jobs','courses','resume'):
                    registration.locator('#mobile-menu').click()
                    registration.locator(f'[data-route="{route}"]').click()
                    expect(registration.locator(f'#page-{route}')).to_have_class('page active')
                    no_overflow(registration)
                registration.locator('#open-builder').click()
                expect(registration.locator('#builder-modal')).to_be_visible()
                no_overflow(registration)
                registration.keyboard.press('Escape')
                open_manager(registration)
                registration.screenshot(path=str(OUT/'preferencias-mobile.png'))
                registration.keyboard.press('Escape')
                for route in ('/termos-de-uso','/politica-de-privacidade','/cookies'):
                    registration.goto(base+route)
                    no_overflow(registration)
                    expect(registration.locator('h1')).to_be_visible()
                registration.screenshot(path=str(OUT/'cookies-mobile.png'))
                results.append('10. Cinco telas do site, gerador de currículo e páginas legais acessíveis em 390x844 sem rolagem horizontal.')
                # Também cobre a menor largura suportada pelo layout existente.
                registration.set_viewport_size({'width':320,'height':720})
                registration.reload()
                no_overflow(registration)

                # Expiração e registro adulterado exigem uma nova escolha.
                registration.evaluate('(key)=>{let p=JSON.parse(localStorage.getItem(key));p.version="antiga";localStorage.setItem(key,JSON.stringify(p));}',KEY)
                registration.reload()
                expect(registration.locator('#cookie-banner')).to_be_visible()
                assert stored(registration) is None
                registration.locator('#cookie-banner [data-cookie-action="reject"]').click()
                results.append('Preferência de versão antiga é descartada e solicita nova escolha.')
                registration.evaluate('(key)=>{let p=JSON.parse(localStorage.getItem(key));const lifetime=180*86400000;const saved=Date.now()-lifetime-1000;p.saved_at=new Date(saved).toISOString();p.expires_at=new Date(saved+lifetime).toISOString();localStorage.setItem(key,JSON.stringify(p));}',KEY)
                registration.reload()
                expect(registration.locator('#cookie-banner')).to_be_visible()
                assert stored(registration) is None
                results.append('Escolha expirada após 180 dias é descartada em novo acesso.')
                blocked=browser.new_context()
                blocked.add_init_script('Storage.prototype.setItem=function(){throw new DOMException("Armazenamento bloqueado","SecurityError")}')
                unavailable=blocked.new_page()
                unavailable.on('pageerror',lambda error:errors.append(str(error)))
                unavailable.goto(base)
                unavailable.locator('#cookie-banner [data-cookie-action="accept"]').click()
                expect(unavailable.locator('#cookie-status')).to_contain_text('O navegador impediu salvar')
                assert stored(unavailable) is None
                unavailable.reload()
                expect(unavailable.locator('#cookie-banner')).to_be_visible()
                blocked.close()
                results.append('Armazenamento bloqueado é informado e não simula persistência após recarga.')
                page.wait_for_function('document.fonts.status === "loaded"')
                assert all(url.startswith(base) for url in urls),[url for url in urls if not url.startswith(base)]
                assert page.evaluate('document.fonts.check(\'16px "DM Sans"\')')
                results.append('11. Nenhuma requisição de rastreamento/terceiro; fontes locais e somente recursos da própria origem.')
                assert errors==[],errors
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
        report={'tested_at':datetime.now().isoformat(),'scenarios':results,'browser_errors':errors,'result':'passed'}
        (OUT/'resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
