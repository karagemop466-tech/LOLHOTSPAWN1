/* Progressive enhancement for the LoL pick'em board: local-time rendering and
   client-side filtering/sorting on the picks page. Everything works without it. */
(function () {
  "use strict";

  // 1. Show kickoff times in the visitor's timezone next to the UTC stamp.
  document.querySelectorAll("[data-utc]").forEach(function (el) {
    var raw = el.getAttribute("data-utc");
    if (!raw) return;
    var d = new Date(raw);
    if (isNaN(d.getTime())) return;
    var local = d.toLocaleString(undefined, {
      weekday: "short", day: "numeric", month: "short",
      hour: "2-digit", minute: "2-digit"
    });
    el.textContent = local;
  });

  // 2. Filtering / sorting of pick cards.
  var list = document.getElementById("picklist");
  if (!list) return;
  var search = document.getElementById("search");
  var league = document.getElementById("league");
  var sort = document.getElementById("sort");
  var cards = Array.prototype.slice.call(list.querySelectorAll(".card"));

  function apply() {
    var q = (search && search.value || "").toLowerCase().trim();
    var lg = league && league.value;
    cards.forEach(function (c) {
      var text = (c.getAttribute("data-teams") || "").toLowerCase() + " " +
                 (c.getAttribute("data-league") || "").toLowerCase();
      var okText = !q || text.indexOf(q) !== -1;
      var okLeague = !lg || c.getAttribute("data-league") === lg;
      c.style.display = (okText && okLeague) ? "" : "none";
    });
    var visible = cards.filter(function (c) { return c.style.display !== "none"; });
    var mode = sort && sort.value;
    if (mode === "prob") {
      visible.sort(function (a, b) {
        return parseFloat(b.getAttribute("data-prob")) - parseFloat(a.getAttribute("data-prob"));
      });
    } else if (mode === "edge") {
      visible.sort(function (a, b) {
        return parseFloat(a.getAttribute("data-edge")) - parseFloat(b.getAttribute("data-edge"));
      });
    } else {
      visible.sort(function (a, b) {
        return (a.getAttribute("data-time") || "").localeCompare(b.getAttribute("data-time") || "");
      });
    }
    visible.forEach(function (c) { list.appendChild(c); });
  }

  [search, league, sort].forEach(function (el) {
    if (el) el.addEventListener("input", apply);
    if (el) el.addEventListener("change", apply);
  });
  apply();
})();
