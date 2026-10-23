/* Hotspawn LoL Pick Desk - no dependencies.
   Everything here is wired to elements the generator actually emits:
   tools/site.py is the single source of those ids/classes. */
(function () {
  "use strict";

  /* ------------------------------------------------------------------ times */
  function hydrateTimestamps() {
    var nodes = document.querySelectorAll("[data-utc]");
    for (var i = 0; i < nodes.length; i++) {
      var iso = nodes[i].getAttribute("data-utc");
      if (!iso) continue;
      var d = new Date(iso);
      if (isNaN(d.getTime())) continue;
      try {
        var local = d.toLocaleString(undefined, {
          month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
        });
        nodes[i].setAttribute("title", "UTC: " + iso + " | Local: " + local);
        if (nodes[i].hasAttribute("data-show-local")) {
          nodes[i].textContent = local + " (" + iso.slice(11, 16) + " UTC)";
          nodes[i].removeAttribute("data-show-local");
        }
      } catch (err) {
        /* keep the static UTC text */
      }
    }
  }

  /* ------------------------------------------------------------------- menu */
  function initMenu() {
    var nav = document.getElementById("nav");
    if (!nav) return;
    var toggles = document.querySelectorAll(".menu-btn, .tabmenu");

    function setOpen(open) {
      nav.classList.toggle("open", open);
      for (var i = 0; i < toggles.length; i++) {
        toggles[i].setAttribute("aria-expanded", open ? "true" : "false");
      }
    }
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener("click", function (ev) {
        ev.preventDefault();
        setOpen(!nav.classList.contains("open"));
      });
    }
    nav.addEventListener("click", function (ev) {
      if (ev.target && ev.target.tagName === "A") setOpen(false);
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") setOpen(false);
    });
    document.addEventListener("click", function (ev) {
      if (!nav.classList.contains("open")) return;
      if (nav.contains(ev.target)) return;
      for (var j = 0; j < toggles.length; j++) {
        if (toggles[j] === ev.target) return;
      }
      setOpen(false);
    });
  }

  /* ---------------------------------------------------------------- filters */
  function slug(value) {
    return String(value || "").toLowerCase()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  }

  function initPickFilters() {
    var list = document.getElementById("list");
    var searchEl = document.getElementById("q");
    var compEl = document.getElementById("comp");
    var windowEl = document.getElementById("window");
    var sortEl = document.getElementById("sort");
    var countEl = document.getElementById("count");
    var emptyEl = document.getElementById("empty");
    var chips = document.querySelectorAll("#chips .chip");
    var reset = document.getElementById("reset");
    if (!list || !searchEl) return;

    var groups = list.querySelectorAll(".daygroup");
    var items = list.querySelectorAll(".pick");
    var activeMethod = "";

    function matches(el) {
      var q = slug(searchEl.value);
      if (q && (el.getAttribute("data-text") || "").indexOf(q) === -1) return false;
      if (compEl && compEl.value && el.getAttribute("data-comp") !== compEl.value) return false;
      if (activeMethod && el.getAttribute("data-method") !== activeMethod) return false;
      if (windowEl && windowEl.value) {
        var hours = parseFloat(el.getAttribute("data-hours") || "99999");
        if (!(hours > 0) || hours > parseFloat(windowEl.value)) return false;
      }
      return true;
    }

    function sortGroup(group) {
      var mode = sortEl ? sortEl.value : "kickoff";
      var nodes = Array.prototype.slice.call(group.querySelectorAll(".pick"));
      nodes.sort(function (a, b) {
        if (mode === "prob_desc") {
          return parseFloat(b.getAttribute("data-favprob") || "0") -
                 parseFloat(a.getAttribute("data-favprob") || "0");
        }
        if (mode === "comp") {
          var an = (a.getAttribute("data-comp") || "").toLowerCase();
          var bn = (b.getAttribute("data-comp") || "").toLowerCase();
          if (an < bn) return -1;
          if (an > bn) return 1;
        }
        return parseFloat(a.getAttribute("data-kickoff") || "0") -
               parseFloat(b.getAttribute("data-kickoff") || "0");
      });
      for (var i = 0; i < nodes.length; i++) group.appendChild(nodes[i]);
    }

    function apply() {
      var shown = 0;
      for (var g = 0; g < groups.length; g++) {
        var group = groups[g];
        sortGroup(group);
        var rows = group.querySelectorAll(".pick");
        var visibleInGroup = 0;
        for (var r = 0; r < rows.length; r++) {
          var ok = matches(rows[r]);
          rows[r].classList.toggle("is-hidden", !ok);
          if (ok) { visibleInGroup++; shown++; }
        }
        var head = group.querySelector(".dayhead");
        if (head) head.classList.toggle("is-hidden", visibleInGroup === 0);
        group.classList.toggle("is-hidden", visibleInGroup === 0);
      }
      if (countEl) countEl.textContent = shown + " of " + items.length + " matches shown";
      if (emptyEl) emptyEl.hidden = shown !== 0;
    }

    function setChip(value) {
      activeMethod = value || "";
      for (var i = 0; i < chips.length; i++) {
        chips[i].classList.toggle("active", (chips[i].getAttribute("data-filter") || "") === activeMethod);
      }
    }

    for (var c = 0; c < chips.length; c++) {
      chips[c].addEventListener("click", function (ev) {
        setChip(ev.currentTarget.getAttribute("data-filter") || "");
        apply();
      });
    }

    /* URL parameters: picks.html?comp=...&q=...&method=... */
    var params = new URLSearchParams(window.location.search);
    if (params.get("comp") && compEl) compEl.value = params.get("comp");
    if (params.get("q")) searchEl.value = params.get("q");
    if (params.get("method")) setChip(params.get("method"));

    [searchEl, compEl, windowEl, sortEl].forEach(function (ctrl) {
      if (!ctrl) return;
      ctrl.addEventListener("input", apply);
      ctrl.addEventListener("change", apply);
    });
    if (reset) {
      reset.addEventListener("click", function () {
        searchEl.value = "";
        if (compEl) compEl.value = "";
        if (windowEl) windowEl.value = "";
        setChip("");
        apply();
      });
    }
    apply();
  }

  function boot() {
    hydrateTimestamps();
    initMenu();
    initPickFilters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
