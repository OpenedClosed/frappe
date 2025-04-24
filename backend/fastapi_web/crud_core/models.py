"""Базовые сущности панели приложения ядро CRUD создания."""
import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from bson import ObjectId
from fastapi import HTTPException
from fastapi.exceptions import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel, ValidationError

from .permissions import AllowAll, BasePermission

logger = logging.getLogger(__name__)


class BaseCrudCore:
    """Базовый класс для CRUD-операций в админке и личном кабинете."""

    model: Type[BaseModel]

    # Метаинформация
    verbose_name: str = "Unnamed Model"
    plural_name: str = "Unnamed Models"
    icon: str = "pi pi-folder"
    description: str = "No description provided"

    # Отображение
    list_display: List[str] = []
    detail_fields: List[str] = []
    computed_fields: List[str] = []
    read_only_fields: List[str] = []
    field_titles: Dict[str, str] = {}
    field_styles: Dict[str, Any] = {}
    field_groups: List[Dict[str, Any]] = []
    help_texts: Dict[str, Dict[str, str]] = {}

    # Инлайны
    inlines: Dict[str, Any] = {}

    # Ограничения
    user_collection_name: Optional[str] = None
    max_instances_per_user: Optional[int] = None

    allow_crud_actions: Dict[str, bool] = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }

    permission_class: BasePermission = AllowAll()

    def __init__(self, db: AsyncIOMotorCollection) -> None:
        """Инициализирует базовый CRUD-класс с переданной коллекцией Mongo."""
        self.db = db

    # --- Логика включения/отключения метода (allow_crud_actions) ---
    def check_crud_enabled(self, action: str) -> None:
        """
        Проверяет, разрешён ли этот CRUD-метод в allow_crud_actions.
        Если нет — выбрасываем 403.
        """
        if not self.allow_crud_actions.get(action, False):
            raise HTTPException(
                403, f"{action.capitalize()} is disabled for this model.")

    # --- Проверка прав (на конкретный объект или без него) ---
    def check_object_permission(
        self,
        action: str,
        user: Optional[BaseModel],
        obj: Optional[dict] = None
    ) -> None:
        """
        Универсальный вызов permission_class, проверяющий право на действие action.
        Если у permission_class нет прав — выбрасываем 403.
        """
        self.permission_class.check(action, user, obj)

    def check_permission(
        self,
        action: str,
        user: Optional[BaseModel],
        obj: Optional[dict] = None
    ) -> None:
        """
        Сочетает в себе check_crud_enabled + check_object_permission.
        Одним вызовом проверяем и включён ли метод, и права пользователя.
        """
        self.check_crud_enabled(action)
        self.check_object_permission(action, user, obj)

    # --- Вспомогательные методы ---
    def detect_id_field(self):
        """Определяет, какое поле служит идентификатором."""
        return "id" if "id" in self.model.__fields__ else "_id"

    def get_user_field_name(self) -> str:
        """Возвращает имя поля пользователя в зависимости от коллекции (если нужно)."""
        return "_id" if self.user_collection_name == self.db.name else "user_id"

    # --- Основные методы ---
    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        current_user: Optional[BaseModel] = None
    ) -> List[dict]:
        """
        Возвращает список документов с учётом фильтра (filters) и прав (permission_class).
        """
        print('-1-')
        base_filter = await self.permission_class.get_base_filter(current_user)
        print('-2-')
        query = {**(filters or {}), **base_filter}
        print('-3-')

        sort_field = sort_by or self.detect_id_field()
        print('-4-')
        cursor = self.db.find(query).sort(sort_field, order)
        print('-5-')

        objs = []
        print('-6-')
        async for raw_doc in cursor:
            print('-7-')
            objs.append(await self.format_document(raw_doc, current_user))
            print('-8-')
        return objs

    async def list(
        self,
        sort_by: Optional[str] = None,
        order: int = 1,
        filters: Optional[dict] = None,
        current_user: Optional[BaseModel] = None
    ) -> List[dict]:
        """
        Возвращает список документов (без пагинации).
        Пример вызова: crud_instance.list(current_user=user).
        """
        print('зашли в списки')
        self.check_permission("read", current_user)
        print('проверили права')

        return await self.get_queryset(filters, sort_by, order, current_user)

    async def list_with_meta(
        self,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        order: int = 1,
        filters: Optional[dict] = None,
        current_user: Optional[BaseModel] = None
    ) -> dict:
        """
        Возвращает список документов с пагинацией и метаданными.
        """

        self.check_permission("read", current_user)

        all_docs = await self.get_queryset(filters, sort_by, order, current_user)
        total_count = len(all_docs)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return {
            "data": all_docs[start_idx:end_idx],
            "meta": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
            }
        }

    async def get(
        self,
        object_id: str,
        current_user: Optional[BaseModel] = None
    ) -> Optional[dict]:
        """
        Возвращает документ по _id с учётом прав доступа и фильтра.
        """
        self.check_crud_enabled("read")
        try:
            docs = await self.get_queryset(
                filters={"_id": ObjectId(object_id)},
                current_user=current_user
            )
            obj = docs[0] if docs else None
            if obj:
                self.check_object_permission("read", current_user, obj)
            return obj
        except Exception:
            return None

    async def create(self, data: dict,
                     current_user: Optional[BaseModel] = None) -> dict:
        """
        Создаёт документ, проверяя права и ограничения.
        Автоматически добавляет user_id при необходимости.
        """
        self.check_permission("create", current_user)

        user_field = self.get_user_field_name()

        if self.max_instances_per_user is not None and current_user:
            filter_by_user = {
                user_field: str(
                    getattr(
                        current_user,
                        "id",
                        None))}
            count = await self.db.count_documents(filter_by_user)
            if count >= self.max_instances_per_user:
                raise HTTPException(
                    403, "You have reached the maximum number of allowed instances.")

        valid_data = await self._process_data(data=data)
        if current_user and user_field == "user_id" and "user_id" not in valid_data:
            user_id = current_user.data["user_id"]
            if user_id:
                valid_data["user_id"] = str(user_id)

        res = await self.db.insert_one(valid_data)
        if not res.inserted_id:
            raise HTTPException(500, "Failed to create object.")

        created_raw = await self.db.find_one({"_id": res.inserted_id})
        if not created_raw:
            raise HTTPException(500, "Failed to retrieve created object.")

        return await self.format_document(created_raw, current_user)

    async def update(self, object_id: str, data: dict,
                     current_user: Optional[BaseModel] = None) -> dict:
        """
        Обновляет объект, проверяя права на изменение.
        Убирает вычисляемые поля перед сохранением.
        """
        self.check_crud_enabled("update")

        obj = await self.db.find_one({"_id": ObjectId(object_id)})
        if not obj:
            raise HTTPException(404, "Item not found.")

        self.check_object_permission("update", current_user, obj)

        valid_data = await self._process_data(data=data, existing_obj=obj, partial=True)

        for field in self.computed_fields:
            valid_data.pop(field, None)

        res = await self.db.update_one({"_id": ObjectId(object_id)}, {"$set": valid_data})
        if res.matched_count == 0:
            raise HTTPException(500, "Failed to update object.")

        updated_raw = await self.db.find_one({"_id": ObjectId(object_id)})
        if not updated_raw:
            raise HTTPException(500, "Failed to retrieve updated object.")

        return await self.format_document(updated_raw, current_user)

    async def delete(self, object_id: str,
                     current_user: Optional[BaseModel] = None) -> dict:
        """
        Удаляет объект, проверяя права доступа.
        """
        self.check_crud_enabled("delete")

        obj = await self.db.find_one({"_id": ObjectId(object_id)})
        if not obj:
            raise HTTPException(404, "Item not found.")

        self.check_object_permission("delete", current_user, obj)

        res = await self.db.delete_one({"_id": ObjectId(object_id)})
        if res.deleted_count == 0:
            raise HTTPException(500, "Failed to delete object.")

        return {"status": "success"}

    # --- Вспомогательные методы для обработки данных ---

    def serialize_value(self, value):
        """
        Сериализует значение перед сохранением в MongoDB.
        """
        if isinstance(value, BaseModel):
            return value.dict()
        if isinstance(value, Enum):
            return value.value
        return value

    async def process_inlines(
            self, existing_doc: Optional[dict], update_data: dict, partial: bool = False) -> dict:
        """Обрабатывает вложенные инлайны с поддержкой удаления, добавления и обновления."""
        inline_data = {}
        try:
            for field, inline_cls in self.inlines.items():
                existing_inlines = existing_doc.get(
                    field, []) if existing_doc else []

                if field in update_data:
                    inline_inst = inline_cls(self.db)
                    update_inlines = update_data.pop(field)

                    if not isinstance(update_inlines, list):
                        update_inlines = [update_inlines]

                    merged_inlines = []
                    if existing_doc:
                        existing_by_id = {
                            item["id"]: item for item in existing_inlines if "id" in item}

                        for item in update_inlines:
                            if not isinstance(item, dict):
                                continue

                            if "id" in item:
                                if item.get("_delete", False):
                                    existing_by_id.pop(item["id"], None)
                                    continue

                                existing_item = existing_by_id.get(
                                    item["id"], {})
                                merged = {**existing_item, **item}
                                validated = await inline_inst.validate_data(merged, partial=False)
                                final_inline = {**merged, **validated}

                                if inline_inst.inlines:
                                    sub_inlines = await inline_inst.process_inlines(existing_item, final_inline, partial=partial)
                                    final_inline.update(sub_inlines)

                                merged_inlines.append(final_inline)
                                existing_by_id.pop(item["id"], None)
                            else:
                                validated = await inline_inst.validate_data(item, partial=False)
                                full_validated = inline_inst.model.parse_obj(
                                    validated).dict()
                                final_inline = full_validated

                                if inline_inst.inlines:
                                    sub_inlines = await inline_inst.process_inlines(None, final_inline, partial=False)
                                    final_inline.update(sub_inlines)

                                merged_inlines.append(final_inline)

                        merged_inlines.extend(existing_by_id.values())
                        inline_data[field] = merged_inlines
                    else:
                        validated_items = []
                        for item in update_inlines:
                            if not isinstance(item, dict):
                                continue

                            validated = await inline_inst.validate_data(item, partial=False)
                            full_validated = inline_inst.model.parse_obj(
                                validated).dict()
                            final_inline = full_validated

                            if inline_inst.inlines:
                                sub_inlines = await inline_inst.process_inlines(None, final_inline, partial=False)
                                final_inline.update(sub_inlines)

                            validated_items.append(final_inline)

                        inline_data[field] = validated_items
                else:
                    inline_data[field] = existing_inlines
            return inline_data
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    async def get_inlines(self, doc: dict,
                          current_user: Optional[dict] = None) -> dict:
        """
        Возвращает данные инлайнов из документа (учитывая, что каждый инлайн сам умеет фильтровать,
        если у него есть permission_class и используется current_user).
        """
        inl_data = {}
        try:
            for field, inline_cls in self.inlines.items():
                inline_inst = inline_cls(self.db)
                parent_id = doc.get("_id")
                if not parent_id:
                    inl_data[field] = []
                    continue

                found = await inline_inst.get_queryset(filters={"_id": parent_id}, current_user=current_user)
                inl_data[field] = [
                    await inline_inst.format_document(child, current_user)
                    if "id" not in child else child
                    for child in found
                ]
            return inl_data
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    async def format_document(self, doc: dict,
                              current_user: Optional[dict] = None) -> dict:
        """
        Форматирует документ, декодируя JSON-строки, вычисляя вычисляемые поля и дополняя инлайнами.
        Если нужны права на просмотр инлайнов — передаём current_user.
        """
        def parse_json_recursive(value: Any) -> Any:
            """Рекурсивно декодирует JSON-строки, если это валидный JSON."""
            if isinstance(value, str):
                try:
                    parsed_value = json.loads(value)
                    if isinstance(parsed_value, (dict, list, str)):
                        return parsed_value
                except json.JSONDecodeError:
                    pass
            if isinstance(value, list):
                return [parse_json_recursive(item) for item in value]
            if isinstance(value, dict):
                return {key: parse_json_recursive(
                    val) for key, val in value.items()}
            return value

        fields_set = list(set(self.list_display + self.detail_fields))
        result = {"id": str(doc.get("_id", doc.get("id")))}

        for field in fields_set:
            value = doc.get(field)
            result[field] = parse_json_recursive(value)

        for cf in self.computed_fields:
            method = getattr(self, f"get_{cf}", None)
            if method:
                computed_value = await method(doc)
                result[cf] = parse_json_recursive(computed_value)

        result.update(await self.get_inlines(doc, current_user))

        return result

    async def validate_data(self, data: dict, partial: bool = False) -> dict:
        """Валидирует данные (без инлайнов), декодируя JSON-строки."""

        errors: Dict[str, Any] = {}
        validated: dict = {}

        def try_parse_json(value: Any) -> Any:
            """Пытается преобразовать строку в JSON-объект."""
            if isinstance(value, str):
                try:
                    parsed_value = json.loads(value)
                    if isinstance(parsed_value, dict):
                        return parsed_value
                except json.JSONDecodeError:
                    pass
            return value

        try:
            if partial:
                for field, val in data.items():
                    if field == "id" or field in self.read_only_fields:
                        continue

                    if field in self.inlines:
                        validated[field] = self.serialize_value(val)
                        continue

                    if field in self.model.__annotations__:
                        field_type = self.model.__annotations__[field]
                        parsed_value = try_parse_json(val)
                        validated_field_value = self.model._validate_field_type(
                            field, field_type, parsed_value)
                        validated[field] = self.serialize_value(
                            validated_field_value)
            else:
                filtered_data = {
                    k: try_parse_json(v) for k, v in data.items() if k not in self.inlines
                }
                obj = self.model(**filtered_data)
                validated = {
                    k: self.serialize_value(v) for k,
                    v in obj.dict().items()}

        except ValidationError as e:
            for err in e.errors():
                loc = err["loc"]
                msg = err["msg"]
                ref = errors
                for part in loc[:-1]:
                    ref = ref.setdefault(part, {})
                ref[loc[-1]] = msg
        except ValueError as e:
            errors["detail"] = str(e)

        if errors:
            raise HTTPException(status_code=400, detail=errors)

        return validated

    async def _process_data(
            self, data: dict, existing_obj: Optional[dict] = None, partial: bool = False) -> dict:
        """Обрабатывает данные, включая валидацию и мердж инлайнов."""

        try:
            valid = await self.validate_data(data, partial=partial)

            if self.inlines:
                inline_data = await self.process_inlines(existing_obj, data, partial=partial)
                valid.update(inline_data)

            return valid
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    def _nested_find(self, doc: Any, target_id: str) -> bool:
        """Ищет target_id в документе (dict/list) рекурсивно."""
        if isinstance(doc, dict):
            if str(doc.get("id")) == target_id:
                return True
            for v in doc.values():
                if self._nested_find(v, target_id):
                    return True
        elif isinstance(doc, list):
            for item in doc:
                if self._nested_find(item, target_id):
                    return True
        return False

    def _find_container(self, doc: Any, target_id: str) -> Optional[dict]:
        """Возвращает родительский словарь, в котором находится элемент с target_id."""
        if isinstance(doc, dict):
            for k, v in doc.items():
                if k == "id" and str(v) == target_id:
                    return doc
                sub_container = self._find_container(v, target_id)
                if sub_container:
                    return sub_container
        elif isinstance(doc, list):
            for item in doc:
                sub_container = self._find_container(item, target_id)
                if sub_container:
                    return sub_container
        return None

    async def get_root_document(self, any_id: str) -> Optional[dict]:
        """Возвращает корневой документ по _id или вложенному id (любая глубина)."""
        objs = await self.db.find({"_id": ObjectId(any_id)}).to_list(None)
        if objs:
            return objs[0]
        all_parents = await self.db.find({}).to_list(None)
        for parent in all_parents:
            if self._nested_find(parent, any_id):
                return parent
        return None

    async def get_parent_container(self, any_id: str) -> Optional[dict]:
        """Возвращает родительский словарь, в котором лежит элемент с any_id."""
        root = await self.get_root_document(any_id)
        if not root:
            return None
        return self._find_container(root, any_id)

    def __str__(self) -> str:
        """Строковое представление класса."""
        return self.verbose_name


