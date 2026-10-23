(function () {
  "use strict";

  // Format `data-utc` timestamps with friendly local date/time while preserving UTC
  function hydrateTimestamps() {
    var nodes = document.querySelectorAll("[data-utc]");
    for (var i = 0; i < nodes.length; i++) {
      var iso = nodes[i].getAttribute("data-utc");
      if (!iso) continue;
      var d = new Date(iso);
      if (isNaN(d.getTime())) continue;
      try {
        var localStr = d.toLocaleString(undefined, {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
        nodes[i].setAttribute("title", "UTC: " + iso + " | Local: " + localStr);
        if (nodes[i].hasAttribute("data-show-local")) {
          nodes[i].textContent = localStr + " (" + iso.slice(11, 16) + " UTC)";
        }
      } catch (_err) {
        // Keep static UTC fallback intact
      }
    }
  }

  // Mobile menu toggle (header)
  function initMenu() {
    var menu = document.querySelector(".menu-btn");
    var nav = document.getElementById("nav");
    if (!menu || !nav) return;
    menu.addEventListener("click", function () {
      var open = menu.getAttribute("aria-expanded") !== "true";
      menu.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("open", open);
    });
  }

  // Snapshot age: a stale snapshot must never look like live odds
  function initSnapshotAge() {
    var snapshot = document.getElementById("snapshot-age");
    if (!snapshot) return;
    var hours = (Date.now() - Date.parse(snapshot.getAttribute("data-fetched"))) / 3600000;
    if (!isFinite(hours)) {
      snapshot.textContent = "Inventory collection time unverified.";
      snapshot.classList.add("stale-warning");
      return;
    }
    var age = Math.max(0, Math.floor(hours));
    snapshot.textContent = "Inventory collected " + age + " hour" + (age === 1 ? "" : "s") + " ago.";
    if (hours > 8) {
      snapshot.classList.add("stale-warning");
      snapshot.textContent += " Refresh overdue - these are not live odds. Check the source links before using a pick.";
    }
  }

  // Card-list filters (picks.html): search + tournament + method chips
  function initPickFilters() {
    var searchEl = document.getElementById("q");
    var compEl = document.getElementById("comp");
    var list = document.getElementById("list");
    var countEl = document.getElementById("count");
    var emptyEl = document.getElementById("empty");
    if (!searchEl && !compEl) return;

    var cards = list ? list.querySelectorAll(".card") : [];
    var method = "";

    function apply() {
      var term = searchEl ? searchEl.value.trim().toLowerCase() : "";
      var comp = compEl ? compEl.value : "";
      var shown = 0;
      for (var i = 0; i < cards.length; i++) {
        var r = cards[i];
        var ok = true;
        if (method && r.getAttribute("data-method") !== method) ok = false;
        if (ok && comp && r.getAttribute("data-comp") !== comp) ok = false;
        if (ok && term && (r.getAttribute("data-text") || "").indexOf(term) === -1) ok = false;
        r.hidden = !ok;
      r.classList.toggle("hidden-row", !ok);
        if (ok) shown++;
      }
      if (countEl) countEl.textContent = shown + " match" + (shown === 1 ? "" : "es") + " shown";
      if (emptyEl) emptyEl.hidden = shown !== 0;
    }

    var chips = document.querySelectorAll("[data-filter]");
    for (var c = 0; c < chips.length; c++) {
      chips[c].addEventListener("click", function (ev) {
        for (var j = 0; j < chips.length; j++) chips[j].classList.remove("active");
        ev.currentTarget.classList.add("active");
        method = ev.currentTarget.getAttribute("data-filter") || "";
        apply();
      });
    }

    if (searchEl) searchEl.addEventListener("input", apply);
    if (compEl) compEl.addEventListener("change", apply);
    apply();
  }

  // Pick-table filters (table.html): search + tournament + method chips
  function initTableFilter() {
    var q = document.getElementById("tq");
    var comp = document.getElementById("tcomp");
    var body = document.getElementById("tbody");
    var count = document.getElementById("tcount");
    var empty = document.getElementById("tempty");
    var chips = document.querySelectorAll("[data-tfilter]");
    if (!body || !chips.length) return;

    var activeMethod = "";
    var rows = body.querySelectorAll("tr.prow");

    function apply() {
      var term = q ? q.value.trim().toLowerCase() : "";
      var compVal = comp ? comp.value : "";
      var shown = 0;
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        var ok = true;
        if (activeMethod && r.getAttribute("data-method") !== activeMethod) ok = false;
        if (ok && compVal && r.getAttribute("data-comp") !== compVal) ok = false;
        if (ok && term && (r.getAttribute("data-text") || "").indexOf(term) === -1) ok = false;
        r.hidden = !ok;
      r.classList.toggle("hidden-row", !ok);
        if (ok) shown++;
      }
      if (count) count.textContent = shown + " match" + (shown === 1 ? "" : "es") + " shown";
      if (empty) empty.hidden = shown !== 0;
    }

    for (var c = 0; c < chips.length; c++) {
      chips[c].addEventListener("click", function (ev) {
        for (var j = 0; j < chips.length; j++) chips[j].classList.remove("active");
        ev.currentTarget.classList.add("active");
        activeMethod = ev.currentTarget.getAttribute("data-tfilter") || "";
        apply();
      });
    }
    if (q) q.addEventListener("input", apply);
    if (comp) comp.addEventListener("change", apply);
    apply();
  }

  /* The script is loaded at the end of <body>, so the elements it needs already exist.
     Boot immediately (keeps the page usable even if DOMContentLoaded has already fired),
     and once more on DOMContentLoaded as a guard, which is idempotent. */
  var booted = false;
  function boot() {
    if (booted) return;
    booted = true;
    hydrateTimestamps();
    initMenu();
    initSnapshotAge();
    initPickFilters();
    initTableFilter();
  }
  boot();
  document.addEventListener("DOMContentLoaded", boot);
})();
