import hmac, time, secrets, logging
from hashlib import sha256
from http.cookies import SimpleCookie

import frappe
import requests

logger = logging.getLogger(__name__)

BASE_PATH = "/integrations/frappe"  # ← как ты сказал

def make_sig(user_id: str, ts: int, nonce: str, secret: str) -> str:
    payload = f"{user_id}|{ts}|{nonce}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()

# def get_user_id() -> str:
#     return "689518945c753e6272c4f174"  # временно

@frappe.whitelist()
def get_iframe_origin() -> dict:
    origin = frappe.conf.get("dantist_iframe_origin") or ""
    if not origin:
        frappe.throw("dantist_iframe_origin not configured", exc=frappe.ValidationError)
    return {"ok": True, "origin": origin}

@frappe.whitelist()
def link_check() -> dict:
    base_url = frappe.conf.get("dantist_base_url")
    if not base_url:
        frappe.throw("Dantist base URL not configured", exc=frappe.ValidationError)

    tok = frappe.request and frappe.request.cookies.get("access_token")
    if not tok:
        return {"ok": False, "reason": "no_token"}

    url = f"{base_url.rstrip('/')}{BASE_PATH}/link_check"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {tok}"}, timeout=6)
    except Exception as e:
        frappe.throw(f"Upstream error: {e}", exc=frappe.ValidationError)

    if r.status_code == 200:
        try:
            data = r.json()
        except Exception:
            data = {"raw": (r.text or "")[:200]}
        return {"ok": True, "data": data}
    if r.status_code == 401:
        return {"ok": False, "reason": "unauthorized"}
    return {"ok": False, "reason": f"status_{r.status_code}", "body": (r.text or "")[:200]}

@frappe.whitelist()
def get_token() -> dict:
    """
    Ходим к FastAPI {BASE_PATH}/session_request, достаём access_token
    из ответа и СТАВИМ его клиенту (браузеру).
    """
    base_url = frappe.conf.get("dantist_base_url")
    secret   = frappe.conf.get("dantist_shared_secret")
    aud      = frappe.conf.get("dantist_integration_aud") or None
    if not base_url or not secret:
        frappe.throw("Dantist integration is not configured.", exc=frappe.ValidationError)

    user_id = get_user_id()
    ts      = int(time.time())
    nonce   = secrets.token_urlsafe(16)
    sig     = make_sig(user_id, ts, nonce, secret)

    url     = f"{base_url.rstrip('/')}{BASE_PATH}/session_request"
    payload = {"user_id": user_id, "ts": ts, "nonce": nonce, "sig": sig, "aud": aud}

    try:
        upstream = requests.post(url, json=payload, timeout=8)
    except Exception as e:
        frappe.throw(f"Auth upstream error: {e}", exc=frappe.ValidationError)

    if upstream.status_code != 200:
        try:
            detail = upstream.json()
        except Exception:
            detail = upstream.text
        frappe.throw(f"Upstream rejected: {detail}", exc=frappe.ValidationError)

    # 1) достаём значение куки
    token_val = upstream.cookies.get("access_token")
    if not token_val:
        set_cookie_header = upstream.headers.get("Set-Cookie")
        if set_cookie_header:
            sc = SimpleCookie(); sc.load(set_cookie_header)
            m = sc.get("access_token")
            if m: token_val = m.value
    if not token_val:
        frappe.throw("Upstream did not return access_token cookie", exc=frappe.ValidationError)

    # 2) ставим куку клиенту
    is_https = (frappe.request and frappe.request.scheme == "https")
    cm = getattr(frappe.local, "cookie_manager", None)
    if cm and hasattr(cm, "set_cookie"):
        # CookieManager из Frappe
        cm.set_cookie(
            key="access_token",
            value=token_val,
            secure=is_https,      # локально False; в проде True (https)
            httponly=False,       # как у твоей админки
            samesite="Lax",
        )
    else:
        # Фолбэк: руками добавляем Set-Cookie
        sc = SimpleCookie()
        sc["access_token"] = token_val
        sc["access_token"]["path"] = "/"
        sc["access_token"]["samesite"] = "Lax"
        if is_https:
            sc["access_token"]["secure"] = True
        # httponly=False — не ставим флаг
        cookie_header = sc.output(header="").strip()  # только значение
        headers = frappe.local.response.setdefault("headers", [])
        headers.append(("Set-Cookie", cookie_header))

    return {"ok": True}
