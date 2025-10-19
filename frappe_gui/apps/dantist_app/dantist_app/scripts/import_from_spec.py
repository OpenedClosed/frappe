# apps/dantist_app/dantist_app/scripts/import_from_spec.py
# -*- coding: utf-8 -*-

import os
import json
import frappe
from typing import Iterable
from frappe.modules.export_file import write_document_file

APP_NAME = "dantist_app"
DEFAULT_MODULE = "Dantist App"
FIXTURES_DIR = "fixtures"


def get_app_path() -> str:
    return frappe.get_app_path(APP_NAME)


def get_fixtures_root() -> str:
    return os.path.join(get_app_path(), FIXTURES_DIR)


def iter_fixture_files(root: str) -> Iterable[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        # игнорируем скрытые папки/файлы
        dirnames[:] = [d for d in sorted(dirnames) if not d.startswith(".")]
        for name in sorted(filenames):
            if name.lower().endswith(".json") and not name.startswith("."):
                yield os.path.join(dirpath, name)


def normalize_spec_inputs(spec: str | None) -> list[str]:
    """
    Возвращает список файлов для импорта:
    - Если spec не задан — все *.json рекурсивно из FIXTURES_DIR.
    - Если spec — абсолютный путь к файлу — берём его.
    - Если spec — абсолютный путь к папке — берём все *.json из неё рекурсивно.
    - Если spec — относительный путь — трактуем относительно FIXTURES_DIR
      (и как файл, и как папку).
    """
    if not spec:
        root = get_fixtures_root()
        if not os.path.isdir(root):
            frappe.throw(f"Папка с фикстурами не найдена: {root}")
        return list(iter_fixture_files(root))

    # абсолютный
    if os.path.isabs(spec):
        if os.path.isdir(spec):
            return list(iter_fixture_files(spec))
        return [spec]

    # относительный — относительно FIXTURES_DIR
    abs_path = os.path.join(get_fixtures_root(), spec)
    if os.path.isdir(abs_path):
        return list(iter_fixture_files(abs_path))
    return [abs_path]


def load_json(path: str):
    if not os.path.exists(path):
        frappe.throw(f"Файл не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception as e:
            frappe.throw(f"Не удалось разобрать JSON: {path}\n{e}")


def ensure_module(module_name: str, app_name: str) -> None:
    if not frappe.db.exists("Module Def", module_name):
        md = frappe.new_doc("Module Def")
        md.module_name = module_name
        md.app_name = app_name
        md.save(ignore_permissions=True)
        print(f"📦 Добавлен модуль: {module_name}")


def coerce_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def field_identity_key(f: dict) -> str:
    # стабильный ключ — fieldname (если его нет, используем name/idx как запасной)
    return (f.get("fieldname") or f.get("name") or "").strip()


def apply_basic_doctype_props(dst, src: dict):
    for key in (
        "module", "issingle", "custom", "track_changes", "allow_rename",
        "editable_grid", "engine", "is_tree", "istable", "title_field",
        "autoname", "search_fields", "sort_field", "sort_order",
        "image_field", "default_view", "naming_rule", "row_format",
        "show_name_in_global_search", "beta", "quick_entry", "grid_page_length",
        "rows_threshold_for_grid_search", "track_views", "queue_in_background",
        "allow_events_in_timeline", "allow_auto_repeat", "make_attachments_public",
        "force_re_route_to_default_view", "show_preview_popup",
        "protect_attached_files", "index_web_pages_for_search"
    ):
        if key in src:
            val = src[key]
            if key in {"issingle", "custom", "track_changes", "allow_rename",
                       "editable_grid", "is_tree", "istable", "beta",
                       "quick_entry", "track_views", "queue_in_background",
                       "allow_events_in_timeline", "allow_auto_repeat",
                       "make_attachments_public", "force_re_route_to_default_view",
                       "show_preview_popup", "protect_attached_files",
                       "index_web_pages_for_search"}:
                val = coerce_int(val, 0)
            setattr(dst, key, val)


def create_doctype_if_absent(spec: dict) -> None:
    name = spec.get("name")
    if not name:
        frappe.throw("В спецификации DocType отсутствует поле 'name'.")
    if frappe.db.exists("DocType", name):
        print(f"ℹ️ DocType «{name}» уже существует — пропускаю.")
        return

    module = spec.get("module") or DEFAULT_MODULE
    ensure_module(module, APP_NAME)

    dt = frappe.new_doc("DocType")
    dt.name = name
    dt.module = module

    apply_basic_doctype_props(dt, spec)

    dt.set("fields", [])
    for field in spec.get("fields", []):
        dt.append("fields", field)

    for key in ("title_field", "autoname", "search_fields", "sort_field", "sort_order", "image_field", "default_view"):
        if key in spec:
            setattr(dt, key, spec[key])

    dt.set("permissions", spec.get("permissions", []))
    dt.set("links", spec.get("links", []))
    dt.set("actions", spec.get("actions", []))
    dt.set("states", spec.get("states", []))

    dt.save(ignore_permissions=True)
    write_document_file(dt)
    frappe.db.commit()
    print(f"✅ Создан DocType «{name}» (модуль: {module}, issingle={dt.issingle}).")


def update_doctype_deep(spec: dict, drop_missing_fields: bool = False) -> None:
    """
    Глубокое обновление существующего DocType:
    - обновляет базовые свойства;
    - синхронизирует поля по fieldname/name (обновить/добавить);
    - по флагу drop_missing_fields удаляет отсутствующие поля;
    - заменяет коллекции permissions/links/actions/states, если заданы в спецификации.
    """
    name = spec.get("name")
    if not name:
        frappe.throw("В спецификации DocType отсутствует поле 'name'.")
    if not frappe.db.exists("DocType", name):
        create_doctype_if_absent(spec)
        print("ℹ️ Обновление не требовалось — DocType только что создан.")
        return

    dt = frappe.get_doc("DocType", name)
    apply_basic_doctype_props(dt, spec)

    current_rows = list(dt.fields or [])
    current_map = {field_identity_key(r): r for r in current_rows if field_identity_key(r)}
    incoming_list = list(spec.get("fields", []))
    incoming_map = {field_identity_key(f): f for f in incoming_list if field_identity_key(f)}

    # удалить отсутствующие
    if drop_missing_fields:
        dt.set("fields", [current_map[k] for k in incoming_map.keys() if k in current_map])

    # индекс заново после возможного удаления
    current_rows = list(dt.fields or [])
    current_map = {field_identity_key(r): r for r in current_rows if field_identity_key(r)}

    # обновить существующие / добавить новые
    for key, fin in incoming_map.items():
        if key in current_map:
            row = current_map[key]
            for k, v in fin.items():
                if k in {"doctype", "parent", "parenttype", "parentfield", "name"}:
                    continue
                setattr(row, k, v)
        else:
            dt.append("fields", fin)

    # порядок как в спецификации
    reordered = []
    seen_ids = set()
    # актуализируем карту после добавлений
    current_rows = list(dt.fields or [])
    cur_by_key = {field_identity_key(r): r for r in current_rows if field_identity_key(r)}
    for fin in incoming_list:
        k = field_identity_key(fin)
        r = cur_by_key.get(k)
        if r and id(r) not in seen_ids:
            reordered.append(r)
            seen_ids.add(id(r))
    # если поля не удаляли — добросить «прочие»
    if not drop_missing_fields:
        for r in current_rows:
            if id(r) not in seen_ids:
                reordered.append(r)
                seen_ids.add(id(r))
    dt.set("fields", reordered)

    # заменить коллекции, если они явно заданы
    for coll in ("permissions", "links", "actions", "states"):
        if coll in spec:
            dt.set(coll, spec.get(coll) or [])

    dt.save(ignore_permissions=True)
    write_document_file(dt)
    frappe.db.commit()
    print(f"🛠 Обновлён DocType «{name}» (deep update, drop_missing_fields={bool(drop_missing_fields)}).")


def upsert_one(doc: dict) -> None:
    doctype = doc.get("doctype")
    if not doctype:
        frappe.throw("В документе отсутствует поле 'doctype'.")

    # эвристика уникального ключа
    where = None
    if "name" in doc:
        where = {"name": doc["name"]}
    elif "title" in doc:
        where = {"title": doc["title"]}

    if where:
        existing = frappe.db.get_value(doctype, where, "name")
        if existing:
            return

    d = frappe.get_doc(doc)
    d.insert(ignore_permissions=True)


def import_docs(payload, update: bool = False, drop_missing_fields: bool = False) -> None:
    if isinstance(payload, list):
        for doc in payload:
            if isinstance(doc, dict):
                if doc.get("doctype") == "DocType":
                    if update:
                        update_doctype_deep(doc, drop_missing_fields=drop_missing_fields)
                    else:
                        create_doctype_if_absent(doc)
                else:
                    upsert_one(doc)
        frappe.db.commit()
        return

    if isinstance(payload, dict):
        if payload.get("doctype") == "DocType":
            if update:
                update_doctype_deep(payload, drop_missing_fields=drop_missing_fields)
            else:
                create_doctype_if_absent(payload)
        else:
            upsert_one(payload)
        frappe.db.commit()
        return

    frappe.throw("Ожидался JSON-объект или массив документов.")


def run(spec: str | None = None, update: int | bool = 0, drop_missing_fields: int | bool = 0) -> None:
    files = normalize_spec_inputs(spec)
    print(f"🔧 Приложение: {APP_NAME}")
    print(f"📂 Папка фикстур по умолчанию: {get_fixtures_root()}")
    if spec:
        print(f"🎯 Источник: {spec}")
    else:
        print("➡️  Источник: все *.json рекурсивно из fixtures/")

    update = bool(int(update)) if isinstance(update, (int, str)) else bool(update)
    drop_missing_fields = bool(int(drop_missing_fields)) if isinstance(drop_missing_fields, (int, str)) else bool(drop_missing_fields)

    doctypes, others = [], []

    for path in files:
        print(f"🔎 {path}")
        data = load_json(path)
        if isinstance(data, dict) and data.get("doctype") == "DocType":
            doctypes.append(data)
        else:
            others.append(data)

    created = 0
    before = frappe.db.count("DocType")
    for spec_obj in doctypes:
        if update:
            update_doctype_deep(spec_obj, drop_missing_fields=drop_missing_fields)
        else:
            create_doctype_if_absent(spec_obj)
    after = frappe.db.count("DocType")
    created += max(0, after - before)

    for payload in others:
        import_docs(payload, update=update, drop_missing_fields=drop_missing_fields)

    print(f"🎉 Готово. Новых DocType: {created}.")
