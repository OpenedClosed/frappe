import frappe
from frappe.utils import now_datetime, get_datetime


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====


def normalize_e164(value):
    """Привести номер к E.164 или вернуть None, если мусор."""
    if not value:
        return None

    value = str(value).strip().replace(" ", "").replace("-", "")

    if not value.startswith("+"):
        return None

    if not all(ch.isdigit() or ch == "+" for ch in value):
        return None

    return value


def get_pbx_token():
    """Получить ожидаемый токен PBX из site_config."""
    return frappe.conf.get("pbx_webhook_token")


def get_pbx_header_token():
    """Получить токен PBX из кастомного заголовка (чтобы не ломать Frappe auth)."""
    return (
        frappe.get_request_header("X-PBX-TOKEN")
        or frappe.get_request_header("X-Webhook-Token")
        or None
    )


def make_naive_datetime(value):
    """Преобразовать строку/дату в naive-datetime (без tzinfo)."""
    dt = get_datetime(value) if value else now_datetime()
    if getattr(dt, "tzinfo", None):
        dt = dt.replace(tzinfo=None)
    return dt


def apply_default_kanban_state(engagement):
    """Поставить первый этап канбана и включить флаги досок, если поля есть."""
    meta = engagement.meta

    # Общий статус кейса, если есть
    status_field = None
    for fname in ("status", "case_status", "workflow_state"):
        f = meta.get_field(fname)
        if f:
            status_field = f
            break

    if status_field:
        current_val = getattr(engagement, status_field.fieldname, None)
        if not current_val:
            options = (status_field.options or "").splitlines()
            for opt in options:
                opt = opt.strip()
                if opt:
                    setattr(engagement, status_field.fieldname, opt)
                    break

    def ensure_flag(flag_fieldname: str):
        f = meta.get_field(flag_fieldname)
        if not f:
            return
        current_val = getattr(engagement, flag_fieldname, None)
        if current_val in (None, "", 0, False):
            setattr(engagement, flag_fieldname, 1)

    def ensure_status(status_fieldname: str, fallback: str | None = None):
        f = meta.get_field(status_fieldname)
        if not f:
            return
        current_val = getattr(engagement, status_fieldname, None)
        if current_val:
            return
        options = (f.options or "").splitlines()
        for opt in options:
            opt = opt.strip()
            if opt:
                setattr(engagement, status_fieldname, opt)
                return
        if fallback:
            setattr(engagement, status_fieldname, fallback)

    # CRM board: включаем показ и первый статус
    ensure_flag("show_board_crm")
    ensure_status("status_crm_board")

    # Leads board: включаем показ и первый статус
    ensure_flag("show_board_leads")
    ensure_status("status_leads")


def publish_realtime_call_update(call_doc, engagement, event_type, phone_for_case, event_ts):
    """Отправить realtime-событие для фронта (popup-звонилка)."""
    try:
        payload = {
            "event": event_type,
            "call_id": call_doc.call_id,
            "call_name": call_doc.name,
            "status": call_doc.status,
            "direction": call_doc.direction,
            "from_number": call_doc.from_number,
            "to_number": call_doc.to_number,
            "did": call_doc.did,
            "queue": call_doc.queue,
            "ivr_language": call_doc.ivr_language,
            "agent_extension": call_doc.agent_extension,
            "ticket": engagement.name if engagement else None,
            "ticket_display_name": getattr(engagement, "display_name", None)
            if engagement
            else None,
            "ticket_title": getattr(engagement, "title", None) if engagement else None,
            "phone_for_case": phone_for_case,
            "start_ts": str(call_doc.start_ts) if call_doc.start_ts else None,
            "answer_ts": str(call_doc.answer_ts) if getattr(call_doc, "answer_ts", None) else None,
            "end_ts": str(call_doc.end_ts) if getattr(call_doc, "end_ts", None) else None,
            "event_ts": str(event_ts) if event_ts else None,
        }

        print(
            "[DNT-CALL-RT] publish",
            {"site": frappe.local.site, "user": frappe.session.user, **payload},
        )

        frappe.publish_realtime(
            "dnt_telephony_call",
            payload,
        )
    except Exception:
        frappe.log_error("Failed to publish realtime telephony update", "Telephony Realtime")

