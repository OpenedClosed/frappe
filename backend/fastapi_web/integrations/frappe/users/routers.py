from datetime import datetime
from typing import List, Optional
from integrations.frappe.schemas import EnsureMongoAdminUserRequest
from users.db.mongo.enums import RoleEnum

from db.mongo.db_init import mongo_db
from fastapi import Query

from fastapi import APIRouter

frappe_users_router = APIRouter()

@frappe_users_router.get("/lookup")
async def frappe_users_lookup(email: str = Query(...)):
    u = await mongo_db.users.find_one({"email": email})
    if not u:
        return {"ok": False}
    return {"ok": True, "user_id": str(u["_id"])}


FRAPPE_TO_LOCAL = {
    "AIHub Super Admin": RoleEnum.SUPERADMIN,
    "System Manager":    RoleEnum.SUPERADMIN,
    "Integration":       RoleEnum.SUPERADMIN,
    "AIHub Admin":       RoleEnum.ADMIN,
    "AIHub Demo":        RoleEnum.DEMO_ADMIN,
}

ROLE_PRIORITY = [
    RoleEnum.SUPERADMIN,
    RoleEnum.ADMIN,
    RoleEnum.DEMO_ADMIN,
    RoleEnum.MAIN_OPERATOR,
    RoleEnum.STAFF,
    RoleEnum.CLIENT,
]


def pick_highest_role(candidates: List[RoleEnum]) -> RoleEnum:
    if not candidates:
        return RoleEnum.CLIENT
    for r in ROLE_PRIORITY:
        if r in candidates:
            return r
    return RoleEnum.CLIENT

def map_roles(inline_role: Optional[str], frappe_roles: Optional[List[str]]) -> RoleEnum:
    # 1) если пришла корректная локальная роль строкой — используем её
    if inline_role:
        try:
            return RoleEnum(inline_role)
        except Exception:
            pass
    # 2) иначе маппим роли из Frappe и берём «самую сильную»
    mapped: List[RoleEnum] = []
    for fr in (frappe_roles or []):
        loc = FRAPPE_TO_LOCAL.get(fr)
        if loc:
            mapped.append(loc)
    if mapped:
        return pick_highest_role(mapped)
    # 3) дефолт
    return RoleEnum.CLIENT

# ──────────────────────────────────────────────────────────────
# Хендлер: создать/актуализировать пользователя в MongoAdmin
#   • email — ключ
#   • роль маппим; существующему пользователю роль только «апгрейдим»
#   • остальное — как у тебя: пароль="", поля как раньше
# ──────────────────────────────────────────────────────────────
@frappe_users_router.post("/ensure_mongoadmin")
async def frappe_users_ensure_mongoadmin(data: EnsureMongoAdminUserRequest):
    col = mongo_db.users
    email = data.email.strip().lower()

    # целевая роль по нашим правилам
    target_role = map_roles(data.role, data.frappe_roles)

    u = await col.find_one({"email": email})
    if not u:
        doc = {
            "email": email,
            "username": (data.username or email.split("@")[0]).strip(),
            "password": "",  # как у тебя было
            "role": target_role.value,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "full_name": data.full_name,
            "avatar": None,
        }
        res = await col.insert_one(doc)
        return {"ok": True, "created": True, "user_id": str(res.inserted_id)}

    # существующий пользователь: апгрейдим роль только если стала «сильнее»
    updates = {}
    try:
        current_role = RoleEnum(u.get("role"))
    except Exception:
        current_role = RoleEnum.CLIENT

    # индекс меньше — роль сильнее (см. ROLE_PRIORITY)
    if ROLE_PRIORITY.index(target_role) < ROLE_PRIORITY.index(current_role):
        updates["role"] = target_role.value

    # дольём пустые поля
    if not u.get("full_name") and data.full_name:
        updates["full_name"] = data.full_name
    if not u.get("username") and data.username:
        updates["username"] = data.username

    if updates:
        await col.update_one({"_id": u["_id"]}, {"$set": updates})

    return {"ok": True, "created": False, "user_id": str(u["_id"])}