class InlineCrud(BaseCrudCore):
    """CRUD-класс для работы с вложенными объектами (инлайнами)."""

    collection_name: str = ""
    dot_field_path: str = ""

    def __init__(self, db: AsyncIOMotorDatabase):
        """Инициализирует коллекцию и базовый класс."""
        super().__init__(db)
        self.db = db[self.collection_name] if isinstance(
            db, AsyncIOMotorDatabase) else db

    async def _get_nested_field(self, doc: dict, dot_path: str) -> Any:
        """Получает вложенные данные по точечной нотации ('a.b.c')."""
        for part in dot_path.split("."):
            if not isinstance(doc, dict) or part not in doc:
                return None
            doc = doc[part]
        return doc

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = "id",
        order: int = 1,
        current_user: Optional[dict] = None
    ) -> List[dict]:
        """
        Получает список вложенных объектов (массив или словарь) из dot_field_path
        у родительских документов, прошедших фильтр permission_class + filters.
        """
        self.check_crud_enabled(
            "read")
        self.permission_class.check("read", current_user, None)

        base_filter = await self.permission_class.get_base_filter(current_user)
        query = {**(filters or {}), **base_filter}

        cursor = self.db.find(query)
        results = []

        async for parent_doc in cursor:
            nested_data = await self._get_nested_field(parent_doc, self.dot_field_path)
            if isinstance(nested_data, list):
                results.extend(nested_data)
            elif isinstance(nested_data, dict):
                results.append(nested_data)

        if sort_by:
            results.sort(key=lambda x: x.get(sort_by), reverse=(order == -1))
        return results

    async def get(
        self,
        object_id: str,
        current_user: Optional[dict] = None
    ) -> Optional[dict]:
        """
        Находит вложенный объект по ID (в dot_field_path), учитывая права доступа (read).
        """
        self.check_crud_enabled("read")

        base_filter = await self.permission_class.get_base_filter(current_user)
        query = {f"{self.dot_field_path}.id": object_id, **base_filter}

        parent_doc = await self.db.find_one(query)
        if not parent_doc:
            return None

        nested_data = await self._get_nested_field(parent_doc, self.dot_field_path)
        item = None
        if isinstance(nested_data, list):
            item = next(
                (el for el in nested_data if el.get("id") == object_id), None)
        elif isinstance(nested_data, dict) and nested_data.get("id") == object_id:
            item = nested_data

        if item:
            self.permission_class.check("read", current_user, item)

        return item

    async def create(
        self,
        data: dict,
        current_user: Optional[dict] = None
    ) -> dict:
        """
        Создаёт новый вложенный объект (append в список dot_field_path).
        """
        self.check_permission("create", current_user)

        valid_data = await self._process_data(data)
        if not valid_data:
            raise HTTPException(400, "No valid fields provided.")

        base_filter = await self.permission_class.get_base_filter(current_user)
        update_query = {"$push": {self.dot_field_path: valid_data}}

        res = await self.db.update_one(base_filter, update_query, upsert=True)
        if res.modified_count == 0 and not res.upserted_id:
            raise HTTPException(500, "Failed to create object.")

        return valid_data

    async def update(
        self,
        object_id: str,
        data: dict,
        current_user: Optional[dict] = None
    ) -> dict:
        """
        Обновляет вложенный объект в массиве (dot_field_path) по "id": object_id.
        """
        self.check_crud_enabled("update")
        existing_obj = await self.get(object_id, current_user)
        if not existing_obj:
            raise HTTPException(404, "Item not found for update.")

        self.permission_class.check("update", current_user, existing_obj)

        valid_data = await self._process_data(data, partial=True)
        if not valid_data:
            raise HTTPException(400, "No valid fields to update.")

        base_filter = await self.permission_class.get_base_filter(current_user)
        filters = {**base_filter, f"{self.dot_field_path}.id": object_id}

        update_query = {
            "$set": {f"{self.dot_field_path}.$.{k}": v for k, v in valid_data.items()}
        }

        res = await self.db.update_one(filters, update_query)
        if res.matched_count == 0:
            raise HTTPException(500, "Failed to update object.")

        updated_obj = await self.get(object_id, current_user)
        if not updated_obj:
            raise HTTPException(500, "Failed to retrieve updated object.")
        return updated_obj

    async def delete(
        self,
        object_id: str,
        current_user: Optional[dict] = None
    ) -> dict:
        """
        Удаляет вложенный объект (учитывает, что dot_field_path может быть списком или единичным объектом).
        """
        self.check_crud_enabled("delete")

        existing_obj = await self.get(object_id, current_user)
        if not existing_obj:
            raise HTTPException(404, "Item not found for deletion.")

        self.permission_class.check("delete", current_user, existing_obj)

        base_filter = await self.permission_class.get_base_filter(current_user)
        filters = {**base_filter, f"{self.dot_field_path}.id": object_id}
        parent_doc = await self.db.find_one(filters)
        if not parent_doc:
            raise HTTPException(404, "Parent document not found.")

        nested_data = await self._get_nested_field(parent_doc, self.dot_field_path)

        if isinstance(nested_data, list):
            update_query = {"$pull": {self.dot_field_path: {"id": object_id}}}
        elif isinstance(nested_data, dict):
            update_query = {"$unset": {self.dot_field_path: ""}}
        else:
            raise HTTPException(
                500, "Unexpected field structure during deletion.")

        res = await self.db.update_one(filters, update_query)
        if res.modified_count == 0:
            raise HTTPException(500, "Failed to delete object.")

        return {"status": "success"}


