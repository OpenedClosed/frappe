import frappe


def boot_session(bootinfo):
    """Пробрасываем iframe_mode из site_config в frappe.boot."""
    env = frappe.conf.get("iframe_mode") or "DEV"
    bootinfo.iframe_mode = str(env).upper()