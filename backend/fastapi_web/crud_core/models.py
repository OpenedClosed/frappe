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

logger = logging.getLogger(__name__)


class BaseCrudCore:
    """Базовый класс для CRUD-операций в админке и личном кабинете."""

    model: Type[BaseModel]

    verbose_name: str = "Unnamed Model"
    plural_name: str = "Unnamed Models"
    icon: str = "pi pi-folder"
    description: str = "No description provided"
    list_display: List[str] = []
    detail_fields: List[str] = []
    computed_fields: List[str] = []
    read_only_fields: List[str] = []
    field_titles: Dict[str, str] = {}
    inlines: Dict[str, Any] = {}
    field_groups: List[Dict[str, Any]] = []
    help_texts: Dict[str, Dict[str, str]] = {}

    user_collection_name: Optional[str] = None
    max_instances_per_user: Optional[int] = None
    allow_crud_actions: Dict[str, bool] = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }

    def __init__(self, db: AsyncIOMotorCollection) -> None:
        """Инициализирует базовый CRUD-класс с переданной коллекцией Mongo."""
        self.db = db

    async def get_user(self, db_global: AsyncIOMotorDatabase,
                       user_id: str) -> Optional[dict]:
        """Ищет пользователя в коллекции user_collection_name, используя db_global."""
        if not self.user_collection_name:
            return None
        user_coll = db_global[self.user_collection_name]
        return await user_coll.find_one({"_id": ObjectId(user_id)})

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        current_user_id: Optional[str] = None
    ) -> List[dict]:
        """Возвращает список документов с учётом фильтра и user_id (если передан)."""
        sort_by = self.detect_id_field()
        query = filters.copy() if filters else {}
        if current_user_id:
            query["user_id"] = current_user_id

        cursor = self.db.find(query)
        if sort_by:
            cursor = cursor.sort(sort_by, order)

        objs = []
        async for raw_doc in cursor:
            objs.append(await self.format_document(raw_doc))
        return objs

    async def list(
        self,
        sort_by: Optional[str] = None,
        order: int = 1,
        filters: Optional[dict] = None,
        current_user_id: Optional[str] = None
    ) -> List[dict]:
        """Возвращает список документов (без пагинации)."""
        if not self.allow_crud_actions["read"]:
            raise HTTPException(403, "Reading is disabled for this model.")

        return await self.get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            current_user_id=current_user_id
        )

    async def list_with_meta(
        self,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        order: int = 1,
        filters: Optional[dict] = None,
        current_user_id: Optional[str] = None
    ) -> dict:
        """Возвращает список документов с пагинацией и метаданными."""
        if not self.allow_crud_actions["read"]:
            raise HTTPException(403, "Reading is disabled for this model.")

        all_docs = await self.get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            current_user_id=current_user_id
        )
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

    async def get(self, object_id: str,
                  current_user_id: Optional[str] = None) -> Optional[dict]:
        """Возвращает документ по _id, с учётом user_id (если задан)."""
        if not self.allow_crud_actions["read"]:
            raise HTTPException(403, "Reading is disabled for this model.")

        try:
            docs = await self.get_queryset(
                filters={"_id": ObjectId(object_id)},
                current_user_id=current_user_id
            )
            return docs[0] if docs else None
        except BaseException:
            return None

    async def create(self, data: dict,
                     current_user_id: Optional[str] = None) -> dict:
        """
        Создаёт документ, проверяя права на создание и ограничение числа объектов для пользователя.
        Если это не коллекция пользователей, автоматически добавляет user_id.
        """
        if not self.allow_crud_actions["create"]:
            raise HTTPException(403, "Creating is disabled for this model.")

        user_field = "_id" if self.user_collection_name == self.db.name else "user_id"

        if self.max_instances_per_user is not None and current_user_id:
            count_for_user = await self.db.count_documents({user_field: ObjectId(current_user_id)})
            if count_for_user >= self.max_instances_per_user:
                raise HTTPException(
                    403, "You have reached the maximum number of allowed instances.")

        valid_data = await self._process_data(data=data)

        if current_user_id and user_field == "user_id" and "user_id" not in valid_data:
            valid_data["user_id"] = current_user_id

        res = await self.db.insert_one(valid_data)
        if not res.inserted_id:
            raise HTTPException(500, "Failed to create object.")

        created_raw = await self.db.find_one({"_id": res.inserted_id})
        if not created_raw:
            raise HTTPException(500, "Failed to retrieve created object.")

        return await self.format_document(created_raw)

    async def update(self, object_id: str, data: dict,
                     current_user_id: Optional[str] = None) -> dict:
        """
        Обновляет объект, проверяя права на изменение и принадлежность пользователю (если нужно).
        Убирает вычисляемые поля при сохранении.
        """
        if not self.allow_crud_actions["update"]:
            raise HTTPException(403, "Updating is disabled for this model.")

        raw_existing_obj = await self.db.find_one({"_id": ObjectId(object_id)})
        if not raw_existing_obj:
            raise HTTPException(404, "Item not found for update.")

        if current_user_id and raw_existing_obj.get(
                "user_id") and raw_existing_obj.get("user_id") != current_user_id:
            raise HTTPException(
                403, "You don't have permission to update this object.")

        valid_data = await self._process_data(data=data, existing_obj=raw_existing_obj, partial=True)

        for cf in self.computed_fields:
            if cf in valid_data:
                del valid_data[cf]

        res = await self.db.update_one({"_id": ObjectId(object_id)}, {"$set": valid_data})
        if res.matched_count == 0:
            raise HTTPException(500, "Failed to update object.")

        updated_raw = await self.db.find_one({"_id": ObjectId(object_id)})
        if not updated_raw:
            raise HTTPException(500, "Failed to retrieve updated object.")

        return await self.format_document(updated_raw)

    async def delete(self, object_id: str,
                     current_user_id: Optional[str] = None) -> dict:
        """
        Удаляет документ, проверяя права на удаление и принадлежность пользователю (если нужно).
        """
        if not self.allow_crud_actions["delete"]:
            raise HTTPException(403, "Deleting is disabled for this model.")

        existing_obj = await self.get(object_id, current_user_id=current_user_id)
        if not existing_obj:
            raise HTTPException(404, "Item not found for deletion.")

        if current_user_id and existing_obj.get(
                "user_id") and existing_obj.get("user_id") != current_user_id:
            raise HTTPException(
                403, "You don't have permission to delete this object.")

        res = await self.db.delete_one({"_id": ObjectId(object_id)})
        if res.deleted_count == 0:
            raise HTTPException(500, "Failed to delete object.")

        return {"status": "success"}

    def serialize_value(self, value):
        """Сериализует значение перед сохранением в MongoDB."""
        if isinstance(value, BaseModel):
            return value.dict()
        elif isinstance(value, Enum):
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

    async def get_inlines(self, doc: dict) -> dict:
        """Возвращает данные инлайнов из документа."""
        inl_data = {}
        try:
            for field, inline_cls in self.inlines.items():
                inline_inst = inline_cls(self.db)
                parent_id = doc.get("_id")
                if not parent_id:
                    inl_data[field] = []
                    continue
                found = await inline_inst.get_queryset(filters={"_id": parent_id})
                inl_data[field] = [
                    await inline_inst.format_document(child) if "id" not in child else child
                    for child in found
                ]
            return inl_data
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    async def format_document(self, doc: dict) -> dict:
        """Форматирует документ, декодируя JSON-строки, вычисляя вычисляемые поля и дополняя инлайнами."""
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

        result.update(await self.get_inlines(doc))
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

    def detect_id_field(self):
        """Определяет, какое поле служит идентификатором."""
        return "id" if "id" in self.model.__fields__ else "_id"

    def __str__(self) -> str:
        """Строковое представление класса."""
        return self.verbose_name


