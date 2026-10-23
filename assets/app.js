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

  function initPickFilters() {
    var searchEl = document.getElementById("filter-search");
    var compEl = document.getElementById("filter-comp");
    var tierEl = document.getElementById("filter-tier");
    var windowEl = document.getElementById("filter-window");
    var sortEl = document.getElementById("filter-sort");
    var countEl = document.getElementById("visible-count");
    var rootEl = document.getElementById("dual-view-root");

    var cardsWrap = document.getElementById("picks-cards-list");
    var tableBody = document.getElementById("picks-table-body");
    if (!searchEl && !compEl && !tierEl && !windowEl) return;

    // Pre-populate controls from URL query string (`?comp=...&tier=...&window=...&q=...`)
    var params = new URLSearchParams(window.location.search);
    if (compEl && params.get("comp")) compEl.value = params.get("comp");
    if (tierEl && params.get("tier")) tierEl.value = params.get("tier");
    if (windowEl && params.get("window")) windowEl.value = params.get("window");
    if (searchEl && params.get("q")) searchEl.value = params.get("q");

    function matchesFilters(el) {
      var q = searchEl ? searchEl.value.trim().toLowerCase() : "";
      var comp = compEl ? compEl.value : "all";
      var tier = tierEl ? tierEl.value : "all";
      var win = windowEl ? windowEl.value : "all";

      if (comp && comp !== "all" && el.getAttribute("data-comp") !== comp) return false;
      if (tier && tier !== "all") {
        var rowTier = el.getAttribute("data-status") || "";
        if (tier === "market" && rowTier !== "market_consensus" && rowTier !== "esportsbook_line") return false;
        if (tier !== "market" && rowTier !== tier) return false;
      }
      if (win && win !== "all") {
        var hrs = parseFloat(el.getAttribute("data-hours") || "99999");
        if (win === "48h" && (hrs <= 0 || hrs > 48)) return false;
        if (win === "7d" && (hrs <= 0 || hrs > 168)) return false;
        if (win === "high" && parseFloat(el.getAttribute("data-favprob") || "0") < 0.65) return false;
      }
      if (q) {
        var hay = (el.getAttribute("data-search") || "").toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    }

    function sortContainer(container, selector) {
      if (!container || !sortEl) return;
      var mode = sortEl.value || "kickoff";
      var items = Array.prototype.slice.call(container.querySelectorAll(selector));
      items.sort(function (a, b) {
        if (mode === "prob_desc") {
          return parseFloat(b.getAttribute("data-favprob") || "0") - parseFloat(a.getAttribute("data-favprob") || "0");
        }
        if (mode === "points_desc") {
          return parseFloat(b.getAttribute("data-points") || "0") - parseFloat(a.getAttribute("data-points") || "0");
        }
        if (mode === "edge_desc") {
          return Math.abs(parseFloat(b.getAttribute("data-delta") || "0")) - Math.abs(parseFloat(a.getAttribute("data-delta") || "0"));
        }
        return parseFloat(a.getAttribute("data-kickoff") || "0") - parseFloat(b.getAttribute("data-kickoff") || "0");
      });
      for (var i = 0; i < items.length; i++) {
        container.appendChild(items[i]);
      }
    }

    function applyAll() {
      sortContainer(cardsWrap, ".pick-item");
      sortContainer(tableBody, ".pick-row");

      var cardItems = cardsWrap ? cardsWrap.querySelectorAll(".pick-item") : [];
      var shown = 0;
      for (var i = 0; i < cardItems.length; i++) {
        var ok = matchesFilters(cardItems[i]);
        cardItems[i].classList.toggle("hidden-row", !ok);
        if (ok) shown++;
      }

      var tableRows = tableBody ? tableBody.querySelectorAll(".pick-row") : [];
      for (var j = 0; j < tableRows.length; j++) {
        var okRow = matchesFilters(tableRows[j]);
        tableRows[j].classList.toggle("hidden-row", !okRow);
        if (!cardsWrap && okRow) shown++;
      }

      if (countEl) {
        countEl.textContent = String(shown);
      }
    }

    [searchEl, compEl, tierEl, windowEl, sortEl].forEach(function (ctrl) {
      if (!ctrl) return;
      ctrl.addEventListener("input", applyAll);
      ctrl.addEventListener("change", applyAll);
    });

    // View switcher (`Auto Mobile/Desktop`, `Cards`, `Table`)
    var viewBtns = document.querySelectorAll("[data-set-view]");
    for (var k = 0; k < viewBtns.length; k++) {
      viewBtns[k].addEventListener("click", function (ev) {
        var mode = ev.currentTarget.getAttribute("data-set-view");
        if (!rootEl) return;
        rootEl.classList.remove("responsive-dual", "view-mode-cards", "view-mode-table");
        rootEl.classList.add(mode);
        viewBtns.forEach(function (b) {
          b.classList.toggle("active", b === ev.currentTarget);
        });
      });
    }

    applyAll();
  }

  // Mobile menu toggle
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

  // Snapshot age: never let a stale snapshot look like live odds
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      hydrateTimestamps();
      initMenu();
      initSnapshotAge();
      initPickFilters();
      initTableFilter();
    });
  } else {
    hydrateTimestamps();
    initMenu();
    initSnapshotAge();
    initPickFilters();
    initTableFilter();
  }
})();
