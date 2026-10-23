(function () {
  "use strict";
  var menu = document.querySelector('.menu-btn');
  var nav = document.getElementById('nav');
  if (menu && nav) menu.addEventListener('click', function () {
    var open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('open', open);
  });
  document.querySelectorAll('[data-utc]').forEach(function (node) {
    var d = new Date(node.dataset.utc);
    if (!isNaN(d.getTime())) {
      node.title = 'UTC: ' + node.dataset.utc;
      node.textContent = d.toLocaleString(undefined, {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit', timeZoneName:'short'});
    }
  });
  var snapshot = document.getElementById('snapshot-age');
  if (snapshot) {
    var hours = (Date.now() - Date.parse(snapshot.dataset.fetched)) / 3600000;
    snapshot.textContent = Number.isFinite(hours) ? 'Inventory collected ' + Math.max(0, Math.floor(hours)) + ' hours ago.' : 'Inventory collection time unverified.';
    if (!Number.isFinite(hours) || hours > 8) {
      snapshot.classList.add('stale-warning');
      snapshot.textContent += ' Refresh overdue — these are not live odds. Check source links before using picks.';
    }
  }
  var list = document.getElementById('list');
  if (!list) return;
  var q = document.getElementById('q'), comp = document.getElementById('comp');
  var method = '', cards = Array.from(list.querySelectorAll('.card'));
  var params = new URLSearchParams(location.search);
  q.value = params.get('q') || '';
  if (params.has('comp')) comp.value = params.get('comp');
  function apply() {
    var shown = 0;
    cards.forEach(function (card) {
      var visible = (!method || card.dataset.method === method) && (!comp.value || card.dataset.comp === comp.value) && card.dataset.text.includes(q.value.trim().toLowerCase());
      card.hidden = !visible;
      if (visible) shown++;
    });
    document.getElementById('count').textContent = shown + ' of ' + cards.length + ' matches shown';
    document.getElementById('empty').hidden = shown !== 0;
  }
  q.addEventListener('input', apply);
  comp.addEventListener('change', apply);
  document.querySelectorAll('[data-filter]').forEach(function (button) {
    button.setAttribute('aria-pressed', String(button.dataset.filter === method));
    button.addEventListener('click', function () {
      method = button.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(function (b) {
        b.classList.toggle('active', b === button);
        b.setAttribute('aria-pressed', String(b === button));
      });
      apply();
    });
  });
  apply();
})();
