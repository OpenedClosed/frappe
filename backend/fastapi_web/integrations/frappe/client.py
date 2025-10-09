# -*- coding: utf-8 -*-
import json
import logging
from typing import Any, Optional, Dict
import aiohttp
from infra import settings

logger = logging.getLogger(__name__)


class FrappeError(RuntimeError):
    """Frappe request failed."""


class FrappeClient:
    """Async Frappe REST wrapper."""

    def api_base(self) -> str:
        return (settings.FRAPPE_API_BASE or "").rstrip("/")

    def auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {settings.FRAPPE_API_KEY}:{settings.FRAPPE_API_SECRET}",
        }

    def default_fields_for_doctype(self, doctype: str) -> list[str]:
        if doctype == "User":
            return [
                "name", "email", "full_name", "first_name", "last_name",
                "username", "user_image", "enabled", "roles", "creation", "modified",
            ]
        return ["name"]

    async def request(self, fn: str, *args: Any, **kwargs: Any) -> Any:
        try:
            headers = self.auth_headers()

            if fn == "call":
                method = args[0]
                data = args[1] if len(args) > 1 else kwargs
                url = f"{self.api_base()}/api/method/{method}"

            elif fn in {"get", "get_list", "insert", "save", "get_value", "set_value", "delete"}:
                method = f"frappe.client.{fn}"
                data = args[0] if args else kwargs

                if fn == "get_list":
                    doctype = data.get("doctype")
                    if doctype and "fields" not in data:
                        data["fields"] = self.default_fields_for_doctype(doctype)
                    if isinstance(data.get("fields"), list):
                        data["fields"] = json.dumps(data["fields"])

                if isinstance(data.get("filters"), dict):
                    data["filters"] = json.dumps(data["filters"])
                if isinstance(data.get("or_filters"), (dict, list)):
                    data["or_filters"] = json.dumps(data["or_filters"])
                if isinstance(data.get("doc"), (dict, list)):
                    data["doc"] = json.dumps(data["doc"])

                url = f"{self.api_base()}/api/method/{method}"
            else:
                raise ValueError(f"Unsupported method: {fn}")

            async with aiohttp.ClientSession() as s:
                async with s.post(url, data=data, headers=headers, timeout=12) as resp:
                    txt = await resp.text()
                    try:
                        out = json.loads(txt)
                    except Exception:
                        out = {"raw": txt}
                    if resp.status >= 400 or "exc" in out:
                        raise FrappeError(out.get("exc") or f"HTTP {resp.status}: {txt}")
                    return out.get("message")
        except Exception as exc:
            logger.exception("Frappe %s failed", fn)
            raise FrappeError(str(exc)) from exc

    async def create_notification_from_upstream(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.api_base()}/api/method/dantist_app.api.integration.create_notification_from_upstream"
        headers = self.auth_headers() | {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, headers=headers, timeout=10) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                if resp.status == 200 and isinstance(data, dict) and data.get("message", {}).get("ok"):
                    return data.get("message")
        return None


client_singleton: Optional[FrappeClient] = None

def get_frappe_client() -> FrappeClient:
    global client_singleton
    if client_singleton is None:
        client_singleton = FrappeClient()
    return client_singleton