class BaseCrud(BaseCrudCore):
    """Базовый класс для CRUD-операций в админке."""

    collection_name: str
    inlines: Dict[str, Type[InlineCrud]] = {}

    def __init__(self, db: AsyncIOMotorDatabase):
        """Определяет основную коллекцию и инициализирует базовый класс."""
        super().__init__(db)
        self.db = db[self.collection_name]

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        current_user: Optional[dict] = None
    ) -> List[dict]:
        """Возвращает список документов, учитывая фильтры, права и сортировку."""
        print('=1=')
        self.check_crud_enabled("read")
        print('=2=')
        self.permission_class.check("read", current_user)
        print('=3=')

        base_filter = await self.permission_class.get_base_filter(current_user)
        print('=4=')
        query = {**(filters or {}), **base_filter}
        print('=5=')

        sort_field = sort_by or self.detect_id_field()
        print('=6=')
        cursor = self.db.find(query).sort(sort_field, order)
        print('=7=')

        objs = []
        print('=8=')
        # page_size = 20
        i = 0
        async for raw_doc in cursor:
            i += 1
            # print("итерация", i)
            # print(raw_doc["_id"])
            if str(raw_doc["_id"]) == "ь":
                # print("нашли урода")
                # print(len(str(raw_doc)))
                continue

            # if len(objs) >= page_size:
            #     break 
            objs.append(await self.format_document(raw_doc, current_user))
        return objs
