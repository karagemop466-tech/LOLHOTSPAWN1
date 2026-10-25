(function () {
  var STALE_WARN_HOURS = 12;
  var STALE_HARD_HOURS = 30;

  function bindOnce(el, type, fn) {
    if (!el) return;
    var key = "bound" + type;
    if (el.dataset && el.dataset[key]) return;
    if (el.dataset) el.dataset[key] = "1";
    el.addEventListener(type, fn);
  }

  function isPastNow(el) {
    if (!el) return false;
    if (el.dataset.stale === "1") return true;
    var raw = el.dataset.start;
    if (!raw) return false;
    var t = Date.parse(raw);
    return !isNaN(t) && t <= Date.now();
  }

  function hydrateLivePastBadges() {
    document.querySelectorAll(".card[data-start]").forEach(function (card) {
      if (!isPastNow(card)) return;
      card.dataset.stale = "1";
      var badges = card.querySelector(".badges");
      if (badges && !badges.querySelector(".b-past")) {
        var b = document.createElement("span");
        b.className = "badge b-past";
        b.textContent = "start time passed";
        badges.insertBefore(b, badges.firstChild);
      }
    });
    document.querySelectorAll(".prow[data-start]").forEach(function (row) {
      if (isPastNow(row)) row.dataset.stale = "1";
    });
  }

  function renderSnapshotAge() {
    var el = document.getElementById("snapshot-age");
    if (!el) return;
    var raw = el.getAttribute("data-fetched");
    var parsed = raw ? Date.parse(raw) : NaN;
    if (!raw || isNaN(parsed)) {
      el.classList.add("stale-hard");
      el.textContent = "Hotspawn inventory timestamp missing or unreadable. Treat every pick on this page as unverified for current schedule.";
      return;
    }
    var hours = (Date.now() - parsed) / 3600000;
    var age = hours < 1 ? Math.max(0, Math.round(hours * 60)) + "m" : Math.round(hours) + "h";
    if (hours >= STALE_HARD_HOURS) {
      el.classList.add("stale-hard");
      el.textContent = "STALE SNAPSHOT: Hotspawn inventory is " + age + " old (collected " + raw + "). Scheduled 6h refresh appears not to have updated this page; re-verify fixtures and odds at the linked sources before relying on any pick.";
    } else if (hours >= STALE_WARN_HOURS) {
      el.classList.add("stale-warn");
      el.textContent = "Snapshot is " + age + " old (collected " + raw + ") — older than one 6h refresh cycle. Check linked sources for line movement and delistings.";
    } else {
      el.textContent = "Hotspawn inventory is " + age + " old (collected " + raw + ").";
    }
  }

  function initMenu() {
    var btn = document.querySelector(".menu-btn");
    var nav = document.getElementById("nav");
    if (!btn || !nav) return;
    bindOnce(btn, "click", function () {
      var open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function initCards() {
    var list = document.getElementById("list");
    if (!list) return;
    var cards = Array.prototype.slice.call(list.querySelectorAll(".card"));
    var q = document.getElementById("q");
    var comp = document.getElementById("comp");
    var count = document.getElementById("count");
    var empty = document.getElementById("empty");
    var upBtn = document.getElementById("upcoming");
    var chips = Array.prototype.slice.call(document.querySelectorAll(".chip[data-filter]"));
    if (!list._state) list._state = { method: "", upcomingOnly: false };

    function apply() {
      var term = q ? q.value.trim().toLowerCase() : "";
      var cv = comp ? comp.value : "";
      var shown = 0;
      cards.forEach(function (c) {
        var ok = (!list._state.method || c.dataset.method === list._state.method) &&
          (!cv || c.dataset.comp === cv) &&
          (!list._state.upcomingOnly || !isPastNow(c)) &&
          (!term || c.dataset.text.indexOf(term) !== -1);
        c.hidden = !ok;
        c.classList.toggle("hidden-row", !ok);
        if (ok) shown++;
      });
      if (count) count.textContent = shown + (shown === 1 ? " match shown" : " matches shown");
      if (empty) empty.hidden = shown !== 0;
    }

    chips.forEach(function (ch) {
      bindOnce(ch, "click", function () {
        chips.forEach(function (x) { x.classList.remove("active"); });
        ch.classList.add("active");
        list._state.method = ch.dataset.filter || "";
        apply();
      });
    });
    if (upBtn) {
      var upSpan = upBtn.querySelector("span");
      if (upSpan) {
        upSpan.textContent = String(cards.filter(function (c) { return !isPastNow(c); }).length);
      }
      bindOnce(upBtn, "click", function () {
        list._state.upcomingOnly = !list._state.upcomingOnly;
        upBtn.classList.toggle("active", list._state.upcomingOnly);
        upBtn.setAttribute("aria-pressed", list._state.upcomingOnly ? "true" : "false");
        apply();
      });
    }
    bindOnce(q, "input", apply);
    bindOnce(comp, "change", apply);
    apply();
  }

  function initTable() {
    var tbody = document.getElementById("tbody");
    if (!tbody) return;
    var rows = Array.prototype.slice.call(tbody.querySelectorAll(".prow"));
    var q = document.getElementById("tq");
    var comp = document.getElementById("tcomp");
    var count = document.getElementById("tcount");
    var empty = document.getElementById("tempty");
    var upBtn = document.getElementById("tupcoming");
    var chips = Array.prototype.slice.call(document.querySelectorAll("[data-tfilter]"));
    if (!tbody._state) tbody._state = { method: "", upcomingOnly: false };

    function apply() {
      var term = q ? q.value.trim().toLowerCase() : "";
      var cv = comp ? comp.value : "";
      var shown = 0;
      rows.forEach(function (r) {
        var ok = (!tbody._state.method || r.dataset.method === tbody._state.method) &&
          (!cv || r.dataset.comp === cv) &&
          (!tbody._state.upcomingOnly || !isPastNow(r)) &&
          (!term || r.dataset.text.indexOf(term) !== -1);
        r.hidden = !ok;
        r.classList.toggle("hidden-row", !ok);
        if (ok) shown++;
      });
      if (count) count.textContent = shown + (shown === 1 ? " match shown" : " matches shown");
      if (empty) empty.hidden = shown !== 0;
    }

    chips.forEach(function (ch) {
      bindOnce(ch, "click", function () {
        chips.forEach(function (x) { x.classList.remove("active"); });
        ch.classList.add("active");
        tbody._state.method = ch.dataset.tfilter || "";
        apply();
      });
    });
    if (upBtn) {
      var upSpan = upBtn.querySelector("span");
      if (upSpan) {
        upSpan.textContent = String(rows.filter(function (r) { return !isPastNow(r); }).length);
      }
      bindOnce(upBtn, "click", function () {
        tbody._state.upcomingOnly = !tbody._state.upcomingOnly;
        upBtn.classList.toggle("active", tbody._state.upcomingOnly);
        upBtn.setAttribute("aria-pressed", tbody._state.upcomingOnly ? "true" : "false");
        apply();
      });
    }
    bindOnce(q, "input", apply);
    bindOnce(comp, "change", apply);
    apply();
  }

  function initTop() {
    var top = document.getElementById("totop");
    bindOnce(top, "click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
  }

  // Deep links: table.html?comp=<tournament>&method=<m>&q=<term>&upcoming=1
  // The landing page's tournament directory and every competition link point here, so a
  // phone user lands on the filtered list instead of scrolling 200+ rows.
  function initDeepLinks() {
    var params;
    try { params = new URLSearchParams(window.location.search); } catch (e) { return; }
    var sel = document.getElementById("comp") || document.getElementById("tcomp");
    var search = document.getElementById("q") || document.getElementById("tq");
    var method = params.get("method");
    var comp = params.get("comp");
    var term = params.get("q");
    var upcoming = params.get("upcoming");

    function fire(el, type) {
      try { el.dispatchEvent(new Event(type, { bubbles: true })); }
      catch (e) { el.dispatchEvent(document.createEvent("HTMLEvents").initEvent(type, true, true)); }
    }

    if (search && term) { search.value = term; fire(search, "input"); }
    if (sel && comp) {
      var found = false;
      Array.prototype.forEach.call(sel.options, function (o) {
        if (o.value === comp) found = true;
      });
      if (found) { sel.value = comp; fire(sel, "change"); }
    }
    if (method) {
      var chip = document.querySelector('.chip[data-filter="' + method.replace(/"/g, "") + '"]') ||
                 document.querySelector('[data-tfilter="' + method.replace(/"/g, "") + '"]');
      if (chip) chip.click();
    }
    if (upcoming === "1") {
      var upBtn = document.getElementById("upcoming") || document.getElementById("tupcoming");
      if (upBtn) upBtn.click();
    }
    var count = document.getElementById("tcount") || document.getElementById("count");
    if (comp && count && count.parentNode && !document.getElementById("filtered-notice")) {
      var note = document.createElement("p");
      note.id = "filtered-notice";
      note.className = "muted small";
      note.innerHTML = 'Filtered to <strong>' + comp.replace(/[<>&]/g, "") + "</strong> &middot; " +
        '<a href="table.html">show every tournament</a> &middot; ' +
        '<a href="index.html#directory">back to the tournament list</a>';
      count.parentNode.insertBefore(note, count.nextSibling);
    }
  }

  // Starting-soon strip (landing page): the server renders the next 16 kick-offs;
  // hide any whose start time has passed since the build (per list), so a
  // locked pick is never presented as upcoming on a phone (session 2faec1ff).
  function initNextStrip() {
    document.querySelectorAll(".nextlist").forEach(function (list) {
      var shown = 0;
      Array.prototype.slice.call(list.querySelectorAll(".nextrow[data-start]"))
        .forEach(function (r) {
          var hide = isPastNow(r) || shown >= 16;
          r.hidden = hide;
          if (!hide) shown++;
        });
    });
  }

  function init() {
    hydrateLivePastBadges();
    initNextStrip();
    renderSnapshotAge();
    initMenu();
    initCards();
    initTable();
    initDeepLinks();
    initTop();
  }

  document.addEventListener("DOMContentLoaded", init);
  init();
})();
