// Executar contra servidor local de teste com banco de usuários separado.
// As rotas e os dados do catálogo não são substituídos por mocks.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.CATALOG_TEST_URL || 'http://127.0.0.1:5057';
const out = process.env.CATALOG_TEST_OUTPUT || path.join(__dirname,'..','tmp','qa_catalogo');
fs.mkdirSync(out,{recursive:true});
(async()=>{
  const browser = await chromium.launch({headless:true,channel:'chrome'});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
    const page = await context.newPage();
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    const registration=await context.request.post(base+'/api/auth/register',{
      headers:{'X-Requested-With':'FirstJob'},data:{terms_accepted:true,terms_version:'2026-11-13',name:'Teste de catálogo',email:`catalogo-${Date.now()}@example.org`,password:'CatalogoTeste123!'}});
    assert.ok(registration.ok(),await registration.text());
    await page.goto(base+'/#profile');
    const saveArea = async area => {
      if (await page.locator('#page-profile').evaluate(el=>!el.classList.contains('active'))) {
        await page.locator('[data-route="profile"]').click();
      }
      await page.locator('#profile-block-goals [data-profile-section="goals"]').click();
      await page.locator('#profile-field-sector').selectOption(area);
      const response = page.waitForResponse(r=>r.url().endsWith('/api/profile/goals') && r.request().method()==='PATCH');
      await page.locator('#profile-form button[type="submit"]').click();
      const result=await response;
      assert.equal(result.status(),200,await result.text());
      assert.equal((await result.json()).profile.sections.goals.sector,area);
      await page.locator('#profile-modal.hidden').waitFor({state:'attached'});
    };
    const loadCourses = async () => {
      const response=page.waitForResponse(r=>r.url().includes('/api/courses?'));
      await page.locator('[data-route="courses"]').click();
      const data=await (await response).json();
      await page.waitForFunction(()=>document.querySelector('#courses-list').getAttribute('aria-busy')==='false');
      assert.deepEqual(await page.locator('#courses-list h2').allTextContents(),data.courses.map(item=>item.title));
      assert.deepEqual(await page.locator('#courses-external a').evaluateAll(links=>links.map(a=>a.href)),data.external_links.map(link=>link.url));
      return data;
    };
    await saveArea('Administração');
    let admin=await loadCourses();
    assert.ok(admin.personalized && admin.total>0);
    assert.equal(admin.interest,'Administração');
    assert.equal(await page.locator('#courses-filters select[name="all"]').inputValue(),'0');
    assert.ok(admin.courses.every(item=>item.match==='direct'));
    assert.ok(admin.external_links.some(link=>link.source_id==='fundacao_bradesco'));
    assert.ok(admin.external_links.some(link=>link.source_id==='senai_sp'));
    assert.ok(admin.external_links.some(link=>link.source_id==='coursera'));
    await page.screenshot({path:path.join(out,'administracao-real.png'),fullPage:true});
    const allResponse=page.waitForResponse(r=>r.url().includes('/api/courses?')&&new URL(r.url()).searchParams.get('all')==='1');
    await page.locator('#courses-filters select[name="all"]').selectOption('1');
    const all=await (await allResponse).json();
    await page.waitForFunction(()=>document.querySelector('#courses-context').textContent.includes('Todas as áreas — filtro ativo'));
    assert.ok(all.total>admin.total && !all.personalized);
    await saveArea('Saúde');
    const health=await loadCourses();
    assert.equal(health.interest,'Saúde');
    assert.ok(health.personalized && health.total>0);
    assert.notDeepEqual(health.courses.map(x=>x.id),admin.courses.map(x=>x.id));
    assert.ok(health.courses.every(item=>item.areas.includes('saude')));
    assert.equal(await page.locator('#courses-filters select[name="all"]').inputValue(),'0');
    // Reproduz uma sessão anterior, sem alterar respostas do backend.
    await page.evaluate(()=>sessionStorage.setItem('filters-courses','all=1&q=&type='));
    const reloadResponse=page.waitForResponse(r=>r.url().includes('/api/courses?'));
    await page.reload();
    const reloaded=await (await reloadResponse).json();
    assert.ok(reloaded.personalized);
    assert.equal(await page.locator('#courses-filters select[name="all"]').inputValue(),'0');
    await page.waitForFunction(()=>document.querySelector('#courses-list').getAttribute('aria-busy')==='false');
    await page.screenshot({path:path.join(out,'saude-real.png'),fullPage:true});
    const noMatch=page.waitForResponse(r=>r.url().includes('/api/courses?'));
    await page.locator('#courses-filters input[name="q"]').fill('zzz-sem-correspondencia-qa');
    await page.locator('#courses-filters button[type="submit"], #courses-filters button:not([type])').click();
    assert.equal((await (await noMatch).json()).result_status,'no_matches');
    await page.getByText('Nenhum resultado corresponde aos filtros aplicados.',{exact:false}).waitFor();
    const jobsResponse=page.waitForResponse(r=>r.url().includes('/api/jobs?'));
    await page.locator('[data-route="jobs"]').click();
    const jobs=await (await jobsResponse).json();
    await page.waitForFunction(()=>document.querySelector('#jobs-list').getAttribute('aria-busy')==='false');
    if(jobs.result_status==='no_data') {
      assert.ok((await page.locator('#jobs-list').innerText()).startsWith('O catálogo está sem vagas verificadas'));
      assert.ok(!(await page.locator('#jobs-list').innerText()).includes('Nenhuma vaga corresponde'));
    }
    assert.ok(jobs.external_links.some(link=>link.source_id==='gupy'));
    assert.ok(jobs.external_links.some(link=>link.source_id==='central_estagios_pr'));
    assert.ok(jobs.external_links.some(link=>link.source_id==='destro'));
    assert.ok(jobs.external_links.some(link=>link.source_id==='ciee_pr'));
    assert.deepEqual(await page.locator('#jobs-external a').evaluateAll(links=>links.map(a=>a.href)),jobs.external_links.map(link=>link.url));
    await page.screenshot({path:path.join(out,'vagas-real.png'),fullPage:true});
    for(const width of [390,320]) {
      await page.setViewportSize({width,height:844});
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      await page.screenshot({path:path.join(out,`vagas-real-${width}.png`),fullPage:true});
    }
    assert.deepEqual(errors,[]);
    const report={admin:{total:admin.total,ids:admin.courses.map(x=>x.id)},health:{total:health.total,ids:health.courses.map(x=>x.id)},all:{total:all.total},jobs:{total:jobs.total,result_status:jobs.result_status,data_status:jobs.data_status,stale_count:jobs.stale_count},external_links:{courses:admin.external_links,jobs:jobs.external_links},page_errors:errors};
    fs.writeFileSync(path.join(out,'catalogo-real-resultados.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report,null,2));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
