// Run with jsdom installed externally: NODE_PATH=/path/to/node_modules node tests/dashboard.cjs
//
// The page scripts only wire themselves up on DOMContentLoaded when the document is still
// parsing, exactly like a real browser. jsdom parses synchronously but fires that event on a
// later tick, so this test must wait for it before clicking anything - otherwise it races the
// app and fails even though the page works (that is the bug this version fixes).
const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const assert = require('node:assert/strict');

const dom = new JSDOM(fs.readFileSync('picks.html','utf8'), {url:'https://example.test/LOLHOTSPAWN1/picks.html', runScripts:'outside-only'});
dom.window.eval(fs.readFileSync('assets/app.js','utf8'));
// Dispatch DOMContentLoaded after initial init() to prove listener registration is idempotent
dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
const doc = dom.window.document;
const visible = () => [...doc.querySelectorAll('#list .card')].filter(c => !c.hidden);
const all = visible().length;
assert.ok(all > 0);
const menu = doc.querySelector('.menu-btn');
menu.click(); assert.equal(menu.getAttribute('aria-expanded'), 'true'); assert.ok(doc.querySelector('#nav').classList.contains('open'));
menu.click(); assert.equal(menu.getAttribute('aria-expanded'), 'false');
const search = doc.querySelector('#q');
search.value = 'this-team-does-not-exist'; search.dispatchEvent(new dom.window.Event('input'));
assert.equal(visible().length, 0); assert.equal(doc.querySelector('#empty').hidden, false);
search.value = ''; search.dispatchEvent(new dom.window.Event('input')); assert.equal(visible().length, all);
doc.querySelector('[data-filter="market"]').click();
assert.ok(visible().length > 0); assert.ok(visible().every(c => c.dataset.method === 'market'));
doc.querySelector('[data-filter=""]').click();
const upBtn = doc.querySelector('#upcoming');
upBtn.click();
assert.ok(visible().length > 0 && visible().length < all);
assert.ok(visible().every(c => c.dataset.stale !== '1'));
upBtn.click();
assert.equal(visible().length, all);
const comp = doc.querySelector('#comp'); comp.value = comp.options[1].value; comp.dispatchEvent(new dom.window.Event('change'));
assert.ok(visible().length > 0); assert.ok(visible().every(c => c.dataset.comp === comp.value));

// Also verify table.html toolbar (#tq, #tcomp, #tupcoming, [data-tfilter])
const tdom = new JSDOM(fs.readFileSync('table.html','utf8'), {url:'https://example.test/LOLHOTSPAWN1/table.html', runScripts:'outside-only'});
tdom.window.eval(fs.readFileSync('assets/app.js','utf8'));
const tdoc = tdom.window.document;
const tvis = () => [...tdoc.querySelectorAll('#tbody .prow')].filter(r => !r.hidden);
assert.equal(tvis().length, all);
tdoc.querySelector('#tupcoming').click();
assert.ok(tvis().length > 0 && tvis().length < all);
tdoc.querySelector('#tupcoming').click();
assert.equal(tvis().length, all);

// The landing-page strip uses the browser clock so a snapshot cannot keep calling past
// kick-offs "Starting soon". Keep the check deterministic with one past and one future row.
const nextMarkup = `<!doctype html><main>
  <div id="nextlist">
    <a class="nextrow" data-start="2026-10-25T10:00:00Z" href="picks.html#match-1">Past</a>
    <a class="nextrow" data-start="2026-10-25T12:00:00Z" href="picks.html#match-2">Future</a>
  </div>
  <p id="next-empty" hidden>No future kick-off remains in this snapshot. <a href="table.html">All picks</a></p>
</main>`;
const futureDom = new JSDOM(nextMarkup, {url:'https://example.test/LOLHOTSPAWN1/', runScripts:'outside-only'});
futureDom.window.Date.now = () => Date.parse('2026-10-25T11:00:00Z');
futureDom.window.eval(fs.readFileSync('assets/app.js','utf8'));
const futureDoc = futureDom.window.document;
assert.equal(futureDoc.querySelectorAll('#nextlist .nextrow:not([hidden])').length, 1);
assert.equal(futureDoc.querySelector('#nextlist .nextrow:not([hidden])').textContent, 'Future');
assert.equal(futureDoc.querySelector('#next-empty').hidden, true);
futureDom.window.close();
const expiredDom = new JSDOM(nextMarkup, {url:'https://example.test/LOLHOTSPAWN1/', runScripts:'outside-only'});
expiredDom.window.Date.now = () => Date.parse('2026-10-25T13:00:00Z');
expiredDom.window.eval(fs.readFileSync('assets/app.js','utf8'));
assert.equal(expiredDom.window.document.querySelectorAll('#nextlist .nextrow:not([hidden])').length, 0);
assert.equal(expiredDom.window.document.querySelector('#next-empty').hidden, false);
assert.ok(expiredDom.window.document.querySelector('#next-empty a[href="table.html"]'));
expiredDom.window.close();

console.log('PASS dashboard menu, search, empty state, upcoming toggle, method & tournament filters + live-clock next-up state (' + all + ' matches)');
