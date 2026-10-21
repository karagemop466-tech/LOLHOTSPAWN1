/* Progressive enhancement only: filtering + search on the pick lists. The page is fully
   readable with JavaScript disabled (every row is rendered server-side by scripts/build_site.py). */
(function () {
  "use strict";
  var list = document.getElementById("list");
  if (!list) return;
  var rows = Array.prototype.slice.call(list.querySelectorAll(".pick"));
  var shown = document.getElementById("shown");
  var state = { basis: "all", status: "all", q: "" };

  function apply() {
    var n = 0;
    rows.forEach(function (el) {
      var ok = true;
      if (state.basis !== "all" && el.dataset.basis !== state.basis) ok = false;
      if (state.status !== "all") {
        var s = el.dataset.status || "";
        if (state.status === "today" && !(s === "today" || s === "closing soon" || s === "locked")) ok = false;
        else if (state.status !== "today" && s !== state.status) ok = false;
      }
      if (state.q && (el.dataset.search || "").indexOf(state.q) === -1) ok = false;
      el.style.display = ok ? "" : "none";
      if (ok) n++;
    });
    if (shown) shown.textContent = String(n);
  }

  document.querySelectorAll(".fbtn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var key = btn.dataset.filter, val = btn.dataset.value;
      var isSame = state[key] === val;
      state[key] = isSame ? "all" : val;
      if (key === "status" && isSame) state.status = "all";
      document.querySelectorAll('.fbtn[data-filter="' + key + '"]').forEach(function (b) {
        b.classList.toggle("is-active", b.dataset.value === state[key]);
      });
      apply();
    });
  });

  var box = document.querySelector(".search");
  if (box) {
    box.addEventListener("input", function () {
      state.q = box.value.trim().toLowerCase();
      apply();
    });
  }

  // ?basis=market|model|unresolved deep links from the executive summary
  var params = new URLSearchParams(location.search);
  ["basis", "status"].forEach(function (key) {
    var val = params.get(key);
    if (!val) return;
    state[key] = val;
    document.querySelectorAll('.fbtn[data-filter="' + key + '"]').forEach(function (b) {
      b.classList.toggle("is-active", b.dataset.value === val);
    });
  });
  apply();
})();