class InlineCrud(BaseCrudCore):
    """CRUD-класс для работы с вложенными объектами (инлайнами)."""

    collection_name: str = ""
    dot_field_path: str = ""

    def __init__(self, db: AsyncIOMotorDatabase):
        """Инициализация базы данных и коллекции."""
        super().__init__(db)
        self.db = db[self.collection_name] if isinstance(
            db, AsyncIOMotorDatabase) else db

    async def _get_nested_field(self, doc: dict, dot_path: str) -> Any:
        """Получает вложенные данные по точечной нотации."""
        for part in dot_path.split("."):
            if not isinstance(doc, dict) or part not in doc:
                return None
            doc = doc[part]
        return doc

    async def get_queryset(
        self, filters: Optional[dict] = None,
        sort_by: Optional[str] = "id",
        order: int = 1,
        current_user_id: Optional[str] = None
    ) -> List[dict]:
        """Получает список вложенных объектов."""
        query = filters.copy() if filters else {}
        # if current_user_id:
        #     query["user_id"] = current_user_id

        cursor = self.db.find(query)
        results = []

        async for doc in cursor:
            nested_data = await self._get_nested_field(doc, self.dot_field_path)
            if isinstance(nested_data, list):
                results.extend(nested_data)
            elif isinstance(nested_data, dict):
                results.append(nested_data)

        if sort_by:
            results.sort(key=lambda x: x.get(sort_by), reverse=(order == -1))

        return results

    async def get(self, object_id: str,
                  current_user_id: Optional[str] = None) -> Optional[dict]:
        """Находит вложенный объект по ID, с учётом user_id (если задан)."""
        filters = {f"{self.dot_field_path}.id": object_id}
        # if current_user_id:
        #     filters["user_id"] = current_user_id

        parent_doc = await self.db.find_one(filters)
        if not parent_doc:
            return None

        nested_data = await self._get_nested_field(parent_doc, self.dot_field_path)
        if isinstance(nested_data, list):
            return next(
                (item for item in nested_data if item.get("id") == object_id), None)

        return nested_data if nested_data and nested_data.get(
            "id") == object_id else None

    async def create(self, data: dict,
                     current_user_id: Optional[str] = None) -> dict:
        """Создаёт новый вложенный объект."""
        valid_data = await self._process_data(data)
        if not valid_data:
            raise HTTPException(400, "No valid fields provided.")

        query = {}
        if current_user_id:
            query["user_id"] = current_user_id

        update_query = {"$push": {self.dot_field_path: valid_data}}

        res = await self.db.update_one(query, update_query, upsert=True)
        if res.modified_count == 0:
            raise HTTPException(500, "Failed to create object.")

        return valid_data

    async def update(self, object_id: str, data: dict,
                     current_user_id: Optional[str] = None) -> dict:
        """Обновляет вложенный объект в массиве."""
        existing_obj = await self.get(object_id, current_user_id)
        if not existing_obj:
            raise HTTPException(404, "Item not found for update.")

        valid_data = await self._process_data(data, partial=True)
        if not valid_data:
            raise HTTPException(400, "No valid fields to update.")

        filters = {f"{self.dot_field_path}.id": object_id}
        # if current_user_id:
        #     filters["user_id"] = current_user_id

        update_query = {
            "$set": {f"{self.dot_field_path}.$.{k}": v for k, v in valid_data.items()}
        }

        res = await self.db.update_one(filters, update_query)
        if res.matched_count == 0:
            raise HTTPException(500, "Failed to update object.")

        return await self.get(object_id, current_user_id)

    async def delete(self, object_id: str,
                     current_user_id: Optional[str] = None) -> dict:
        """Удаляет вложенный объект (учитывает массив или одиночный объект)."""
        existing_obj = await self.get(object_id, current_user_id)
        if not existing_obj:
            raise HTTPException(404, "Item not found for deletion.")

        # Проверяем, является ли dot_field_path массивом или одиночным объектом
        parent_doc = await self.db.find_one({f"{self.dot_field_path}.id": object_id})
        if not parent_doc:
            raise HTTPException(404, "Parent document not found.")

        nested_data = await self._get_nested_field(parent_doc, self.dot_field_path)

        filters = {f"{self.dot_field_path}.id": object_id}
        update_query = {}

        if isinstance(nested_data, list):
            # Удаление из массива через $pull
            update_query = {"$pull": {self.dot_field_path: {"id": object_id}}}
        elif isinstance(nested_data, dict):
            # Если поле - одиночный объект, просто обнуляем его
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
        sort_by: Optional[str] = "_id",
        order: int = 1,
        current_user_id: Optional[str] = None
    ) -> List[dict]:
        """Возвращает список документов, учитывая фильтры и сортировку."""
        query = filters.copy() if filters else {}
        id_field_key = self.detect_id_field()

        cursor = self.db.find(query)
        if sort_by:
            cursor = cursor.sort(sort_by, order)
        else:
            cursor = cursor.sort(id_field_key, -1)

        objs: List[dict] = []
        async for raw_doc in cursor:
            objs.append(await self.format_document(raw_doc))

        return objs
