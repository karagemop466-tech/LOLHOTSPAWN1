// Run with jsdom installed externally: NODE_PATH=/path/to/node_modules node tests/dashboard.cjs
//
// The page scripts only wire themselves up on DOMContentLoaded when the document is still
// parsing, exactly like a real browser. jsdom parses synchronously but fires that event on a
// later tick, so this test must wait for it before clicking anything - otherwise it races the
// app and fails even though the page works (that is the bug this version fixes).
const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const assert = require('node:assert/strict');

function ready(document, win) {
  return new Promise((resolve) => {
    if (document.readyState !== 'loading') return resolve();
    let done = false;
    const finish = () => { if (!done) { done = true; resolve(); } };
    document.addEventListener('DOMContentLoaded', finish);
    win.setTimeout(finish, 1000);
  });
}

(async () => {
  const dom = new JSDOM(fs.readFileSync('picks.html', 'utf8'), {
    url: 'https://example.test/LOLHOTSPAWN1/picks.html',
    runScripts: 'outside-only',
  });
  dom.window.eval(fs.readFileSync('assets/app.js', 'utf8'));
  await ready(dom.window.document, dom.window);

  const doc = dom.window.document;
  const window = dom.window;
  // app.js hides filtered cards with the `hidden-row` class (not the hidden property).
  const visible = () => [...doc.querySelectorAll('#list .card')].filter((c) => !c.classList.contains('hidden-row'));
  const all = visible().length;
  assert.ok(all > 0, 'picks list must render cards');

  const menu = doc.querySelector('.menu-btn');
  menu.click();
  assert.equal(menu.getAttribute('aria-expanded'), 'true');
  assert.ok(doc.querySelector('#nav').classList.contains('open'));
  menu.click();
  assert.equal(menu.getAttribute('aria-expanded'), 'false');

  const search = doc.querySelector('#q');
  search.value = 'this-team-does-not-exist';
  search.dispatchEvent(new window.Event('input'));
  assert.equal(visible().length, 0);
  assert.equal(doc.querySelector('#empty').hidden, false);
  search.value = '';
  search.dispatchEvent(new window.Event('input'));
  assert.equal(visible().length, all);

  doc.querySelector('[data-filter="market"]').click();
  assert.ok(visible().length > 0);
  assert.ok(visible().every((c) => c.dataset.method === 'market'));
  doc.querySelector('[data-filter=""]').click();

  const comp = doc.querySelector('#comp');
  comp.value = comp.options[1].value;
  comp.dispatchEvent(new window.Event('change'));
  assert.ok(visible().length > 0);
  assert.ok(visible().every((c) => c.dataset.comp === comp.value));

  console.log('PASS dashboard menu, search, empty state, method and tournament filters (' + all + ' cards)');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
