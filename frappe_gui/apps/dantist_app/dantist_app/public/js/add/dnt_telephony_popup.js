// === DNT Telephony Call Popup — v1.4 (debug, socket.io) ===
// Плавающий виджет звонка для Desk (Frappe v15).

(function () {
  if (window.__DNT_TELEPHONY_POPUP) {
    try {
      console.log("[DNT-CALL] already initialized");
    } catch (e) {}
    return;
  }
  window.__DNT_TELEPHONY_POPUP = true;

  try {
    console.log(
      "[DNT-CALL] bootstrap",
      "frappe=",
      !!window.frappe,
      "realtime=",
      !!(window.frappe && frappe.realtime)
    );
  } catch (e) {}

  const CFG = {
    event_name: "dnt_telephony_call",
    css_id: "dnt-telephony-popup-css",
    root_id: "dnt-telephony-popup",
    log_prefix: "[DNT-CALL]",
    debug: true || localStorage.getItem("dnt.telephony.debug") === "1",
    finished_statuses: new Set(["missed", "failed", "voicemail"]),
  };

  function log() {
    if (!CFG.debug) return;
    try {
      console.log(CFG.log_prefix, ...arguments);
    } catch (e) {}
  }

  function t(msg) {
    try {
      return __(msg);
    } catch (e) {
      return msg;
    }
  }

  // ===== CSS =====

  (function inject_css() {
    if (document.getElementById(CFG.css_id)) return;
    const s = document.createElement("style");
    s.id = CFG.css_id;
    s.textContent = `
      .dnt-call-popup {
        position: fixed;
        right: 18px;
        bottom: 18px;
        z-index: 1040;
        max-width: 360px;
        width: 100%;
        background: rgba(15, 23, 42, 0.92);
        color: #f9fafb;
        border-radius: 18px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.55);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        overflow: hidden;
        transform: translateY(20px);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.18s ease-out, transform 0.18s ease-out;
        font-size: 13px;
      }

      .dnt-call-popup.dnt-call-visible {
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
      }

      .dnt-call-popup-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px 4px 12px;
      }

      .dnt-call-label {
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        font-size: 11px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }

      .dnt-call-status-pill {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 10px;
        background: rgba(34,197,94,0.18);
        color: #bbf7d0;
      }

      .dnt-call-status-pill--ringing {
        background: rgba(250,204,21,0.18);
        color: #fef9c3;
      }

      .dnt-call-status-pill-dot {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        margin-right: 4px;
        background: currentColor;
      }

      .dnt-call-timer {
        font-variant-numeric: tabular-nums;
        font-size: 12px;
        opacity: 0.85;
        margin-right: 6px;
      }

      .dnt-call-close {
        border: none;
        background: none;
        color: inherit;
        padding: 2px;
        margin: 0;
        width: 22px;
        height: 22px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        opacity: 0.6;
      }
      .dnt-call-close:hover {
        background: rgba(148, 163, 184, 0.18);
        opacity: 1;
      }

      .dnt-call-popup-body {
        display: flex;
        align-items: center;
        padding: 8px 12px 6px 12px;
        gap: 10px;
      }

      .dnt-call-avatar {
        flex: 0 0 auto;
        width: 42px;
        height: 42px;
        border-radius: 14px;
        background: linear-gradient(135deg, #38bdf8, #6366f1);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 18px;
        color: white;
        text-transform: uppercase;
      }

      .dnt-call-main {
        flex: 1 1 auto;
        min-width: 0;
      }

      .dnt-call-name {
        font-weight: 600;
        font-size: 13px;
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
      }

      .dnt-call-phone {
        font-size: 12px;
        opacity: 0.85;
        margin-top: 2px;
      }

      .dnt-call-meta {
        font-size: 11px;
        opacity: 0.7;
        margin-top: 4px;
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
      }

      .dnt-call-popup-footer {
        padding: 8px 12px 10px 12px;
        display: flex;
        justify-content: flex-end;
        gap: 8px;
      }

      .dnt-call-popup-footer .btn {
        font-size: 11px;
        padding-inline: 10px;
        border-radius: 999px;
      }

      @media (max-width: 767px) {
        .dnt-call-popup {
          left: 10px;
          right: 10px;
          bottom: 10px;
        }
      }
    `;
    document.head.appendChild(s);
    log("CSS injected");
  })();

  // ===== DOM / состояние =====

  const state = {
    call_id: null,
    status: null,
    ticket: null,
    dismissed: false,
    timer_id: null,
    started_at_ms: null,
  };

  function ensure_root() {
    let root = document.getElementById(CFG.root_id);
    if (root) return root;

    log("ensure_root(): create DOM root");

    const esc = (txt) => {
      try {
        return frappe.utils.escape_html(txt);
      } catch (e) {
        return txt;
      }
    };

    root = document.createElement("div");
    root.id = CFG.root_id;
    root.className = "dnt-call-popup";

    root.innerHTML = `
      <div class="dnt-call-popup-header">
        <div class="dnt-call-label">
          <span>${esc(t("Call"))}</span>
          <span class="dnt-call-status-pill">
            <span class="dnt-call-status-pill-dot"></span>
            <span class="dnt-call-status-text">${esc(t("Ringing"))}</span>
          </span>
        </div>
        <div class="dnt-call-header-right">
          <span class="dnt-call-timer">00:00</span>
          <button type="button" class="dnt-call-close" aria-label="${esc(t("Dismiss"))}">
            ×
          </button>
        </div>
      </div>
      <div class="dnt-call-popup-body">
        <div class="dnt-call-avatar">?</div>
        <div class="dnt-call-main">
          <div class="dnt-call-name">—</div>
          <div class="dnt-call-phone">—</div>
          <div class="dnt-call-meta"></div>
        </div>
      </div>
      <div class="dnt-call-popup-footer">
        <button type="button" class="btn btn-default btn-xs dnt-call-dismiss">
          ${esc(t("Dismiss"))}
        </button>
        <button type="button" class="btn btn-primary btn-xs dnt-call-open">
          ${esc(t("Open case"))}
        </button>
      </div>
    `;
    document.body.appendChild(root);

    const btnClose = root.querySelector(".dnt-call-close");
    const btnDismiss = root.querySelector(".dnt-call-dismiss");
    const btnOpen = root.querySelector(".dnt-call-open");

    const hide = () => hide_popup(true);

    btnClose.addEventListener("click", hide);
    btnDismiss.addEventListener("click", hide);

    btnOpen.addEventListener("click", () => {
      log("open clicked", "ticket=", state.ticket, "call_id=", state.call_id);
      if (state.ticket) {
        try {
          frappe.set_route("Form", "Engagement Case", state.ticket);
        } catch (e) {
          log("route to case failed", e);
        }
      } else if (state.call_id) {
        try {
          frappe.set_route("Form", "Call", state.call_id);
        } catch (e) {
          log("route to call failed", e);
        }
      }
      hide_popup(true);
    });

    return root;
  }

  function set_timer(start_ms) {
    clear_timer();

    state.started_at_ms = start_ms;

    const root = document.getElementById(CFG.root_id);
    if (!root) return;
    const el = root.querySelector(".dnt-call-timer");
    if (!el) return;

    const update = () => {
      if (!state.started_at_ms) return;
      const now = Date.now();
      const diff = Math.max(0, Math.floor((now - state.started_at_ms) / 1000));
      const mm = String(Math.floor(diff / 60)).padStart(2, "0");
      const ss = String(diff % 60).padStart(2, "0");
      el.textContent = `${mm}:${ss}`;
    };

    update();
    state.timer_id = setInterval(update, 1000);
  }

  function clear_timer() {
    if (state.timer_id) {
      clearInterval(state.timer_id);
      state.timer_id = null;
    }
  }

  function hide_popup(mark_dismissed) {
    log("hide_popup", "mark_dismissed=", mark_dismissed);
    const root = document.getElementById(CFG.root_id);
    clear_timer();
    if (mark_dismissed) state.dismissed = true;
    if (root) {
      root.classList.remove("dnt-call-visible");
    }
  }

  function show_popup(data) {
    log("show_popup()", data);
    const root = ensure_root();
    const nameEl = root.querySelector(".dnt-call-name");
    const phoneEl = root.querySelector(".dnt-call-phone");
    const metaEl = root.querySelector(".dnt-call-meta");
    const avatarEl = root.querySelector(".dnt-call-avatar");
    const statusPill = root.querySelector(".dnt-call-status-pill");
    const statusText = root.querySelector(".dnt-call-status-text");

    const rawStatus = (data.status || "").toString();
    const rawEvent = (data.event || "").toString();

    const status = rawStatus.toLowerCase().trim();
    const eventType = rawEvent.toUpperCase().trim();
    const direction = (data.direction || "").toLowerCase().trim();

    log("parsed status/event", { rawStatus, rawEvent, status, eventType });

    const isRinging = status === "ringing";
    const isAnswered = status === "answered";

    const label =
      direction === "in"
        ? isRinging
          ? t("Incoming call")
          : t("Active call")
        : isRinging
        ? t("Outgoing call")
        : t("Active call");

    const statusLabel = isRinging
      ? t("Ringing")
      : isAnswered
      ? t("In progress")
      : rawStatus || t("In progress");

    const displayName =
      data.ticket_display_name ||
      data.ticket_title ||
      (data.phone_for_case || data.from_number || data.to_number || t("Unknown"));

    const phone =
      data.phone_for_case ||
      data.from_number ||
      data.to_number ||
      data.did ||
      "";

    const metaParts = [];
    if (data.queue) metaParts.push(t("Queue") + ": " + data.queue);
    if (data.agent_extension)
      metaParts.push(t("Extension") + ": " + data.agent_extension);
    if (data.ivr_language)
      metaParts.push(t("Language") + ": " + data.ivr_language);

    const meta = metaParts.join(" • ");

    const firstChar =
      (displayName || "").trim().charAt(0) ||
      (phone || "").replace(/[^0-9A-Za-z]/g, "").charAt(0) ||
      "?";

    const labelEl = root.querySelector(".dnt-call-label span:first-child");
    if (labelEl) labelEl.textContent = label;

    if (statusText) statusText.textContent = statusLabel;

    if (statusPill) {
      statusPill.classList.remove("dnt-call-status-pill--ringing");
      if (isRinging) statusPill.classList.add("dnt-call-status-pill--ringing");
    }

    if (nameEl) nameEl.textContent = displayName;
    if (phoneEl) phoneEl.textContent = phone || "—";
    if (metaEl) metaEl.textContent = meta;
    if (avatarEl) avatarEl.textContent = firstChar.toUpperCase();

    const start_ts = data.start_ts || data.event_ts || null;
    let startMs = Date.now();
    if (start_ts) {
      const normalized = start_ts.replace(" ", "T");
      const parsed = Date.parse(normalized);
      if (!Number.isNaN(parsed)) {
        startMs = parsed;
      }
    }
    set_timer(startMs);

    root.classList.add("dnt-call-visible");
  }

  // ===== Обработка realtime-событий =====

  function handle_event(data) {
    try {
      log("handle_event()", data);

      if (!data) return;

      if (!data.call_id && !data.call_name) {
        log("no call_id in event, test / skip for popup");
        return;
      }

      const callId = data.call_id || data.call_name;
      const rawStatus = (data.status || "").toString();
      const rawEvent = (data.event || "").toString();

      const status = rawStatus.toLowerCase().trim();
      const eventType = rawEvent.toUpperCase().trim();

      log("event parsed", { callId, status, eventType });

      if (
        CFG.finished_statuses.has(status) ||
        eventType === "CALL_HANGUP" ||
        eventType === "CALL_MISSED" ||
        eventType === "VOICEMAIL_LEFT"
      ) {
        log("final event, hide if same call");
        if (state.call_id && state.call_id === callId) {
          hide_popup(false);
        }
        return;
      }

      if (state.dismissed && state.call_id === callId) {
        log("call dismissed by user, skip");
        return;
      }

      state.call_id = callId;
      state.status = status;
      state.ticket = data.ticket || null;
      state.dismissed = false;

      show_popup(data);
    } catch (e) {
      log("handle_event error", e);
    }
  }

  function ready() {
    try {
      const hasFrappe = !!window.frappe;
      const hasRealtime = !!(hasFrappe && frappe.realtime);
      const hasSocket =
        !!(window.frappe && frappe.socketio && frappe.socketio.socket);
      log("ready()? frappe=", hasFrappe, "realtime=", hasRealtime, "socket=", hasSocket);
      return hasRealtime || hasSocket;
    } catch (e) {
      log("ready() error", e);
      return false;
    }
  }

  // ===== УСТОЙЧИВАЯ ПОДПИСКА: frappe.realtime И НАПРЯМУЮ НА SOCKET =====

  let lastRealtime = null;
  let socketBound = false;

  function ensure_subscription() {
    try {
      if (!ready()) return;

      // 1) через frappe.realtime (если живой)
      if (window.frappe && frappe.realtime && frappe.realtime.on) {
        const rt = frappe.realtime;
        if (rt !== lastRealtime) {
          lastRealtime = rt;
          try {
            rt.on(CFG.event_name, handle_event);
            log("ensure_subscription(): subscribed via frappe.realtime to", CFG.event_name, "on", rt);
          } catch (e) {
            log("ensure_subscription frappe.realtime error", e);
          }
        }
      }

      // 2) напрямую через socket.io (если есть)
      if (
        window.frappe &&
        frappe.socketio &&
        frappe.socketio.socket &&
        !socketBound
      ) {
        try {
          frappe.socketio.socket.on(CFG.event_name, handle_event);
          socketBound = true;
          log("ensure_subscription(): subscribed via socket.io to", CFG.event_name);
        } catch (e) {
          log("ensure_subscription socket error", e);
        }
      }
    } catch (e) {
      log("ensure_subscription error", e);
    }
  }

  // Стартуем и периодически проверяем (на случай, если socket/realtime появятся позже)
  ensure_subscription();
  setInterval(ensure_subscription, 1000);
})();