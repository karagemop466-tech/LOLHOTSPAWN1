/* LoL Hotspawn Picks — progressive enhancement: filters for the picks list.
   All content is server-rendered; this only hides/shows rows. */
(function () {
  var q = document.getElementById("f-q");
  if (!q) return;
  var tour = document.getElementById("f-tour");
  var src = document.getElementById("f-src");
  var soon = document.getElementById("f-soon");
  // deep-link support: picks.html?tour=<competition_id>&q=<term>&src=<source>
  try {
    var params = new URLSearchParams(location.search);
    if (tour && params.get("tour")) tour.value = params.get("tour");
    if (src && params.get("src")) src.value = params.get("src");
    if (q && params.get("q")) q.value = params.get("q");
    if (soon && params.get("soon") === "1") soon.checked = true;
  } catch (e) {}
  var count = document.getElementById("f-count");
  var matches = Array.prototype.slice.call(document.querySelectorAll(".match[data-searchable]"));
  var dayhdrs = Array.prototype.slice.call(document.querySelectorAll(".dayhdr[data-dayhdr]"));

  function apply() {
    var term = (q.value || "").trim().toLowerCase();
    var tsel = tour ? tour.value : "";
    var ssel = src ? src.value : "";
    var soonOn = soon && soon.checked;
    var now = Date.now();
    var shown = 0;
    matches.forEach(function (el) {
      var ok = true;
      if (term && (el.getAttribute("data-searchable") || "").indexOf(term) === -1) ok = false;
      if (ok && tsel && el.getAttribute("data-tour") !== tsel) ok = false;
      if (ok && ssel) {
        var s = el.getAttribute("data-src");
        if (ssel === "market" && s !== "pinnacle" && s !== "polymarket") ok = false;
        if (ssel === "model" && s !== "model") ok = false;
        if (ssel === "unresolved" && s !== "none") ok = false;
        if (ssel === "pinnacle" && s !== "pinnacle") ok = false;
        if (ssel === "polymarket" && s !== "polymarket") ok = false;
      }
      if (ok && soonOn) {
        var lock = Number(el.getAttribute("data-lock") || "0");
        if (!lock || lock - now > 24 * 3600 * 1000) ok = false;
      }
      el.classList.toggle("hidden", !ok);
      if (ok) shown++;
    });
    // hide empty day headers
    dayhdrs.forEach(function (h) {
      var n = h.nextElementSibling;
      var anyVisible = false;
      while (n && !n.hasAttribute("data-dayhdr")) {
        if (n.classList.contains("match") && !n.classList.contains("hidden")) anyVisible = true;
        n = n.nextElementSibling;
      }
      h.classList.toggle("hidden", !anyVisible);
    });
    if (count) count.textContent = shown + " match" + (shown === 1 ? "" : "es") + " shown";
  }

  [q, tour, src].forEach(function (el) { if (el) el.addEventListener("input", apply); if (el) el.addEventListener("change", apply); });
  if (soon) soon.addEventListener("change", apply);
  apply();
})();
