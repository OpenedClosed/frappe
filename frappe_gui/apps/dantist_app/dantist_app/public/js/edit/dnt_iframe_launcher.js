// === DNT IFrame Launcher — v3 ===
// Универсальный лаунчер плавающего iframe по конфигу в options DocField.
// Ищет поля с options, содержащими [IFRAME], и рисует кнопку вместо инпута.

(() => {
  if (window.__DNT_IFRAME_LAUNCHER_V3) return;
  window.__DNT_IFRAME_LAUNCHER_V3 = true;

  const LOG_PREFIX = "[DNT-IFRAME]";
  const log = (...args) => console.log(LOG_PREFIX, ...args);
  const warn = (...args) => console.warn(LOG_PREFIX, ...args);
  const err = (...args) => console.error(LOG_PREFIX, ...args);

  const CFG = {
    panelId: "dnt-iframe-panel",
    iframeId: "dnt-iframe-panel-frame",
    envTagId: "dnt-iframe-panel-env",
    cssId: "dnt-iframe-panel-css",
    marker: "[IFRAME]",
    defaultWidth: 520,
    defaultHeight: 420,
  };

  log("script loaded, waiting for Form class", { marker: CFG.marker });

  function get_env() {
    const env =
      (frappe.boot && frappe.boot.iframe_mode) ||
      frappe.boot?.pana_portal_env ||
      "DEV";
    const val = String(env || "DEV").toUpperCase();
    log("get_env ->", val);
    return val;
  }

  function ensure_styles() {
    if (document.getElementById(CFG.cssId)) return;

    const style = document.createElement("style");
    style.id = CFG.cssId;
    style.textContent = `
      #${CFG.panelId} {
        position: fixed;
        z-index: 1050;
        right: 24px;
        bottom: 24px;
        width: ${CFG.defaultWidth}px;
        height: ${CFG.defaultHeight}px;
        min-width: 360px;
        min-height: 260px;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.35);
        display: none;
        flex-direction: column;
        overflow: hidden;
        resize: both;
      }

      #${CFG.panelId}.dnt-visible {
        display: flex;
      }

      #${CFG.panelId}.dnt-max {
        resize: none;
      }

      #${CFG.panelId} .dnt-panel-header {
        flex: 0 0 auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 10px;
        background: rgba(15, 23, 42, 0.88);
        color: #f9fafb;
        cursor: move;
        user-select: none;
      }

      #${CFG.panelId} .dnt-panel-title {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        font-weight: 500;
      }

      #${CFG.envTagId} {
        font-size: 10px;
        text-transform: uppercase;
        padding: 2px 6px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.35);
      }

      #${CFG.panelId} .dnt-panel-actions {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      #${CFG.panelId} .dnt-panel-btn {
        border: none;
        background: transparent;
        color: #e5e7eb;
        width: 24px;
        height: 24px;
        border-radius: 999px;
        padding: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 13px;
      }

      #${CFG.panelId} .dnt-panel-btn:hover {
        background: rgba(148, 163, 184, 0.35);
        color: #ffffff;
      }

      #${CFG.panelId} .dnt-panel-body {
        flex: 1 1 auto;
        border-top: 1px solid #e5e7eb;
      }

      #${CFG.iframeId} {
        width: 100%;
        height: 100%;
        border: none;
      }

      .dnt-iframe-open-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }

      .dnt-iframe-open-btn .dnt-iframe-env-pill {
        font-size: 10px;
        text-transform: uppercase;
        padding: 1px 6px;
        border-radius: 999px;
        background: #e5e7eb;
        color: #374151;
      }
    `;
    document.head.appendChild(style);
    log("CSS injected");
  }

  function make_draggable(panel, handle) {
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let startLeft = 0;
    let startTop = 0;

    handle.addEventListener("mousedown", (evt) => {
      if (evt.button !== 0) return;
      // не даём drag-ить, если в максимальном режиме
      if (panel.classList.contains("dnt-max")) return;

      isDragging = true;
      const rect = panel.getBoundingClientRect();
      startX = evt.clientX;
      startY = evt.clientY;
      startLeft = rect.left;
      startTop = rect.top;
      document.body.classList.add("dnt-iframe-dragging");
      evt.preventDefault();
    });

    document.addEventListener("mousemove", (evt) => {
      if (!isDragging) return;
      const dx = evt.clientX - startX;
      const dy = evt.clientY - startY;

      let newLeft = startLeft + dx;
      let newTop = startTop + dy;

      const maxLeft = window.innerWidth - 120;
      const maxTop = window.innerHeight - 80;

      if (newLeft < 12) newLeft = 12;
      if (newTop < 12) newTop = 12;
      if (newLeft > maxLeft) newLeft = maxLeft;
      if (newTop > maxTop) newTop = maxTop;

      panel.style.left = newLeft + "px";
      panel.style.top = newTop + "px";
      panel.style.right = "auto";
      panel.style.bottom = "auto";
    });

    document.addEventListener("mouseup", () => {
      if (!isDragging) return;
      isDragging = false;
      document.body.classList.remove("dnt-iframe-dragging");
    });
  }

  function toggle_panel_size(panel, toggleBtn) {
    const isMax = panel.classList.contains("dnt-max");

    if (!isMax) {
      const rect = panel.getBoundingClientRect();
      panel.dataset.prevLeft = String(rect.left);
      panel.dataset.prevTop = String(rect.top);
      panel.dataset.prevWidth = String(rect.width);
      panel.dataset.prevHeight = String(rect.height);

      panel.classList.add("dnt-max");
      panel.style.left = "16px";
      panel.style.top = "16px";
      panel.style.right = "16px";
      panel.style.bottom = "16px";
      panel.style.width = "auto";
      panel.style.height = "auto";

      if (toggleBtn) toggleBtn.textContent = "⤡";
      log("panel maximized");
    } else {
      const left = parseFloat(panel.dataset.prevLeft || "0");
      const top = parseFloat(panel.dataset.prevTop || "0");
      const width = parseFloat(panel.dataset.prevWidth || String(CFG.defaultWidth));
      const height = parseFloat(panel.dataset.prevHeight || String(CFG.defaultHeight));

      panel.classList.remove("dnt-max");
      panel.style.right = "24px";
      panel.style.bottom = "24px";
      panel.style.width = width + "px";
      panel.style.height = height + "px";

      if (left && top) {
        panel.style.left = left + "px";
        panel.style.top = top + "px";
      } else {
        panel.style.left = "";
        panel.style.top = "";
      }

      if (toggleBtn) toggleBtn.textContent = "⤢";
      log("panel restored");
    }
  }

  function ensure_panel() {
    let panel = document.getElementById(CFG.panelId);
    if (panel) return panel;

    ensure_styles();

    panel = document.createElement("div");
    panel.id = CFG.panelId;

    const header = document.createElement("div");
    header.className = "dnt-panel-header";

    const titleWrap = document.createElement("div");
    titleWrap.className = "dnt-panel-title";

    const titleSpan = document.createElement("span");
    titleSpan.textContent = "External Portal";

    const envTag = document.createElement("span");
    envTag.id = CFG.envTagId;
    envTag.textContent = get_env();

    titleWrap.appendChild(titleSpan);
    titleWrap.appendChild(envTag);

    const actions = document.createElement("div");
    actions.className = "dnt-panel-actions";

    const toggleBtn = document.createElement("button");
    toggleBtn.className = "dnt-panel-btn";
    toggleBtn.type = "button";
    toggleBtn.textContent = "⤢";
    toggleBtn.title = "Toggle size";

    toggleBtn.addEventListener("click", () => {
      toggle_panel_size(panel, toggleBtn);
    });

    const closeBtn = document.createElement("button");
    closeBtn.className = "dnt-panel-btn";
    closeBtn.type = "button";
    closeBtn.innerHTML = "&times;";
    closeBtn.title = "Close";

    closeBtn.addEventListener("click", () => {
      panel.classList.remove("dnt-visible");
    });

    actions.appendChild(toggleBtn);
    actions.appendChild(closeBtn);

    header.appendChild(titleWrap);
    header.appendChild(actions);

    const body = document.createElement("div");
    body.className = "dnt-panel-body";

    const iframe = document.createElement("iframe");
    iframe.id = CFG.iframeId;
    iframe.setAttribute(
      "sandbox",
      "allow-same-origin allow-scripts allow-forms allow-popups"
    );

    body.appendChild(iframe);

    panel.appendChild(header);
    panel.appendChild(body);
    document.body.appendChild(panel);

    make_draggable(panel, header);

    log("panel created");
    return panel;
  }

  function open_panel(url, title) {
    const panel = ensure_panel();
    const iframe = document.getElementById(CFG.iframeId);
    const envTag = document.getElementById(CFG.envTagId);

    if (envTag) envTag.textContent = get_env();

    const headerTitle = panel.querySelector(".dnt-panel-title span");
    if (headerTitle && title) {
      headerTitle.textContent = title;
    }

    if (iframe && url) {
      const last = iframe.dataset.dntLastUrl || "";
      if (last !== url) {
        log("open_panel set src:", url);
        iframe.src = url;
        iframe.dataset.dntLastUrl = url;
      } else {
        log("open_panel reuse existing iframe session");
      }
    } else {
      warn("open_panel called without url", { url });
    }

    if (!panel.style.left && !panel.style.top && !panel.classList.contains("dnt-max")) {
      panel.style.right = "24px";
      panel.style.bottom = "24px";
    }

    panel.classList.add("dnt-visible");
  }

  function parse_iframe_options(optionsStr) {
    if (!optionsStr) return null;

    const lines = String(optionsStr).split(/\r?\n/);
    let seenMarker = false;
    const cfg = {};

    for (let raw of lines) {
      const line = raw.trim();
      if (!line) continue;

      if (!seenMarker) {
        if (line !== CFG.marker) {
          log("options: first non-empty line is not marker", {
            line,
            expected: CFG.marker,
          });
          return null;
        }
        seenMarker = true;
        continue;
      }

      if (line.startsWith("#") || line.startsWith("//")) continue;

      const eqIndex = line.indexOf("=");
      if (eqIndex === -1) continue;

      const key = line.slice(0, eqIndex).trim().toUpperCase();
      const value = line.slice(eqIndex + 1).trim();

      if (!key) continue;
      cfg[key] = value;
    }

    if (!seenMarker) {
      log("options: marker not seen");
      return null;
    }

    log("parsed iframe cfg:", cfg);
    return cfg;
  }

  function resolve_url_from_cfg(cfg) {
    const env = get_env();
    const envKey = env.toUpperCase();

    let url =
      cfg[envKey] ||
      cfg.DEFAULT ||
      cfg.DEV ||
      cfg.PRODUCTION ||
      cfg.URL ||
      null;

    if (!url) {
      warn("no URL resolved from cfg for env", env, cfg);
      return null;
    }

    return url;
  }

  function process_field(frm, df) {
    const field = frm.get_field(df.fieldname);
    if (!field || !field.$wrapper) {
      warn("process_field: no field wrapper", {
        doctype: frm.doctype,
        name: frm.doc && frm.doc.name,
        fieldname: df.fieldname,
      });
      return;
    }

    const cfg = parse_iframe_options(df.options || "");
    if (!cfg) return;

    const wrapper = field.$wrapper;

    // Уже есть кнопка — только обновим бейдж env
    if (wrapper.find(".dnt-iframe-open-btn").length) {
      const env = get_env();
      wrapper.find(".dnt-iframe-env-pill").text(env);
      log("button already exists, env pill updated", {
        doctype: frm.doctype,
        name: frm.doc && frm.doc.name,
        fieldname: df.fieldname,
        env,
      });
      return;
    }

    // Прячем оригинальный инпут целиком
    const controlInputWrapper = wrapper.find(".control-input-wrapper");
    controlInputWrapper.hide();

    // Создаём аккуратный контейнер под кнопку
    let btnWrapper = wrapper.find(".dnt-iframe-btn-wrapper");
    if (!btnWrapper.length) {
      btnWrapper = $('<div class="dnt-iframe-btn-wrapper"></div>');
      wrapper.append(btnWrapper);
    }

    const title = cfg.TITLE || df.label || "Open IFrame";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-xs btn-secondary dnt-iframe-open-btn";

    const safeTitle =
      frappe.utils && frappe.utils.escape_html
        ? frappe.utils.escape_html(title)
        : title;

    btn.innerHTML = `
      <span>${safeTitle}</span>
      <span class="dnt-iframe-env-pill">${get_env()}</span>
    `;

    btn.addEventListener("click", () => {
      try {
        const url = resolve_url_from_cfg(cfg);
        if (!url) {
          const env = get_env();
          frappe.msgprint({
            message: __(
              "No URL configured for current environment ({0}).",
              [env]
            ),
            indicator: "red",
            title: __("IFrame Error"),
          });
          return;
        }
        open_panel(url, title);
      } catch (e) {
        err("error on button click", e);
        frappe.msgprint({
          message: __("Error while opening IFrame."),
          indicator: "red",
          title: __("IFrame Error"),
        });
      }
    });

    btnWrapper.get(0).appendChild(btn);

    log("button created", {
      doctype: frm.doctype,
      name: frm.doc && frm.doc.name,
      fieldname: df.fieldname,
      title,
    });
  }

  function process_form(frm) {
    if (!frm || !frm.meta || !Array.isArray(frm.meta.fields)) {
      warn("process_form: invalid frm", frm);
      return;
    }

    log(
      "process_form",
      frm.doctype,
      frm.doc && frm.doc.name,
      "fields",
      frm.meta.fields.length
    );

    let any = false;

    (frm.meta.fields || []).forEach((df) => {
      if (!df || !df.options) return;

      if (!String(df.options).includes(CFG.marker)) return;

      any = true;
      log("candidate field with marker", {
        doctype: frm.doctype,
        name: frm.doc && frm.doc.name,
        fieldname: df.fieldname,
        label: df.label,
      });

      try {
        process_field(frm, df);
      } catch (e) {
        err("error in process_field", df.fieldname, e);
      }
    });

    if (!any) {
      log("no fields with marker found on form", {
        doctype: frm.doctype,
        name: frm.doc && frm.doc.name,
      });
    }
  }

  function patch_form_class_once() {
    if (!frappe || !frappe.ui || !frappe.ui.form || !frappe.ui.form.Form) {
      return false;
    }

    const Form = frappe.ui.form.Form;

    if (Form.prototype.__dnt_iframe_patched) {
      return true;
    }
    Form.prototype.__dnt_iframe_patched = true;

    const origRefresh = Form.prototype.refresh;
    const origOnload = Form.prototype.onload;

    Form.prototype.refresh = function (...args) {
      const res = origRefresh ? origRefresh.apply(this, args) : undefined;
      try {
        process_form(this);
      } catch (e) {
        err("error in patched refresh", e);
      }
      return res;
    };

    Form.prototype.onload = function (...args) {
      const res = origOnload ? origOnload.apply(this, args) : undefined;
      try {
        process_form(this);
      } catch (e) {
        err("error in patched onload", e);
      }
      return res;
    };

    log("Form.prototype patched for refresh/onload");
    return true;
  }

  if (!patch_form_class_once()) {
    let attempts = 0;
    const maxAttempts = 20;
    const timer = setInterval(() => {
      attempts += 1;
      if (patch_form_class_once() || attempts >= maxAttempts) {
        clearInterval(timer);
        if (attempts >= maxAttempts) {
          warn("failed to patch Form.prototype, max attempts reached");
        }
      } else {
        log("waiting for Form class, attempt", attempts);
      }
    }, 300);
  }
})();