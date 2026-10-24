/* docs/assets/app.js — Progressive enhancement for mobile nav, filters & freshness */
(function () {
  "use strict";

  function init() {
    if (document.documentElement.dataset.docsAppInit === "1") return;
    document.documentElement.dataset.docsAppInit = "1";

    // 1. Mobile navigation drawer
    var btn = document.getElementById("nav-toggle");
    var nav = document.getElementById("site-nav");
    if (btn && nav) {
      btn.addEventListener("click", function () {
        var open = nav.classList.toggle("open");
        btn.setAttribute("aria-expanded", open ? "true" : "false");
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && nav.classList.contains("open")) {
          nav.classList.remove("open");
          btn.setAttribute("aria-expanded", "false");
        }
      });
    }

    // 2. Stale snapshot warning (>12h old)
    var bar = document.querySelector("[data-generated-at]");
    var alertBox = document.getElementById("stale-snapshot-alert");
    if (bar && alertBox) {
      var ts = Date.parse(bar.getAttribute("data-generated-at") || "");
      if (ts && Date.now() - ts > 12 * 3600 * 1000) {
        var hrs = Math.round((Date.now() - ts) / 3600000);
        alertBox.textContent =
          "Snapshot age notice: this build was generated " +
          hrs +
          "h ago (scheduled auto-refresh runs every 6 hours). Verify live lines before locking.";
        alertBox.hidden = false;
      }
    }

    // 3. Local timezone hint on <time data-utc="...">
    var times = document.querySelectorAll("time[data-utc]");
    for (var i = 0; i < times.length; i++) {
      var t = times[i];
      var ms = Date.parse(t.getAttribute("data-utc") || "");
      if (!isNaN(ms)) {
        try {
          t.title = "Local: " + new Date(ms).toLocaleString();
        } catch (_e) {}
      }
    }

    // 4. Unified filter controller for cards & table rows
    var list = document.getElementById("filter-list");
    if (!list) return;

    var items = Array.prototype.slice.call(list.querySelectorAll("[data-item]"));
    var qInput = document.getElementById("q");
    var compSel = document.getElementById("comp");
    var upBtn = document.getElementById("upcoming-btn");
    var pillBtns = Array.prototype.slice.call(document.querySelectorAll("[data-method-filter]"));
    var countEl = document.getElementById("visible-count");
    var emptyEl = document.getElementById("empty-state");

    var activeMethod = "";
    var hideStale = upBtn ? upBtn.getAttribute("aria-pressed") === "true" : false;

    function applyFilters() {
      var q = qInput ? qInput.value.trim().toLowerCase() : "";
      var comp = compSel ? compSel.value : "";
      var shown = 0;

      for (var j = 0; j < items.length; j++) {
        var el = items[j];
        var ok = true;
        if (hideStale && el.getAttribute("data-stale") === "1") ok = false;
        if (ok && activeMethod && el.getAttribute("data-method") !== activeMethod) ok = false;
        if (ok && comp && el.getAttribute("data-comp") !== comp) ok = false;
        if (ok && q) {
          var hay = (el.getAttribute("data-search") || "").toLowerCase();
          if (hay.indexOf(q) === -1) ok = false;
        }
        el.hidden = !ok;
        if (ok) shown++;
      }
      if (countEl) {
        countEl.textContent = shown + " / " + items.length + " shown";
      }
      if (emptyEl) {
        emptyEl.hidden = shown > 0;
      }
    }

    if (qInput) qInput.addEventListener("input", applyFilters);
    if (compSel) compSel.addEventListener("change", applyFilters);
    if (upBtn) {
      upBtn.addEventListener("click", function () {
        hideStale = !hideStale;
        upBtn.setAttribute("aria-pressed", hideStale ? "true" : "false");
        upBtn.classList.toggle("active", hideStale);
        applyFilters();
      });
    }
    for (var k = 0; k < pillBtns.length; k++) {
      (function (b) {
        b.addEventListener("click", function () {
          activeMethod = b.getAttribute("data-method-filter") || "";
          for (var x = 0; x < pillBtns.length; x++) {
            pillBtns[x].classList.toggle("active", pillBtns[x] === b);
          }
          applyFilters();
        });
      })(pillBtns[k]);
    }
    applyFilters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