def upsert_call(call_id):
    """Найти или создать Call по call_id (идемпотентность)."""
    existing_name = frappe.db.exists("Call", {"call_id": call_id})
    if existing_name:
        return frappe.get_doc("Call", existing_name)

    doc = frappe.get_doc(
        {
            "doctype": "Call",
            "call_id": call_id,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


def get_or_create_engagement_case_by_phone(phone, event_ts):
    """Найти или создать Engagement Case по номеру телефона."""
    if not phone:
        return None

    existing = frappe.get_all(
        "Engagement Case",
        filters={"phone": phone},
        fields=["name"],
        limit=1,
    )

    if existing:
        return frappe.get_doc("Engagement Case", existing[0].name)

    title = f"Call {phone}"

    doc = frappe.get_doc(
        {
            "doctype": "Engagement Case",
            "title": title,
            "channel_type": "Call",
            "channel_platform": "Telephony",
            "phone": phone,
            "sync_enabled": 1,
            "last_event_at": event_ts,
        }
    )

    apply_default_kanban_state(doc)

    doc.insert(ignore_permissions=True)
    return doc


def attach_call_to_engagement(engagement, call_doc, event_ts):
    """Обновить кейс и привязать к нему звонок через child-таблицу."""
    engagement.last_event_at = event_ts

    if hasattr(engagement, "channel_type") and not engagement.channel_type:
        engagement.channel_type = "Call"
    if hasattr(engagement, "channel_platform") and not engagement.channel_platform:
        engagement.channel_platform = "Telephony"

    calls_field = engagement.meta.get_field("calls")
    if calls_field:
        rows = engagement.get("calls") or []
        already_linked = any(row.call == call_doc.name for row in rows)
        if not already_linked:
            engagement.append("calls", {"call": call_doc.name})

    engagement.flags.ignore_permissions = True
    engagement.save()

    return engagement


# ===== БИЗНЕС-ЛОГИКА ОБРАБОТКИ СОБЫТИЯ PBX =====


def process_pbx_event(payload):
    """Обработать одно событие PBX и вернуть краткий результат."""
    event_type = payload.get("event")
    call_id = payload.get("call_id")

    if not call_id:
        return {"ok": False, "error": "Missing call_id"}

    details = payload.get("details") or {}
    direction = details.get("direction")

    caller = normalize_e164(payload.get("caller"))
    callee_raw = payload.get("callee")
    did = normalize_e164(payload.get("did"))
    queue = payload.get("queue")
    ivr_language = payload.get("ivr_language")
    agent_extension = payload.get("agent_extension")
    timestamp_raw = payload.get("timestamp")

    event_ts = make_naive_datetime(timestamp_raw)

    recording = details.get("recording")
    billsec = details.get("billsec")

    from_number = caller
    to_number = None

    if direction == "in":
        to_number = did or normalize_e164(callee_raw)
    elif direction == "out":
        to_number = normalize_e164(callee_raw) or did

    call_doc = upsert_call(call_id)

    if event_ts:
        if event_type == "CALL_NEW":
            call_doc.start_ts = event_ts
        elif not call_doc.start_ts:
            call_doc.start_ts = event_ts

    if direction:
        call_doc.direction = direction

    if from_number:
        call_doc.from_number = from_number
    if to_number:
        call_doc.to_number = to_number
    if did:
        call_doc.did = did

    if queue:
        call_doc.queue = queue
    if ivr_language:
        call_doc.ivr_language = ivr_language
    if agent_extension:
        call_doc.agent_extension = agent_extension

    if billsec is not None:
        try:
            call_doc.billsec = int(billsec)
        except Exception:
            pass

    if recording:
        call_doc.recording_url = recording

    if event_type in ("CALL_NEW", "CALL_RINGING"):
        call_doc.status = "ringing"

    if event_type == "CALL_ANSWERED":
        call_doc.status = "answered"
        call_doc.answer_ts = event_ts

    if event_type in ("CALL_HANGUP", "CALL_MISSED", "VOICEMAIL_LEFT"):
        call_doc.end_ts = event_ts

    if event_type == "CALL_MISSED":
        call_doc.status = "missed"

    if event_type == "VOICEMAIL_LEFT":
        call_doc.status = "voicemail"

    if event_type == "CALL_HANGUP" and not call_doc.status:
        if billsec and int(billsec) > 0:
            call_doc.status = "answered"
        else:
            call_doc.status = "failed"

    call_doc.raw_payload = frappe.as_json(payload)

    phone_for_case = from_number or to_number or did
    engagement = None
    if phone_for_case:
        engagement = get_or_create_engagement_case_by_phone(phone_for_case, event_ts)
        if engagement:
            call_doc.ticket = engagement.name
            attach_call_to_engagement(engagement, call_doc, event_ts)

    call_doc.flags.ignore_permissions = True
    call_doc.save()

    try:
        publish_realtime_call_update(
            call_doc=call_doc,
            engagement=engagement,
            event_type=event_type,
            phone_for_case=phone_for_case,
            event_ts=event_ts,
        )
    except Exception:
        frappe.log_error("Failed to publish realtime PBX event", "Telephony Realtime")

    return {
        "ok": True,
        "call_id": call_id,
        "call_name": call_doc.name,
        "ticket": engagement.name if engagement else None,
    }


def process_cdr_row(row):
    """Обработать одну CDR-запись."""
    call_id = row.get("call_id") or row.get("uniqueid")
    if not call_id:
        return {"ok": False, "error": "Missing call_id"}

    start_raw = row.get("start_time")
    end_raw = row.get("end_time")

    start_ts = make_naive_datetime(start_raw)
    end_ts = make_naive_datetime(end_raw) if end_raw else None

    from_number = normalize_e164(row.get("from"))
    to_raw = row.get("to")
    did = normalize_e164(row.get("did"))
    direction = row.get("direction")
    disposition = row.get("disposition")
    billsec = row.get("billsec")
    recording_url = row.get("recording_url")

    call_doc = upsert_call(call_id)

    call_doc.start_ts = start_ts
    if end_ts:
        call_doc.end_ts = end_ts

    if direction:
        call_doc.direction = direction

    if from_number:
        call_doc.from_number = from_number

    to_number = None
    if direction == "in":
        to_number = did or normalize_e164(to_raw)
    else:
        to_number = normalize_e164(to_raw) or did
    if to_number:
        call_doc.to_number = to_number

    if did:
        call_doc.did = did

    if billsec is not None:
        try:
            call_doc.billsec = int(billsec)
        except Exception:
            pass

    if recording_url:
        call_doc.recording_url = recording_url

    if disposition == "ANSWERED":
        call_doc.status = "answered"
    elif disposition == "NO ANSWER":
        call_doc.status = "missed"
    elif disposition in ("BUSY", "FAILED"):
        call_doc.status = "failed"
    elif disposition == "VOICEMAIL":
        call_doc.status = "voicemail"

    call_doc.raw_payload = frappe.as_json(row)

    phone_for_case = from_number or to_number or did
    engagement = None
    if phone_for_case:
        last_ts = end_ts or start_ts
        engagement = get_or_create_engagement_case_by_phone(phone_for_case, last_ts)
        if engagement:
            call_doc.ticket = engagement.name
            attach_call_to_engagement(engagement, call_doc, last_ts)

    call_doc.flags.ignore_permissions = True
    call_doc.save()

    return {
        "ok": True,
        "call_id": call_id,
        "call_name": call_doc.name,
        "ticket": engagement.name if engagement else None,
    }


# ===== ПУБЛИЧНЫЕ ЭНДПОЙНТЫ PBX =====


@frappe.whitelist(allow_guest=True)
def call_event():
    """Webhook от АТС: события звонков (один или массив)."""
    frappe.local.response["type"] = "json"

    expected_token = get_pbx_token()
    received_token = get_pbx_header_token()

    if not expected_token:
        frappe.local.response["http_status_code"] = 500
        return {"ok": False, "error": "PBX token is not configured"}

    if not received_token or received_token != expected_token:
        frappe.local.response["http_status_code"] = 403
        return {"ok": False, "error": "Forbidden"}

    try:
        payload = frappe.request.get_json()
    except Exception:
        frappe.local.response["http_status_code"] = 400
        return {"ok": False, "error": "Invalid JSON"}

    if isinstance(payload, dict):
        result = process_pbx_event(payload)
        if not result.get("ok"):
            frappe.local.response["http_status_code"] = 400
        else:
            frappe.local.response["http_status_code"] = 200
        frappe.db.commit()
        return result

    if isinstance(payload, list):
        results = []
        for item in payload:
            if not isinstance(item, dict):
                results.append({"ok": False, "error": "Invalid item"})
                continue
            results.append(process_pbx_event(item))
        frappe.local.response["http_status_code"] = 200
        frappe.db.commit()
        return {"ok": True, "results": results}

    frappe.local.response["http_status_code"] = 400
    return {"ok": False, "error": "Invalid payload"}


@frappe.whitelist(allow_guest=True)
def cdr_ingest():
    """Массовый импорт CDR (по крону или ручной вызов)."""
    frappe.local.response["type"] = "json"

    expected_token = get_pbx_token()
    received_token = get_pbx_header_token()

    if not expected_token:
        frappe.local.response["http_status_code"] = 500
        return {"ok": False, "error": "PBX token is not configured"}

    if not received_token or received_token != expected_token:
        frappe.local.response["http_status_code"] = 403
        return {"ok": False, "error": "Forbidden"}

    try:
        payload = frappe.request.get_json()
    except Exception:
        frappe.local.response["http_status_code"] = 400
        return {"ok": False, "error": "Invalid JSON"}

    rows = None
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        rows = payload.get("items")

    if not isinstance(rows, list):
        frappe.local.response["http_status_code"] = 400
        return {"ok": False, "error": "Invalid payload for CDR ingest"}

    results = []
    for row in rows:
        if not isinstance(row, dict):
            results.append({"ok": False, "error": "Invalid CDR row"})
            continue
        results.append(process_cdr_row(row))

    frappe.db.commit()
    frappe.local.response["http_status_code"] = 200
    return {"ok": True, "results": results, "count": len(results)}