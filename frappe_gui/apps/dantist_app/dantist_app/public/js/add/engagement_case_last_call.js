// ==============================
// Engagement Case — Last Call UI — v1.1
// Использует секцию "Telephony" (telephony_section), вместо грид-таблицы Calls.
// Показывается только для channel_type="Call" & channel_platform="Telephony".
// Последний звонок определяется по времени (end_ts > start_ts > creation).
// ==============================
(function () {
  const DOCTYPE = "Engagement Case";
  const V = "v1.1";

  function log(tag, ...args) { try { console.log(`📞 EC-CALL[${V}] ${tag}`, ...args); } catch (_) {} }
  function warn(tag, ...args) { try { console.warn(`📞 EC-CALL[${V}] ${tag}`, ...args); } catch (_) {} }
  function err(tag, ...args) { try { console.error(`📞 EC-CALL[${V}] ${tag}`, ...args); } catch (_) {} }

  // ===== Условия видимости =====
  function shouldShowLastCall(doc) {
    if (!doc) return false;
    if (doc.channel_type !== "Call") return false;
    if (doc.channel_platform !== "Telephony") return false;
    return true;
  }

  // ===== utils =====
  function fmtDt(dtStr) {
    if (!dtStr) return "";
    try {
      return moment(dtStr).format("YYYY-MM-DD HH:mm");
    } catch (e) {
      return String(dtStr);
    }
  }

  function fmtDurationSeconds(sec) {
    const n = parseInt(sec, 10);
    if (!Number.isFinite(n) || n <= 0) return "";
    const mm = String(Math.floor(n / 60)).padStart(2, "0");
    const ss = String(n % 60).padStart(2, "0");
    return `${mm}:${ss}`;
  }

  function statusLabel(status) {
    const s = (status || "").toString().toLowerCase().trim();
    if (!s) return __("Unknown");
    if (s === "ringing") return __("Ringing");
    if (s === "answered") return __("Answered");
    if (s === "missed") return __("Missed");
    if (s === "failed") return __("Failed");
    if (s === "voicemail") return __("Voicemail");
    return __(status);
  }

  function directionLabel(direction) {
    const d = (direction || "").toString().toLowerCase().trim();
    if (d === "in") return __("Incoming call");
    if (d === "out") return __("Outgoing call");
    return __("Call");
  }

  function directionChip(direction) {
    const d = (direction || "").toString().toLowerCase().trim();
    if (d === "in") return __("Incoming");
    if (d === "out") return __("Outgoing");
    return __("Unknown");
  }

  function statusClass(status) {
    const s = (status || "").toString().toLowerCase().trim();
    if (s === "answered") return "-ok";
    if (s === "ringing") return "-ringing";
    if (s === "missed" || s === "failed") return "-bad";
    if (s === "voicemail") return "-vm";
    return "-neutral";
  }

  function parseTs(ts) {
    if (!ts) return 0;
    try {
      const normalized = String(ts).replace(" ", "T");
      const val = Date.parse(normalized);
      return Number.isNaN(val) ? 0 : val;
    } catch (e) {
      return 0;
    }
  }

  function pickLastCallByTime(list) {
    let best = null;
    let bestTs = -1;

    (list || []).forEach((c) => {
      const t =
        parseTs(c.end_ts) ||
        parseTs(c.start_ts) ||
        parseTs(c.creation);
      if (t >= bestTs) {
        bestTs = t;
        best = c;
      }
    });

    return best;
  }

  // ===== работа с Telephony-секцией =====
  function getTelephonySection(frm) {
    try {
      const fld =
        (frm.get_field && frm.get_field("telephony_section")) ||
        (frm.fields_dict && frm.fields_dict.telephony_section);
      if (!fld) return null;

      const w = fld.wrapper || fld.$wrapper;
      const el = w && (w[0] || w);
      if (!el) return null;

      const sec =
        el.closest(".form-section.card-section") ||
        el.closest(".form-section");
      return sec || null;
    } catch (e) {
      warn("getTelephonySection error", e);
      return null;
    }
  }

  function getCallsGridWrapper(frm) {
    try {
      const fld = frm.fields_dict && frm.fields_dict.calls;
      if (!fld || !fld.grid || !fld.grid.wrapper) return null;
      const w = fld.grid.wrapper;
      return w[0] || w;
    } catch (e) {
      return null;
    }
  }

  function ensureLastCallContainer(frm) {
    const sec = getTelephonySection(frm);
    if (!sec) return null;

    const body =
      sec.querySelector(".section-body") ||
      sec.querySelector(".form-section-body") ||
      sec;
    if (!body) return null;

    // Прячем оригинальный грид calls
    const grid = getCallsGridWrapper(frm);
    if (grid) {
      grid.style.display = "none";
    }

    let box = body.querySelector(".ec-last-call-body");
    if (!box) {
      box = document.createElement("div");
      box.className = "ec-last-call-body";
      body.appendChild(box);
    }
    return { section: sec, container: box };
  }

  function hideTelephonySection(frm) {
    const sec = getTelephonySection(frm);
    const grid = getCallsGridWrapper(frm);
    if (sec) sec.classList.add("hide");
    // если вдруг грид скрывали — вернём
    if (grid) grid.style.display = "";
  }

  function showTelephonySection(frm) {
    const sec = getTelephonySection(frm);
    if (sec) sec.classList.remove("hide");
  }

  // ===== рендер =====
  function renderEmpty(container) {
    container.innerHTML = `
      <div class="text-muted small ec-last-call-empty">
        ${frappe.utils.escape_html(__("No calls for this case yet."))}
      </div>
    `;
  }

  function renderCall(container, doc, call) {
    if (!call) {
      renderEmpty(container);
      return;
    }

    const esc = frappe.utils.escape_html;

    const status = call.status || "";
    const direction = call.direction || "";
    const statusCls = statusClass(status);

    const label = directionLabel(direction);
    const statusLbl = statusLabel(status);
    const dirChip = directionChip(direction);

    const fromNumber = call.from_number || call.caller || "";
    const toNumber =
      call.to_number ||
      call.did ||
      call.callee ||
      "";

    const start = fmtDt(call.start_ts || call.creation || "");
    const answer = fmtDt(call.answer_ts || "");
    const end = fmtDt(call.end_ts || "");
    const durVal = fmtDurationSeconds(call.billsec);
    const durLabel = durVal || __("Unknown");

    const queue = call.queue || "";
    const lang = call.ivr_language || "";
    const ext = call.agent_extension || "";

    const recording = call.recording_url || "";

    const metaChips = [];

    if (dirChip) {
      metaChips.push(
        `<span class="chip -ghost">${esc(dirChip)}</span>`
      );
    }
    if (queue) {
      metaChips.push(
        `<span class="chip -ghost">${esc(__("Queue"))}: ${esc(queue)}</span>`
      );
    }
    if (ext) {
      metaChips.push(
        `<span class="chip -ghost">${esc(__("Ext"))}: ${esc(ext)}</span>`
      );
    }
    if (lang) {
      metaChips.push(
        `<span class="chip -ghost">${esc(__("Lang"))}: ${esc(lang)}</span>`
      );
    }
    if (start) {
      metaChips.push(
        `<span class="chip -ghost" title="${esc(__("Start"))}">⏱ ${esc(start)}</span>`
      );
    }
    if (answer) {
      metaChips.push(
        `<span class="chip -ghost" title="${esc(__("Answered at"))}">✅ ${esc(answer)}</span>`
      );
    }
    if (end) {
      metaChips.push(
        `<span class="chip -ghost" title="${esc(__("Ended at"))}">⏹ ${esc(end)}</span>`
      );
    }

    // Длительность всегда показываем: либо MM:SS, либо "Unknown"
    metaChips.push(
      `<span class="chip -ghost -dur" title="${esc(__("Duration"))}">⏳ ${esc(durLabel)}</span>`
    );

    container.innerHTML = `
      <div class="ec-last-call-card ec-call-${esc(statusCls)}">
        <div class="ec-last-call-header">
          <div class="left">
            <div class="label-row">
              <span class="pill pill-main">${esc(label)}</span>
              <span class="pill pill-status ${esc(statusCls)}">${esc(statusLbl)}</span>
            </div>
            <div class="number-main">
              ${esc(
                doc.display_name ||
                  doc.title ||
                  doc.phone ||
                  (fromNumber || toNumber || __("Call"))
              )}
            </div>
          </div>
          <div class="right">
            <button type="button"
                    class="btn btn-xs btn-default"
                    data-act="open-call">
              ${esc(__("Open Call"))}
            </button>
          </div>
        </div>

        <div class="ec-last-call-body-main">
          <div class="numbers-row">
            <div class="num-block">
              <div class="num-label">${esc(__("From"))}</div>
              <div class="num-value">${esc(fromNumber || __("Unknown"))}</div>
            </div>
            <div class="num-arrow">→</div>
            <div class="num-block">
              <div class="num-label">${esc(__("To / DID"))}</div>
              <div class="num-value">${esc(toNumber || __("Unknown"))}</div>
            </div>
          </div>

          <div class="meta-row">
            ${metaChips.join(" ")}
          </div>

          ${
            recording
              ? `<div class="record-row">
                   <span class="text-muted small mr-2">${esc(__("Recording"))}:</span>
                   <a href="${esc(recording)}" target="_blank" rel="noopener noreferrer">
                     ${esc(__("Open recording"))}
                   </a>
                 </div>`
              : ""
          }
        </div>

        <div class="ec-last-call-footer">
          <button type="button"
                  class="btn btn-xs btn-default"
                  data-act="all-calls">
            ${esc(__("All calls for this case"))}
          </button>
        </div>
      </div>
    `;

    // биндим кнопки
    const btnOpenCall = container.querySelector('[data-act="open-call"]');
    const btnAll = container.querySelector('[data-act="all-calls"]');

    if (btnOpenCall) {
      btnOpenCall.addEventListener("click", () => {
        try {
          frappe.set_route("Form", "Call", call.name);
        } catch (e) {
          warn("route to Call failed", e);
        }
      });
    }

    if (btnAll) {
      btnAll.addEventListener("click", () => {
        try {
          frappe.set_route("List", "Call", { ticket: doc.name });
        } catch (e) {
          warn("route to Call list failed", e);
        }
      });
    }
  }

  // ===== загрузка данных (по времени звонка) =====
  async function loadLastCall(frm) {
    const ctl = ensureLastCallContainer(frm);
    if (!ctl) return;
    const { section, container } = ctl;
    const doc = frm.doc;

    if (!shouldShowLastCall(doc)) {
      hideTelephonySection(frm);
      return;
    }

    showTelephonySection(frm);

    const calls = Array.isArray(doc.calls) ? doc.calls : [];
    if (!calls.length) {
      log("no calls in child table");
      renderEmpty(container);
      return;
    }

    const names = calls
      .map((r) => r.call)
      .filter((x) => !!x);

    if (!names.length) {
      log("child rows without call names");
      renderEmpty(container);
      return;
    }

    container.innerHTML = `
      <div class="text-muted small">
        ${frappe.utils.escape_html(__("Loading last call…"))}
      </div>
    `;

    try {
      log("fetch Call list", { names });
      const { message } = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "Call",
          filters: [["name", "in", names]],
          fields: [
            "name",
            "status",
            "direction",
            "from_number",
            "to_number",
            "did",
            "queue",
            "ivr_language",
            "agent_extension",
            "start_ts",
            "answer_ts",
            "end_ts",
            "billsec",
            "recording_url",
            "creation",
          ],
          limit_page_length: names.length,
        },
      });

      const rows = message || [];
      log("Call list loaded", rows);

      const last = pickLastCallByTime(rows);
      renderCall(container, doc, last);
    } catch (e) {
      err("loadLastCall failed", e);
      container.innerHTML = `
        <div class="text-danger small">
          ${frappe.utils.escape_html(__("Failed to load last call."))}
        </div>
      `;
    }
  }

  // ===== бинды формы =====
  frappe.ui.form.on(DOCTYPE, {
    refresh(frm) {
      if (!shouldShowLastCall(frm.doc)) {
        hideTelephonySection(frm);
        return;
      }
      showTelephonySection(frm);
      loadLastCall(frm);
    },
    after_save(frm) {
      if (!shouldShowLastCall(frm.doc)) {
        hideTelephonySection(frm);
        return;
      }
      showTelephonySection(frm);
      loadLastCall(frm);
    },
  });

  // ===== стили =====
  const css = document.createElement("style");
  css.textContent = `
    .ec-last-call-body {
      margin-top: 6px;
    }

    .ec-last-call-card {
      border-radius: 16px;
      padding: 10px 12px 10px;
      background: radial-gradient(circle at top left, rgba(59,130,246,0.12), transparent 55%),
                  radial-gradient(circle at bottom right, rgba(16,185,129,0.16), transparent 55%),
                  var(--control-bg,#f8fafc);
      box-shadow: 0 10px 28px rgba(15,23,42,0.16);
      border: 1px solid rgba(148,163,184,0.35);
      font-size: 13px;
    }

    .ec-last-call-header {
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:10px;
      margin-bottom:6px;
    }
    .ec-last-call-header .left {
      min-width:0;
      flex:1 1 auto;
    }
    .ec-last-call-header .right {
      flex:0 0 auto;
    }

    .ec-last-call-header .label-row {
      display:flex;
      align-items:center;
      gap:6px;
      margin-bottom:3px;
    }

    .ec-last-call-header .number-main {
      font-weight:600;
      font-size:14px;
      white-space:nowrap;
      text-overflow:ellipsis;
      overflow:hidden;
    }

    .pill {
      display:inline-flex;
      align-items:center;
      padding:2px 8px;
      border-radius:999px;
      border:1px solid rgba(148,163,184,0.6);
      font-size:10px;
      text-transform:uppercase;
      letter-spacing:.03em;
      background: rgba(255,255,255,0.8);
    }
    .pill-main {
      background: rgba(59,130,246,0.1);
      border-color: rgba(59,130,246,0.5);
      color: #1d4ed8;
    }
    .pill-status.-ok {
      background: rgba(16,185,129,0.12);
      border-color: rgba(16,185,129,0.6);
      color: #0f766e;
    }
    .pill-status.-ringing {
      background: rgba(250,204,21,0.16);
      border-color: rgba(234,179,8,0.6);
      color: #92400e;
    }
    .pill-status.-bad {
      background: rgba(248,113,113,0.16);
      border-color: rgba(220,38,38,0.65);
      color: #991b1b;
    }
    .pill-status.-vm {
      background: rgba(129,140,248,0.16);
      border-color: rgba(79,70,229,0.6);
      color: #312e81;
    }
    .pill-status.-neutral {
      background: rgba(148,163,184,0.16);
      border-color: rgba(148,163,184,0.6);
      color: #374151;
    }

    .ec-last-call-body-main {
      margin-top:6px;
    }

    .numbers-row {
      display:flex;
      align-items:flex-start;
      gap:8px;
      margin-bottom:6px;
      flex-wrap:wrap;
    }
    .numbers-row .num-block {
      min-width:0;
    }
    .numbers-row .num-label {
      font-size:10px;
      text-transform:uppercase;
      letter-spacing:.04em;
      color: var(--text-muted,#6b7280);
      margin-bottom:1px;
    }
    .numbers-row .num-value {
      font-size:13px;
      font-weight:500;
      white-space:nowrap;
      text-overflow:ellipsis;
      overflow:hidden;
    }
    .numbers-row .num-arrow {
      align-self:center;
      font-size:16px;
      opacity:0.65;
    }

    .ec-last-call-body-main .meta-row {
      display:flex;
      flex-wrap:wrap;
      gap:6px;
      margin-top:4px;
    }

    .ec-last-call-body-main .chip {
      border-radius:999px;
      padding:2px 7px;
      border:1px solid rgba(148,163,184,0.6);
      background: rgba(255,255,255,0.9);
      font-size:10px;
      color: var(--text-color,#111827);
    }
    .ec-last-call-body-main .chip.-ghost {
      background: rgba(248,250,252,0.9);
    }
    .ec-last-call-body-main .chip.-dur {
      font-variant-numeric: tabular-nums;
    }

    .ec-last-call-footer {
      margin-top:8px;
      display:flex;
      justify-content:flex-end;
    }

    .ec-last-call-empty {
      padding:2px 2px 0;
    }

    .record-row {
      margin-top:6px;
      font-size:11px;
    }

    [data-theme="dark"] .ec-last-call-card {
      background: radial-gradient(circle at top left, rgba(59,130,246,0.18), transparent 60%),
                  radial-gradient(circle at bottom right, rgba(16,185,129,0.22), transparent 60%),
                  var(--control-bg,#020617);
      border-color: rgba(30,64,175,0.65);
      box-shadow: 0 16px 40px rgba(15,23,42,0.75);
    }
  `;
  document.head.appendChild(css);
})();