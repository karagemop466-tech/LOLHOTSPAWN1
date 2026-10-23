/* Hotspawn LoL Pick Desk - progressive enhancement only.
 * Every page is complete and readable without this file: the HTML carries
 * all matches, all picks and all source links. This script adds the mobile
 * menu, local-time tooltips and the client-side filters on picks.html.
 */
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  };

  /* ---------------------------------------------------------------- *
   * Mobile menu: the header collapses to a "Menu" button on phones.
   * ---------------------------------------------------------------- */
  function initMenu() {
    var btn = $(".menu-btn");
    var nav = document.getElementById("nav");
    if (!btn || !nav || btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      var open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.textContent = open ? "Close" : "Menu";
    });
    nav.addEventListener("click", function (ev) {
      if (ev.target && ev.target.tagName === "A") {
        nav.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
        btn.textContent = "Menu";
      }
    });
  }

  /* ---------------------------------------------------------------- *
   * Local time: <time data-utc="..."> already shows UTC, so it stays
   * readable when the browser has no Intl support.
   * ---------------------------------------------------------------- */
  function initTimes() {
    $$("[data-utc]").forEach(function (el) {
      var iso = el.getAttribute("data-utc");
      if (!iso) return;
      var d = new Date(iso);
      if (isNaN(d.getTime())) return;
      var local;
      try {
        local = d.toLocaleString(undefined, {
          weekday: "short", month: "short", day: "numeric",
          hour: "2-digit", minute: "2-digit"
        });
      } catch (err) {
        return;
      }
      el.setAttribute("title", iso + " UTC = " + local + " local");
    });
  }

  /* ---------------------------------------------------------------- *
   * Snapshot age: says out loud when the committed data is stale.
   * ---------------------------------------------------------------- */
  function initSnapshotAge() {
    var el = document.getElementById("snapshot-age");
    if (!el) return;
    var fetched = el.getAttribute("data-fetched");
    if (!fetched) return;
    var t = Date.parse(fetched);
    if (isNaN(t)) return;
    var hours = (Date.now() - t) / 3600000;
    if (hours > 8) {
      el.className += " stale-warning";
      el.textContent += " - this snapshot is " + hours.toFixed(0) +
        " hours old; the refresh may have failed. Check the source timestamps before betting.";
    }
  }

  /* ---------------------------------------------------------------- *
   * picks.html filters: search, tournament, pick type, kick-off window.
   * State lives in the URL so a filtered view can be shared or opened
   * from the summary page (?method=market, ?window=today, ...).
   * ---------------------------------------------------------------- */
  function initPicks() {
    var list = document.getElementById("list");
    var q = document.getElementById("q");
    if (!list || !q) return;

    var comp = document.getElementById("comp");
    var count = document.getElementById("count");
    var empty = document.getElementById("empty");
    var reset = document.getElementById("reset");
    var clear = document.getElementById("clear");
    var typeChips = $$(".chip[data-filter]");
    var winChips = $$(".chip[data-window]");
    var cards = $$(".card", list);
    var groups = $$(".daygroup", list);

    var params = new URLSearchParams(window.location.search);
    var state = {
      q: params.get("q") || "",
      comp: params.get("comp") || "",
      method: params.get("method") || "",
      window: params.get("window") || ""
    };
    if (state.q) q.value = state.q;
    if (state.comp && comp) comp.value = state.comp;

    function utcDay(ms) { return new Date(ms).toISOString().slice(0, 10); }
    var nowMs = Date.now();
    var today = utcDay(nowMs);
    var tomorrow = utcDay(nowMs + 86400000);

    function markChips(chips, value) {
      chips.forEach(function (c) {
        var on = (c.getAttribute("data-filter") || c.getAttribute("data-window") || "") === value;
        c.classList.toggle("active", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });
    }
    markChips(typeChips, state.method);
    markChips(winChips, state.window);

    function syncUrl() {
      var next = new URLSearchParams();
      if (state.q.trim()) next.set("q", state.q.trim());
      if (state.comp) next.set("comp", state.comp);
      if (state.method) next.set("method", state.method);
      if (state.window) next.set("window", state.window);
      var qs = next.toString();
      try {
        window.history.replaceState(null, "", qs ? "?" + qs : window.location.pathname);
      } catch (err) { /* file:// or a locked-down context */ }
    }

    function inWindow(card) {
      if (!state.window) return true;
      var start = card.getAttribute("data-start") || "";
      var day = start.slice(0, 10);
      if (state.window === "today") return day === today;
      if (state.window === "tomorrow") return day === tomorrow;
      if (state.window === "next7") return day >= today && day <= utcDay(nowMs + 7 * 86400000);
      if (state.window === "upcoming") return start > new Date(nowMs).toISOString().slice(0, 19);
      return true;
    }

    function apply() {
      var needle = state.q.trim().toLowerCase();
      var shown = 0;
      cards.forEach(function (card) {
        var ok = true;
        if (needle && (card.getAttribute("data-text") || "").toLowerCase().indexOf(needle) === -1) ok = false;
        if (ok && state.comp && card.getAttribute("data-comp") !== state.comp) ok = false;
        if (ok && state.method && card.getAttribute("data-method") !== state.method) ok = false;
        if (ok && !inWindow(card)) ok = false;
        card.hidden = !ok;
        if (ok) shown += 1;
      });
      groups.forEach(function (group) {
        var visible = group.querySelectorAll(".card:not([hidden])").length;
        var keepNote = !!group.querySelector(".empty-day") && shown === 0 &&
          !needle && !state.comp && !state.method && !state.window;
        group.hidden = visible === 0 && !keepNote;
      });
      if (count) {
        count.textContent = shown + (shown === 1 ? " match shown" : " matches shown") +
          (shown === cards.length ? "" : " of " + cards.length);
      }
      if (empty) empty.hidden = shown !== 0;
      syncUrl();
    }

    function resetAll() {
      state.q = ""; state.comp = ""; state.method = ""; state.window = "";
      q.value = "";
      if (comp) comp.value = "";
      markChips(typeChips, "");
      markChips(winChips, "");
      apply();
    }

    q.addEventListener("input", function () { state.q = q.value || ""; apply(); });
    q.addEventListener("search", function () { state.q = q.value || ""; apply(); });
    if (comp) {
      comp.addEventListener("change", function () { state.comp = comp.value || ""; apply(); });
    }
    typeChips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        state.method = chip.getAttribute("data-filter") || "";
        markChips(typeChips, state.method);
        apply();
      });
    });
    winChips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        state.window = chip.getAttribute("data-window") || "";
        markChips(winChips, state.window);
        apply();
      });
    });
    if (reset) reset.addEventListener("click", resetAll);
    if (clear) clear.addEventListener("click", resetAll);

    apply();
  }

  /* ---------------------------------------------------------------- *
   * Back to top: the pick list is long on a phone.
   * ---------------------------------------------------------------- */
  function initToTop() {
    var btn = document.getElementById("totop");
    if (!btn || btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function init() {
    initMenu();
    initTimes();
    initSnapshotAge();
    initPicks();
    initToTop();
  }

  // Run now (the document is already parsed when this file is deferred at the
  // end of the body) and again on DOMContentLoaded. Every initialiser is
  // idempotent, so a second pass cannot double-bind a handler.
  init();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
