(function () {
  "use strict";

  /* ------------------------------------------------------------------ *
   * 1. Local-time tooltips (static HTML keeps a UTC fallback)           *
   * ------------------------------------------------------------------ */
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
        /* keep the UTC text */
      }
    }
  }

  /* ------------------------------------------------------------------ *
   * 2. Mobile menu button (was rendered but never wired up)             *
   * ------------------------------------------------------------------ */
  function initMenu() {
    var btn = document.querySelector(".menu-btn");
    var nav = document.getElementById("nav");
    if (!btn || !nav || btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";

    function setOpen(open) {
      nav.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.textContent = open ? "Close" : "Menu";
    }

    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      setOpen(!nav.classList.contains("open"));
    });

    // Close the menu after following a link, and on Escape.
    nav.addEventListener("click", function (ev) {
      if (ev.target && ev.target.tagName === "A") setOpen(false);
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") setOpen(false);
    });
  }

  /* ------------------------------------------------------------------ *
   * 3. Picks page: search + tournament filter + method chips            *
   *    (the markup uses #q, #comp, .chip[data-filter], #list, #count)   *
   * ------------------------------------------------------------------ */
  function initPickFilters() {
    var searchEl = document.getElementById("q");
    var compEl = document.getElementById("comp");
    var listEl = document.getElementById("list");
    var countEl = document.getElementById("count");
    var emptyEl = document.getElementById("empty");
    var chips = document.querySelectorAll(".chip[data-filter]");
    if (!listEl || listEl.dataset.bound === "1") return;
    listEl.dataset.bound = "1";

    var cards = Array.prototype.slice.call(listEl.querySelectorAll(".card"));
    var state = { q: "", comp: "", method: "" };

    var params = new URLSearchParams(window.location.search);
    if (params.get("q") && searchEl) {
      state.q = params.get("q");
      searchEl.value = state.q;
    }
    if (params.get("comp") && compEl) {
      state.comp = params.get("comp");
      compEl.value = state.comp;
    }
    if (params.get("method")) {
      state.method = params.get("method");
      for (var c = 0; c < chips.length; c++) {
        chips[c].classList.toggle("active", chips[c].getAttribute("data-filter") === state.method);
      }
    }

    function apply() {
      var q = state.q.trim().toLowerCase();
      var shown = 0;
      for (var i = 0; i < cards.length; i++) {
        var card = cards[i];
        var ok = true;
        if (q) {
          var hay = (card.getAttribute("data-text") || "").toLowerCase();
          if (hay.indexOf(q) === -1) ok = false;
        }
        if (ok && state.comp && card.getAttribute("data-comp") !== state.comp) ok = false;
        if (ok && state.method && card.getAttribute("data-method") !== state.method) ok = false;
        card.hidden = !ok;
        if (ok) shown++;
      }
      if (countEl) {
        countEl.textContent =
          shown + (shown === 1 ? " match shown" : " matches shown") +
          (shown === cards.length ? "" : " of " + cards.length);
      }
      if (emptyEl) emptyEl.hidden = shown !== 0;
    }

    if (searchEl) {
      searchEl.addEventListener("input", function () {
        state.q = searchEl.value || "";
        apply();
      });
    }
    if (compEl) {
      compEl.addEventListener("change", function () {
        state.comp = compEl.value || "";
        apply();
      });
    }
    for (var k = 0; k < chips.length; k++) {
      chips[k].addEventListener("click", function (ev) {
        for (var m = 0; m < chips.length; m++) chips[m].classList.remove("active");
        ev.currentTarget.classList.add("active");
        state.method = ev.currentTarget.getAttribute("data-filter") || "";
        apply();
      });
    }

    apply();
  }

  /* ------------------------------------------------------------------ *
   * 4. Back-to-top: the all-picks list is long on a phone               *
   * ------------------------------------------------------------------ */
  function initToTop() {
    var btn = document.getElementById("totop");
    if (!btn || btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function init() {
    hydrateTimestamps();
    initMenu();
    initPickFilters();
    initToTop();
  }

  // Run now and again once the document is ready. Both passes are idempotent, so a
  // script evaluated before DOMContentLoaded (and a test harness that evaluates it
  // afterwards) both end up with exactly one handler per control.
  init();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
