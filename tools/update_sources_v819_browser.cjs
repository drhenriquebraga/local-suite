const fs = require('fs');
const assert = require('assert');
const {chromium} = require(process.argv[3]);
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.argv[4]});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    let fail = false;
    const calls = [];
    await page.route('http://suite.test/**', async route => {
      if (new URL(route.request().url()).pathname === '/config')
        return route.fulfill({contentType: 'text/html', body: fs.readFileSync(process.argv[2] + '/config.html', 'utf8')});
      assert.equal(route.request().headers().origin, 'http://suite.test');
      const action = route.request().postDataJSON().acao;
      calls.push(action);
      return route.fulfill({json: {
        etapa: 'livre', nova: !fail, publicada: fail ? '' : '8.19',
        consulta_estado: fail ? 'erro' : 'nova', consulta_fonte: 'espelho',
        consulta_origens: {github: {estado: 'erro'}, espelho: {estado: fail ? 'erro' : 'nova'}},
        consulta_erro: fail ? 'GitHub: HTTP 403; espelho: TLS_ERROR <img src=x onerror=alert(1)>' : '',
        consultando: action === 'consultar'
      }});
    });
    await page.goto('http://suite.test/config');
    await page.click('#btConsultarVersao');
    await page.waitForFunction(() => !document.getElementById('btConsultarVersao').disabled);
    assert((await page.textContent('#subAtu')).includes('8.19'));
    assert((await page.textContent('#consultaVersaoOrigens')).includes('GitHub: Indisponível'));
    assert((await page.textContent('#consultaVersaoOrigens')).includes('Espelho: Disponível'));
    assert(await page.locator('#btAtuAgora').isVisible());
    assert.deepEqual(calls, ['consultar', 'estado']);
    fail = true;
    await page.click('#btConsultarVersao');
    await page.waitForFunction(() => !document.getElementById('btConsultarVersao').disabled);
    assert((await page.textContent('#subAtu')).includes('Não foi possível'));
    assert((await page.textContent('#consultaVersaoErro')).includes('TLS_ERROR'));
    assert.equal(await page.locator('#consultaVersaoErro img').count(), 0);
    assert(!(await page.locator('#btAtuAgora').isVisible()));
    assert.deepEqual(errors, []);
    console.log('PASS source-aware settings refresh, force polling, failure diagnostics and text-only errors');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
