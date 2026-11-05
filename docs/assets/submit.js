// The Submit page (docs/submit.md): it checks that every required item is answered, and only then lets the
// answers go, as an email to the developer (or copied, or saved as a text file). Nothing leaves the browser
// until the visitor sends that email. Loaded on every page (mkdocs.yml, extra_javascript); it does nothing
// where the form is not.
(function () {
  "use strict";

  function start() {
    var form = document.getElementById("submit-form");
    if (!form || form.dataset.ready) return;
    form.dataset.ready = "1";
    var to = form.dataset.to;

    var CRITERIA = [
      ["contact", "Your name, email, and permission"],
      ["1", "1. The original video, and how it will be sent"],
      ["2", "2. The field of view, angular scale, or device and zoom"],
      ["3", "3. The range to the object"],
      ["4", "4. The motion of the camera"],
      ["5", "5. The angle to the line of sight"],
      ["6", "6. The direction the camera faced"],
      ["7", "7. Date, time, time zone, latitude, longitude"],
      ["8", "8. The height above sea level"],
    ];

    // the time zones: the browser's own list, with the visitor's own chosen
    var tz = form.elements.tz;
    var zones = ["UTC"];
    try { zones = zones.concat(Intl.supportedValuesOf("timeZone").filter(function (z) { return z !== "UTC"; })); }
    catch (e) { /* an older browser: UTC, and the offsets below */ }
    for (var h = -12; h <= 14; h++) {
      if (h) zones.push("UTC" + (h > 0 ? "+" : "−") + Math.abs(h));
    }
    zones.forEach(function (z) {
      var o = document.createElement("option");
      o.value = o.textContent = z;
      tz.appendChild(o);
    });
    try {
      var here = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (here && zones.indexOf(here) >= 0) tz.value = here;
    } catch (e) { /* leave it to the visitor */ }

    var list = document.getElementById("sf-checklist");
    var items = {};
    CRITERIA.forEach(function (c) {
      var li = document.createElement("li");
      li.textContent = c[1];
      list.appendChild(li);
      items[c[0]] = li;
    });

    function value(name) {
      var el = form.elements[name];
      if (!el) return "";
      if (el instanceof RadioNodeList) return el.value || "";
      if (el.type === "checkbox") return el.checked ? "yes" : "";
      return (el.value || "").trim();
    }

    // a field shown only for one answer (data-when="delivery=link") is required only then
    function shown(el) {
      var box = el.closest("[data-when]");
      if (!box) return true;
      var w = box.dataset.when.split("=");
      return value(w[0]) === w[1];
    }

    function refresh() {
      form.querySelectorAll("[data-when]").forEach(function (box) {
        var w = box.dataset.when.split("=");
        box.hidden = value(w[0]) !== w[1];
      });
      // the fields the moving camera and the link need, required only when shown
      ["link", "speed", "heading"].forEach(function (n) {
        form.elements[n].required = shown(form.elements[n]);
      });
    }

    function fieldOk(el) {
      if (!shown(el)) return true;
      return el.checkValidity();
    }

    function criterionOk(key) {
      var set = form.querySelector('fieldset[data-criterion="' + key + '"]');
      var ok = Array.prototype.every.call(set.querySelectorAll("input, select, textarea"), fieldOk);
      // the field of view, or the angular scale, or the device and its zoom setting to look them up from
      if (key === "2") ok = ok && (value("hfov") !== "" || value("scale") !== "" ||
                                   (value("device") !== "" && value("zoom") !== ""));
      return ok;
    }

    function check() {
      refresh();
      var all = true;
      CRITERIA.forEach(function (c) {
        var ok = criterionOk(c[0]);
        items[c[0]].classList.toggle("sf-done", ok);
        all = all && ok;
      });
      ["sf-send", "sf-copy", "sf-download"].forEach(function (id) {
        document.getElementById(id).disabled = !all;
      });
      return all;
    }

    // the visitor sees what is wrong in a field once they have left it
    form.addEventListener("focusout", function (e) {
      if (e.target.matches("input, select, textarea")) e.target.classList.add("sf-touched");
    });
    form.addEventListener("input", check);
    form.addEventListener("change", check);

    function withUnit(name) {
      var v = value(name);
      return v === "" ? "" : v + " " + value(name + "_unit");
    }

    function answers() {
      var moving = value("platform") === "moving";
      var sections = [
        ["Submitted by", [["Name", value("name")], ["Email", value("email")],
          ["Permission to analyze and contact", value("permission")]]],
        ["1. The video", [["File name", value("filename")],
          ["Sent by", value("delivery") === "link" ? "download link" : "attached to this email"],
          ["Link", value("delivery") === "link" ? value("link") : ""],
          ["Recorded by", value("recorder")], ["Original and unaltered", value("original")]]],
        ["2. Field of view", [["Horizontal field of view (deg)", value("hfov")],
          ["Angular scale", withUnit("scale")], ["Device or camera", value("device")], ["Lens", value("lens")],
          ["Zoom", value("zoom")], ["Observation mode", value("mode")]]],
        ["3. Range", [["Range", withUnit("range")],
          ["Range rate (+ away, - closer)", withUnit("range_rate")]]],
        ["4. Camera motion", moving ? [["Moving", "yes"], ["Platform", value("platform_type")],
          ["Speed", withUnit("speed")], ["Heading (deg true)", value("heading")],
          ["Climb or descent rate", withUnit("climb")], ["Maneuvering", value("maneuver")], ["Trajectory log", value("platform_log")]]
          : [["Moving", "no, stationary"]]],
        ["5. Object motion vs. line of sight", [["Angle (deg)", value("los_angle")]]],
        ["6. Camera direction", [["Azimuth (deg true)", value("azimuth")],
          ["Elevation above horizon (deg)", value("elevation")]]],
        ["7. When and where", [["Date", value("date")], ["Time (start of video)", value("time")],
          ["Time zone", value("tz")], ["Latitude", value("lat")], ["Longitude", value("lon")]]],
        ["8. Height", [["Height above sea level", withUnit("height")]]],
        ["9. Weather (optional)", [["Weather", value("weather")]]],
        ["10. Reference object (optional)", [["Object", value("ref_object")], ["Size", value("ref_size")]]],
        ["Notes", [["Notes", value("notes")]]],
      ];
      var lines = ["mcDonald video submission", ""];
      sections.forEach(function (s) {
        var rows = s[1].filter(function (r) { return r[1] !== ""; });
        if (!rows.length) return;
        lines.push(s[0]);
        rows.forEach(function (r) { lines.push("  " + r[0] + ": " + r[1].replace(/\n/g, "\n    ")); });
        lines.push("");
      });
      return lines.join("\n");
    }

    function subject() {
      return "mcDonald video submission: " + value("filename") + " (" + value("date") + ")";
    }

    function after() {
      document.getElementById("sf-address").textContent = to;
      document.getElementById("sf-after").hidden = false;
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      form.querySelectorAll("input, select, textarea").forEach(function (el) { el.classList.add("sf-touched"); });
      if (!check()) return;
      var body = answers();
      if (value("delivery") === "attach") body += "\n(Please attach the video file to this email before sending.)\n";
      window.location.href = "mailto:" + to + "?subject=" + encodeURIComponent(subject()) +
        "&body=" + encodeURIComponent(body.replace(/\n/g, "\r\n"));
      after();
    });

    document.getElementById("sf-copy").addEventListener("click", function () {
      if (!check()) return;
      var button = this;
      navigator.clipboard.writeText(subject() + "\n\n" + answers()).then(function () {
        button.textContent = "Copied";
        setTimeout(function () { button.textContent = "Copy answers"; }, 2000);
      });
      after();
    });

    document.getElementById("sf-download").addEventListener("click", function () {
      if (!check()) return;
      var a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([answers()], { type: "text/plain" }));
      a.download = "mcdonald-submission-" + (value("date") || "video") + ".txt";
      document.body.appendChild(a);
      a.click();
      a.remove();
      after();
    });

    check();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
