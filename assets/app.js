(function () {
  "use strict";

  /* ---------- mobile menu ---------- */
  var menu = document.querySelector('.menu-btn');
  var nav = document.getElementById('nav');
  if (menu && nav) {
    menu.addEventListener('click', function () {
      var open = menu.getAttribute('aria-expanded') !== 'true';
      menu.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('open', open);
    });
  }

  /* ---------- local time rendering ---------- */
  document.querySelectorAll('[data-utc]').forEach(function (node) {
    var d = new Date(node.dataset.utc);
    if (!isNaN(d.getTime())) {
      node.title = 'UTC: ' + node.dataset.utc;
      node.textContent = d.toLocaleString(undefined, {
        weekday: 'short', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
      });
    }
  });

  /* ---------- snapshot age warning ---------- */
  var snapshot = document.getElementById('snapshot-age');
  if (snapshot && snapshot.dataset.fetched) {
    var hours = (Date.now() - Date.parse(snapshot.dataset.fetched)) / 3600000;
    snapshot.textContent = Number.isFinite(hours)
      ? 'Inventory collected ' + Math.max(0, Math.floor(hours)) + ' hours ago.'
      : 'Inventory collection time unverified.';
    if (!Number.isFinite(hours) || hours > 8) {
      snapshot.classList.add('stale-warning');
      snapshot.textContent += ' Refresh overdue — these are not live odds. Check the source links before using a pick.';
    }
  }

  /* ---------- pick filters ---------- */
  var list = document.getElementById('list');
  if (!list) return;

  var q = document.getElementById('q');
  var comp = document.getElementById('comp');
  var countEl = document.getElementById('count');
  var emptyEl = document.getElementById('empty');
  var clearBtn = document.getElementById('clear');
  var resetBtn = document.getElementById('reset');
  var chips = Array.prototype.slice.call(document.querySelectorAll('[data-filter]'));
  var cards = Array.prototype.slice.call(list.querySelectorAll('.card'));
  var groups = Array.prototype.slice.call(list.querySelectorAll('.daygroup'));
  var params = new URLSearchParams(location.search);
  var method = params.get('method') || '';
  var win = params.get('window') || '';

  function utcDay(ms) { return new Date(ms).toISOString().slice(0, 10); }
  var todayStr = utcDay(Date.now());
  var plus7Str = utcDay(Date.now() + 7 * 86400000);
  var nowStr = new Date().toISOString().slice(0, 19);

  if (params.get('q') && q) q.value = params.get('q');
  if (params.get('comp') && comp) comp.value = params.get('comp');

  function setMethod(value) {
    method = value || '';
    chips.forEach(function (b) {
      var on = b.dataset.filter === method;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', String(on));
    });
  }

  function matches(card) {
    if (method && card.dataset.method !== method) return false;
    if (comp && comp.value && card.dataset.comp !== comp.value) return false;
    if (q && q.value) {
      var needle = q.value.trim().toLowerCase();
      if (needle && (card.dataset.text || '').indexOf(needle) === -1) return false;
    }
    if (win) {
      var start = card.dataset.start || '';
      var day = start.slice(0, 10);
      if (!start) return false;
      if (start <= nowStr) return false;
      if (win === 'today' && day !== todayStr) return false;
      if (win === 'next7' && !(day >= todayStr && day <= plus7Str)) return false;
    }
    return true;
  }

  function apply() {
    var shown = 0;
    cards.forEach(function (card) {
      var visible = matches(card);
      card.hidden = !visible;
      if (visible) shown++;
    });
    groups.forEach(function (group) {
      var visibleInside = group.querySelectorAll('.card:not([hidden])').length;
      var hasNote = !!group.querySelector('.empty-day');
      group.hidden = visibleInside === 0 && !(hasNote && shown === 0 && !method && !win && !(comp && comp.value) && !(q && q.value));
    });
    if (countEl) countEl.textContent = shown + ' of ' + cards.length + ' matches shown';
    if (emptyEl) emptyEl.hidden = shown !== 0;

    var next = new URLSearchParams();
    if (q && q.value.trim()) next.set('q', q.value.trim());
    if (comp && comp.value) next.set('comp', comp.value);
    if (method) next.set('method', method);
    if (win) next.set('window', win);
    var qs = next.toString();
    history.replaceState(null, '', qs ? '?' + qs : location.pathname);
  }

  function bind(el, evt) {
    if (el) el.addEventListener(evt, apply);
  }
  bind(q, 'input');
  bind(comp, 'change');

  chips.forEach(function (button) {
    button.addEventListener('click', function () {
      setMethod(button.dataset.filter);
      apply();
    });
  });

  function resetAll() {
    if (q) q.value = '';
    if (comp) comp.value = '';
    win = '';
    setMethod('');
    apply();
  }
  if (resetBtn) resetBtn.addEventListener('click', resetAll);
  if (clearBtn) clearBtn.addEventListener('click', resetAll);

  if (method) setMethod(method);
  apply();
})();
