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

    dt.issingle = int(spec.get("issingle", 0))
    dt.custom = int(spec.get("custom", 0))
    dt.track_changes = int(spec.get("track_changes", 1))
    dt.allow_rename = int(spec.get("allow_rename", 0))
    dt.editable_grid = int(spec.get("editable_grid", 0))
    dt.engine = spec.get("engine", "InnoDB")
    dt.is_tree = int(spec.get("is_tree", 0))
    dt.istable = int(spec.get("istable", 0))

    dt.set("fields", [])
    for field in spec.get("fields", []):
        dt.append("fields", field)

    for key in ("title_field", "autoname", "search_fields", "sort_field", "sort_order"):
        if key in spec:
            setattr(dt, key, spec[key])

    dt.set("permissions", [])
    dt.set("links", [])
    dt.set("actions", [])
    dt.set("states", [])

    dt.save(ignore_permissions=True)
    write_document_file(dt)
    frappe.db.commit()
    print(f"✅ Создан DocType «{name}» (модуль: {module}, issingle={dt.issingle}).")


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


def import_docs(payload) -> None:
    if isinstance(payload, list):
        for doc in payload:
            if isinstance(doc, dict):
                if doc.get("doctype") == "DocType":
                    create_doctype_if_absent(doc)
                else:
                    upsert_one(doc)
        frappe.db.commit()
        return

    if isinstance(payload, dict):
        if payload.get("doctype") == "DocType":
            create_doctype_if_absent(payload)
        else:
            upsert_one(payload)
        frappe.db.commit()
        return

    frappe.throw("Ожидался JSON-объект или массив документов.")


def run(spec: str | None = None) -> None:
    files = normalize_spec_inputs(spec)
    print(f"🔧 Приложение: {APP_NAME}")
    print(f"📂 Папка фикстур по умолчанию: {get_fixtures_root()}")
    if spec:
        print(f"🎯 Источник: {spec}")
    else:
        print("➡️  Источник: все *.json рекурсивно из fixtures/")

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
        create_doctype_if_absent(spec_obj)
    after = frappe.db.count("DocType")
    created += max(0, after - before)

    for payload in others:
        import_docs(payload)

    print(f"🎉 Готово. Новых DocType: {created}.")
