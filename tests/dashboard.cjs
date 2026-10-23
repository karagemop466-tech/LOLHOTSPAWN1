// Interaction tests for the published dashboard.
// Run with jsdom available: NODE_PATH=/path/to/node_modules node tests/dashboard.cjs
// The pages are the generated ones in the repository root, so run this after
// tools/site.py has rebuilt them.
const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const assert = require('node:assert/strict');

const HTML = fs.readFileSync('picks.html', 'utf8');
const APP = fs.readFileSync('assets/app.js', 'utf8');

function boot(query) {
  const dom = new JSDOM(HTML, {
    url: 'https://example.test/LOLHOTSPAWN1/picks.html' + (query || ''),
    runScripts: 'outside-only'
  });
  dom.window.eval(APP);
  return dom;
}

const dom = boot();
const doc = dom.window.document;
const visible = () => [...doc.querySelectorAll('#list .card')].filter(c => !c.hidden);
const all = visible().length;
assert.ok(all > 0, 'no cards rendered');

// --- mobile menu ---------------------------------------------------------
const menu = doc.querySelector('.menu-btn');
assert.equal(menu.getAttribute('aria-expanded'), 'false');
menu.click();
assert.equal(menu.getAttribute('aria-expanded'), 'true');
assert.ok(doc.querySelector('#nav').classList.contains('open'));
menu.click();
assert.equal(menu.getAttribute('aria-expanded'), 'false');

// --- mobile tab bar: five entries, one active ----------------------------
const tabbar = doc.querySelector('.tabbar');
assert.ok(tabbar, 'mobile tab bar missing');
assert.equal(tabbar.querySelectorAll('a').length, 5);
assert.ok(tabbar.querySelector('a.active'), 'no active tab');
assert.equal(tabbar.querySelector('a.active').getAttribute('href'), 'picks.html');

// --- search --------------------------------------------------------------
const search = doc.querySelector('#q');
const count = doc.querySelector('#count');
search.value = 'this-team-does-not-exist';
search.dispatchEvent(new dom.window.Event('input'));
assert.equal(visible().length, 0);
assert.equal(doc.querySelector('#empty').hidden, false);
assert.match(count.textContent, /0 matches/);
search.value = '';
search.dispatchEvent(new dom.window.Event('input'));
assert.equal(visible().length, all);

// searching a real team name keeps that team's card
const sample = doc.querySelector('#list .card');
const team = sample.getAttribute('data-comp').split(' ')[0];
search.value = team;
search.dispatchEvent(new dom.window.Event('input'));
assert.ok(visible().length > 0);
assert.ok(visible().length <= all);
search.value = '';
search.dispatchEvent(new dom.window.Event('input'));

// --- pick-type chips -----------------------------------------------------
doc.querySelector('[data-filter="market"]').click();
assert.ok(visible().length > 0);
assert.ok(visible().every(c => c.dataset.method === 'market'));
doc.querySelector('[data-filter="unresolved"]').click();
assert.ok(visible().every(c => c.dataset.method === 'unresolved'));
// a settlement pick names a participant and claims no probability
assert.ok(visible().every(c => c.getAttribute('data-prob') === ''));
assert.ok(visible().every(c => c.getAttribute('data-pick') !== ''));
doc.querySelector('[data-filter=""]').click();
assert.equal(visible().length, all);

// --- kick-off window chips ----------------------------------------------
const todayStr = new Date().toISOString().slice(0, 10);
doc.querySelector('[data-window="today"]').click();
assert.ok(visible().every(c => (c.dataset.start || '').slice(0, 10) === todayStr));
assert.ok(doc.querySelector('[data-window="today"]').classList.contains('active'));
doc.querySelector('[data-window="next7"]').click();
assert.ok(visible().every(c => (c.dataset.start || '').slice(0, 10) >= todayStr));
doc.querySelector('[data-window=""]').click();
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
assert.ok(!doc.querySelector('[data-window="today"]').classList.contains('active'));

// --- day groups stay in sync with their cards ----------------------------
const groups = [...doc.querySelectorAll('#list .daygroup')];
assert.ok(groups.length > 1, 'expected day groups');
doc.querySelector('[data-filter="unresolved"]').click();
groups.forEach(g => {
  const shown = g.querySelectorAll('.card:not([hidden])').length;
  assert.equal(g.hidden, shown === 0, 'day group visibility out of sync');
});
doc.querySelector('[data-filter=""]').click();

// --- deep links ----------------------------------------------------------
const market = boot('?method=market');
const marketCards = [...market.window.document.querySelectorAll('#list .card')].filter(c => !c.hidden);
assert.ok(marketCards.length > 0);
assert.ok(marketCards.every(c => c.dataset.method === 'market'));
assert.ok(marketCards.length < all);

const today = boot('?window=today');
const todayCards = [...today.window.document.querySelectorAll('#list .card')].filter(c => !c.hidden);
assert.ok(todayCards.every(c => (c.dataset.start || '').slice(0, 10) === todayStr));

const searchDeep = boot('?q=' + encodeURIComponent('worlds'));
assert.ok([...searchDeep.window.document.querySelectorAll('#list .card')].filter(c => !c.hidden).length > 0);

// --- every page carries the tab bar and the menu -------------------------
for (const page of ['index.html', 'featured.html', 'originated.html', 'unresolved.html',
                    'competitions.html', 'teams.html', 'methodology.html', 'sources.html',
                    'verification.html', 'flagged.html']) {
  const html = fs.readFileSync(page, 'utf8');
  assert.ok(html.includes('class="mobnav tabbar"'), page + ' is missing the mobile tab bar');
  assert.ok(html.includes('class="menu-btn"'), page + ' is missing the menu button');
  assert.ok(html.includes('assets/app.js'), page + ' does not load the dashboard script');
}

console.log('PASS dashboard: menu, 5-tab bar, search, empty state, type/window/tournament ' +
            'filters, reset, day groups, deep links (' + all + ' cards)');
