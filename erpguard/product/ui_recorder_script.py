from __future__ import annotations

import json


_SELECTOR_PRIORITY_ATTRS = ["data-testid", "aria-label", "name", "placeholder"]

_SECRET_FIELD_NAMES = ["password", "token", "secret", "key", "api_key", "apikey", "auth", "credential"]


def build_recorder_script(rsid: str, api_base: str = "") -> str:
    rsid_json = json.dumps(rsid)
    api_base_json = json.dumps(api_base.rstrip("/"))
    return f"""
<script id="erpguard-recorder-s21">
(function () {{
  var rsid = {rsid_json};
  var apiBase = {api_base_json};
  var endpoint = apiBase + "/v1/record-to-skill/sessions/" + rsid + "/events";
  var finishEndpoint = apiBase + "/v1/record-to-skill/sessions/" + rsid + "/finish";
  var eventCount = 0;

  // ── overlay ──────────────────────────────────────────────────────────
  var overlay = document.createElement("div");
  overlay.id = "erpguard-recorder-overlay";
  overlay.setAttribute("data-testid", "recorder-overlay");
  overlay.setAttribute("role", "status");
  overlay.setAttribute("aria-label", "ERPGuard recorder overlay");
  overlay.style.cssText = [
    "position:fixed", "bottom:20px", "right:20px",
    "background:#1d1a16", "color:#f5efe6",
    "padding:10px 16px", "border-radius:12px",
    "z-index:2147483647", "font-family:monospace",
    "font-size:13px", "display:flex", "gap:10px",
    "align-items:center", "box-shadow:0 4px 16px rgba(0,0,0,.4)",
  ].join(";");
  overlay.innerHTML =
    "<span>Recording</span>" +
    "<span id=\\"erpguard-recorder-count\\" data-testid=\\"recorder-count\\">0 events</span>" +
    "<button id=\\"erpguard-recorder-stop\\" data-testid=\\"recorder-stop\\"" +
    " aria-label=\\"Stop recording\\"" +
    " style=\\"background:#9b2c2c;border:none;color:#fff;padding:5px 10px;" +
    "border-radius:6px;cursor:pointer;font-family:inherit\\">Stop</button>";
  document.body.appendChild(overlay);

  var countEl = document.getElementById("erpguard-recorder-count");
  function updateCount() {{
    if (countEl) countEl.textContent = eventCount + " event" + (eventCount === 1 ? "" : "s");
  }}

  // ── selector candidate extraction ────────────────────────────────────
  var PRIORITY_ATTRS = {json.dumps(_SELECTOR_PRIORITY_ATTRS)};

  function bestSelector(el) {{
    for (var i = 0; i < PRIORITY_ATTRS.length; i++) {{
      var attr = PRIORITY_ATTRS[i];
      var val = el.getAttribute(attr);
      if (val) return "[" + attr + "='" + val.replace(/'/g, "\\\\'") + "']";
    }}
    var tag = (el.tagName || "").toLowerCase();
    var text = (el.textContent || el.innerText || "").trim().slice(0, 40);
    if (text) return tag + ":text('" + text.replace(/'/g, "\\\\'") + "')";
    return tag || null;
  }}

  // ── secret redaction ─────────────────────────────────────────────────
  var SECRET_KEYWORDS = {json.dumps(_SECRET_FIELD_NAMES)};

  function isSecretField(el) {{
    if (el.type === "password") return true;
    var nameId = ((el.name || "") + " " + (el.id || "") + " " + (el.getAttribute("data-testid") || "")).toLowerCase();
    return SECRET_KEYWORDS.some(function(k) {{ return nameId.indexOf(k) !== -1; }});
  }}

  function safeValue(el, value) {{
    return isSecretField(el) ? "[REDACTED]" : value;
  }}

  // ── event posting ─────────────────────────────────────────────────────
  function postEvent(payload) {{
    eventCount++;
    updateCount();
    var body = JSON.stringify(payload);
    var blob = new Blob([body], {{ type: "application/json" }});
    try {{
      if (navigator.sendBeacon(endpoint, blob)) return;
    }} catch (e) {{ }}
    fetch(endpoint, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: body,
      keepalive: true,
    }}).catch(function(e) {{ console.warn("[ERPGuard recorder] event failed", e); }});
  }}

  // ── capture page load ─────────────────────────────────────────────────
  postEvent({{
    event_type: "page_load",
    url: window.location.href,
    selector: null,
    element_text: document.title || null,
    element_label: null,
    input_value: null,
    metadata: {{ source: "recorder_s21", page: window.location.pathname }},
  }});

  // ── capture clicks (generic, delegated) ──────────────────────────────
  document.addEventListener("click", function(e) {{
    var stop = document.getElementById("erpguard-recorder-stop");
    if (stop && (e.target === stop || stop.contains(e.target))) return;
    var el = e.target;
    var candidate = el.closest("a, button, [role='button'], input[type='submit'], input[type='button'], [data-testid]");
    if (!candidate) candidate = el;
    var sel = bestSelector(candidate);
    var etype = candidate.tagName === "A" ? "click" : "click";
    postEvent({{
      event_type: etype,
      url: candidate.href || window.location.href,
      selector: sel,
      element_text: (candidate.textContent || candidate.innerText || "").trim().slice(0, 100) || null,
      element_label: candidate.getAttribute("aria-label") || null,
      input_value: null,
      metadata: {{ source: "recorder_s21", tag: (candidate.tagName || "").toLowerCase() }},
    }});
  }}, true);

  // ── capture input / change ────────────────────────────────────────────
  document.addEventListener("change", function(e) {{
    var el = e.target;
    if (!el || !["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName)) return;
    postEvent({{
      event_type: "fill",
      url: window.location.href,
      selector: bestSelector(el),
      element_text: null,
      element_label: el.getAttribute("aria-label") || el.getAttribute("placeholder") || null,
      input_value: safeValue(el, el.value),
      metadata: {{ source: "recorder_s21", tag: el.tagName.toLowerCase(), type: el.type || null }},
    }});
  }}, true);

  // ── capture navigation (pushState / replaceState) ─────────────────────
  var _pushState = history.pushState.bind(history);
  var _replaceState = history.replaceState.bind(history);
  function onNav() {{
    postEvent({{
      event_type: "navigate",
      url: window.location.href,
      selector: null,
      element_text: document.title || null,
      element_label: null,
      input_value: null,
      metadata: {{ source: "recorder_s21" }},
    }});
  }}
  history.pushState = function() {{ _pushState.apply(history, arguments); onNav(); }};
  history.replaceState = function() {{ _replaceState.apply(history, arguments); onNav(); }};
  window.addEventListener("popstate", onNav);

  // ── stop button ───────────────────────────────────────────────────────
  document.getElementById("erpguard-recorder-stop").addEventListener("click", function() {{
    fetch(finishEndpoint, {{ method: "POST" }})
      .then(function() {{
        overlay.style.background = "#186a3b";
        overlay.innerHTML = "<span>Recording stopped &#10003; — return to /demo to continue.</span>";
        setTimeout(function() {{ if (overlay.parentNode) overlay.parentNode.removeChild(overlay); }}, 4000);
      }})
      .catch(function(e) {{
        overlay.innerHTML = "<span style='color:#fca5a5'>Stop failed: " + e.message + "</span>";
      }});
  }});
}})();
</script>"""


def selector_priority_attrs() -> list[str]:
    return list(_SELECTOR_PRIORITY_ATTRS)


def secret_field_names() -> list[str]:
    return list(_SECRET_FIELD_NAMES)
