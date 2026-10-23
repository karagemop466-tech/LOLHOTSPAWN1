// Run with jsdom installed externally: NODE_PATH=/path/to/node_modules node tests/dashboard.cjs
const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const assert = require('node:assert/strict');

function boot(query) {
  const dom = new JSDOM(fs.readFileSync('picks.html', 'utf8'), {
    url: 'https://example.test/LOLHOTSPAWN1/picks.html' + (query || ''),
    runScripts: 'outside-only'
  });
  dom.window.eval(fs.readFileSync('assets/app.js', 'utf8'));
  return dom;
}

const dom = boot();
const doc = dom.window.document;
const visible = () => [...doc.querySelectorAll('#list .card')].filter(c => !c.hidden);
const all = visible().length;
assert.ok(all > 0);

// --- mobile menu ---------------------------------------------------------
const menu = doc.querySelector('.menu-btn');
menu.click();
assert.equal(menu.getAttribute('aria-expanded'), 'true');
assert.ok(doc.querySelector('#nav').classList.contains('open'));
menu.click();
assert.equal(menu.getAttribute('aria-expanded'), 'false');

// --- mobile tab bar ------------------------------------------------------
const tabbar = doc.querySelector('.tabbar');
assert.ok(tabbar, 'mobile tab bar missing');
assert.equal(tabbar.querySelectorAll('a').length, 4);
assert.ok(tabbar.querySelector('a.active'), 'no active tab');

// --- search --------------------------------------------------------------
const search = doc.querySelector('#q');
search.value = 'this-team-does-not-exist';
search.dispatchEvent(new dom.window.Event('input'));
assert.equal(visible().length, 0);
assert.equal(doc.querySelector('#empty').hidden, false);
search.value = '';
search.dispatchEvent(new dom.window.Event('input'));
assert.equal(visible().length, all);

// --- method chips --------------------------------------------------------
doc.querySelector('[data-filter="market"]').click();
assert.ok(visible().length > 0);
assert.ok(visible().every(c => c.dataset.method === 'market'));
doc.querySelector('[data-filter=""]').click();
assert.equal(visible().length, all);

// --- tournament select ---------------------------------------------------
const comp = doc.querySelector('#comp');
comp.value = comp.options[1].value;
comp.dispatchEvent(new dom.window.Event('change'));
assert.ok(visible().length > 0);
assert.ok(visible().every(c => c.dataset.comp === comp.value));

// --- reset button --------------------------------------------------------
doc.querySelector('#reset').click();
assert.equal(comp.value, '');
assert.equal(search.value, '');
assert.equal(visible().length, all);

// --- day groups ----------------------------------------------------------
const groups = [...doc.querySelectorAll('.daygroup')];
assert.ok(groups.length > 1, 'expected day groups');
doc.querySelector('[data-filter="unresolved"]').click();
groups.forEach(g => {
  const shown = g.querySelectorAll('.card:not([hidden])').length;
  assert.equal(g.hidden, shown === 0, 'day group visibility out of sync');
});
doc.querySelector('[data-filter=""]').click();

// --- deep link: ?method=market ------------------------------------------
const market = boot('?method=market');
const marketCards = [...market.window.document.querySelectorAll('#list .card')].filter(c => !c.hidden);
assert.ok(marketCards.length > 0);
assert.ok(marketCards.every(c => c.dataset.method === 'market'));
assert.ok(marketCards.length < all);

// --- deep link: ?window=today -------------------------------------------
const today = boot('?window=today');
const todayCards = [...today.window.document.querySelectorAll('#list .card')].filter(c => !c.hidden);
const todayStr = new Date().toISOString().slice(0, 10);
assert.ok(todayCards.every(c => (c.dataset.start || '').slice(0, 10) === todayStr));

console.log('PASS dashboard menu, tab bar, search, empty state, method/tournament/window filters, reset, day groups (' + all + ' cards)');
