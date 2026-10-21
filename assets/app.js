(function () {
  "use strict";

  // 1. Show times in the visitor's own timezone (the page ships UTC and upgrades it).
  document.querySelectorAll("time.utc[data-utc]").forEach(function (el) {
    var raw = el.getAttribute("data-utc");
    var d = new Date(raw);
    if (isNaN(d.getTime())) return;
    try {
      el.textContent = d.toLocaleString(undefined, {
        weekday: "short", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
      });
      el.title = raw;
    } catch (err) { /* keep UTC text */ }
  });

  // 2. Mobile menu
  var btn = document.querySelector(".menu-btn");
  var nav = document.getElementById("nav");
  if (btn && nav) {
    btn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // 3. Filters on the picks page (progressive enhancement: everything is visible without JS)
  var list = document.getElementById("list");
  if (!list) return;
  var q = document.getElementById("q");
  var comp = document.getElementById("comp");
  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip[data-filter]"));
  var counter = document.getElementById("count");
  var empty = document.getElementById("empty");
  var cards = Array.prototype.slice.call(list.querySelectorAll(".card"));
  var activeMethod = "";

  function apply() {
    var term = (q && q.value || "").trim().toLowerCase();
    var tournament = comp && comp.value || "";
    var shown = 0;
    cards.forEach(function (card) {
      var okMethod = !activeMethod || card.getAttribute("data-method") === activeMethod;
      var okComp = !tournament || card.getAttribute("data-comp") === tournament;
      var okTerm = !term || (card.getAttribute("data-text") || "").indexOf(term) !== -1;
      var show = okMethod && okComp && okTerm;
      card.hidden = !show;
      if (show) shown++;
    });
    if (counter) counter.textContent = shown + " matches shown";
    if (empty) empty.hidden = shown !== 0;
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      chips.forEach(function (c) { c.classList.remove("active"); });
      chip.classList.add("active");
      activeMethod = chip.getAttribute("data-filter") || "";
      apply();
    });
  });
  if (q) q.addEventListener("input", apply);
  if (comp) comp.addEventListener("change", apply);
})();
