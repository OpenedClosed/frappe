# dantist_app/permissions/user/rules.py
import frappe


def get_excluded_users() -> set[str]:
    """Точные логины/почты, которые надо скрыть (lower по name/email)."""
    conf = frappe.get_conf() or {}
    configured = conf.get("dantist_excluded_users", [])
    if isinstance(configured, str):
        configured = [configured]
    base = {"Guest", "Administrator"}
    return {str(x).strip().lower() for x in base.union(set(configured)) if str(x).strip()}


def user_permission_query_conditions(user: str | None = None) -> str:
    """Фильтр списка User по ролям."""
    user = (user or frappe.session.user or "").strip()
    roles = set(frappe.get_roles(user))
    excluded = get_excluded_users()

    if "System Manager" in roles:
        return ""

    if "AIHub Admin" in roles or "AIHub Demo" in roles:
        return f"`tabUser`.name = {frappe.db.escape(user)}"

    if excluded:
        excl = ", ".join(frappe.db.escape(x) for x in excluded)
        return (
            f"lower(`tabUser`.name) NOT IN ({excl}) "
            f"AND lower(coalesce(`tabUser`.email, '')) NOT IN ({excl})"
        )

    return ""


def user_has_permission(doc, user: str | None = None) -> bool:
    """Право открытия карточки User по ролям."""
    user = (user or frappe.session.user or "").strip()
    roles = set(frappe.get_roles(user))
    excluded = get_excluded_users()

    if "System Manager" in roles:
        return True

    doc_email = (getattr(doc, "email", None) or "").strip().lower()
    doc_name_l = (doc.name or "").strip().lower()
    if doc.doctype == "User" and (doc_name_l in excluded or doc_email in excluded):
        return False

    if "AIHub Admin" in roles or "AIHub Demo" in roles:
        return doc.name == user

    return True
