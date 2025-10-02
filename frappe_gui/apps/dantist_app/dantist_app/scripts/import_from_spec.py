# apps/dantist_app/dantist_app/scripts/import_from_spec.py
# -*- coding: utf-8 -*-
"""
Импорт DocType из JSON-спецификаций в папке fixtures.

— По умолчанию обходит ВСЕ *.json в папке FIXTURES_DIR и создаёт DocType,
  если его ещё нет (существующие не трогаем).
— Можно передать одно имя файла (строкой) — тогда импортируется только он.
— Права/воркспейсы НЕ создаём.
— После создания ВСЕГДА экспортируем DocType в код приложения (контроль версий).
— Логи — краткие, на русском и с эмодзи.

Запуск из корня bench-проекта:
  1) Импортировать все:
     bench --site <site> execute dantist_app.scripts.import_from_spec.run

  2) Импортировать один файл (относительно FIXTURES_DIR или абсолютный путь):
     bench --site <site> execute dantist_app.scripts.import_from_spec.run --args '["bot_settings_doctype.json"]'
     # или kwargs одной строкой:
     bench --site <site> execute dantist_app.scripts.import_from_spec.run --kwargs '"bot_settings_doctype.json"'
"""

import os
import json
import frappe
from typing import Iterable
from frappe.modules.export_file import write_document_file


# === НАСТРОЙКИ (меняйте под свой апп) =========================================
APP_NAME = "dantist_app"          # системное имя приложения
DEFAULT_MODULE = "Dantist App"    # модуль, куда создаём DocType по умолчанию
FIXTURES_DIR = "fixtures"         # папка с JSON-спецификациями внутри приложения
# =============================================================================


def get_app_path() -> str:
    """Путь до корня приложения."""
    return frappe.get_app_path(APP_NAME)


def get_fixtures_root() -> str:
    """Абсолютный путь к папке фикстур приложения."""
    return os.path.join(get_app_path(), FIXTURES_DIR)


def iter_fixture_files() -> Iterable[str]:
    """Даёт список всех *.json в FIXTURES_DIR (только файлы верхнего уровня)."""
    root = get_fixtures_root()
    if not os.path.isdir(root):
        frappe.throw(f"Папка с фикстурами не найдена: {root}")
    for name in sorted(os.listdir(root)):
        if name.lower().endswith(".json"):
            yield os.path.join(root, name)


def normalize_spec_path(spec: str | None) -> list[str]:
    """
    Возвращает список абсолютных путей спецификаций для импорта.
    Если spec не задан — все *.json из FIXTURES_DIR.
    Если задан — только указанный файл (абс./относительно FIXTURES_DIR).
    """
    if not spec:
        return list(iter_fixture_files())

    if os.path.isabs(spec):
        return [spec]

    abs_path = os.path.join(get_fixtures_root(), spec)
    return [abs_path]


def load_spec_file(spec_path: str) -> dict:
    """Загружает один JSON-файл спецификации DocType."""
    if not os.path.exists(spec_path):
        frappe.throw(f"Файл спецификации не найден: {spec_path}")
    with open(spec_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        frappe.throw(f"Ожидался JSON-объект DocType в: {spec_path}")
    return data


def ensure_module(module_name: str, app_name: str) -> None:
    """Гарантирует наличие Module Def (без создания прав/воркспейсов)."""
    if not frappe.db.exists("Module Def", module_name):
        md = frappe.new_doc("Module Def")
        md.module_name = module_name
        md.app_name = app_name
        md.save(ignore_permissions=True)
        print(f"📦 Добавлен модуль: {module_name}")


def create_doctype_if_absent(spec: dict) -> None:
    """
    Создаёт DocType из спецификации, если его ещё нет.
    Ничего не меняет у существующих.
    Сразу же экспортирует JSON-файл DocType в структуру приложения.
    """
    doctype_name = spec.get("name")
    if not doctype_name:
        frappe.throw("В спецификации отсутствует поле 'name'.")

    if frappe.db.exists("DocType", doctype_name):
        print(f"ℹ️ DocType «{doctype_name}» уже существует — пропускаю.")
        return

    module = spec.get("module") or DEFAULT_MODULE

    ensure_module(module, APP_NAME)

    # Создаём каркас DocType
    dt = frappe.new_doc("DocType")
    dt.name = doctype_name
    dt.module = module

    # Базовые безопасные настройки + прокидываем часть свойств из спецификации
    dt.issingle = int(spec.get("issingle", 0))
    dt.custom = int(spec.get("custom", 0))
    dt.track_changes = int(spec.get("track_changes", 1))
    dt.allow_rename = int(spec.get("allow_rename", 0))
    dt.editable_grid = int(spec.get("editable_grid", 0))
    dt.engine = spec.get("engine", "InnoDB")
    dt.is_tree = int(spec.get("is_tree", 0))
    dt.istable = int(spec.get("istable", 0))

    # Поля
    dt.set("fields", [])
    for field in spec.get("fields", []):
        dt.append("fields", field)

    # Прочие атрибуты (если есть)
    for key in ("title_field", "autoname", "search_fields", "sort_field", "sort_order"):
        if key in spec:
            setattr(dt, key, spec[key])

    # Не трогаем ни permissions, ни links/actions/states
    dt.set("permissions", [])
    dt.set("links", [])
    dt.set("actions", [])
    dt.set("states", [])

    dt.save(ignore_permissions=True)
    print(f"✅ Создан DocType «{doctype_name}» (модуль: {module}, issingle={dt.issingle}).")

    # Экспорт JSON в код приложения (фраппе выведет строку «Wrote document file…» — это нормально)
    write_document_file(dt)
    print("📝 Экспортирован JSON DocType в код приложения.")

    frappe.db.commit()


def run(spec: str | None = None) -> None:
    """
    Точка входа для bench execute.

    Аргументы:
      spec — (необязательно) имя файла спецификации (строка).
              Если не указано — импортируются все *.json из FIXTURES_DIR.
    """
    specs = normalize_spec_path(spec)
    print(f"🔧 Приложение: {APP_NAME}")
    print(f"📂 Папка фикстур: {get_fixtures_root()}")
    if spec:
        print(f"🎯 Импортирую файл: {spec}")
    else:
        print("➡️  Импортирую все *.json в папке фикстур")

    count_created = 0
    for path in specs:
        print(f"🔎 Обрабатываю: {path}")
        data = load_spec_file(path)
        before = frappe.db.count("DocType")
        create_doctype_if_absent(data)
        after = frappe.db.count("DocType")
        if after > before:
            count_created += 1

    print(f"🎉 Готово. Создано новых DocType: {count_created}. Остальные — уже существовали и пропущены.")
