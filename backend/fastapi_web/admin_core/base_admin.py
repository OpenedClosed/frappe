"""Базовые сущности админ-панели."""
import logging
from typing import Any, Dict, List, Optional, Type

from bson import ObjectId
from fastapi import HTTPException
from fastapi.exceptions import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel, ValidationError, create_model

logger = logging.getLogger(__name__)


class BaseAdminCore:
    """Базовый класс для админок."""

    model: Type[BaseModel]
    verbose_name: str = "Unnamed Model"
    plural_name: str = "Unnamed Models"
    icon: str = "pi pi-folder"
    description: str = "No description provided"
    list_display: List[str] = []
    computed_fields: List[str] = []
    read_only_fields: List[str] = []
    field_titles: Dict[str, str] = {}
    inlines: Dict[str, Type["BaseAdminCore"]] = {}

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Инициализация."""
        self.db = db

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1
    ) -> List[dict]:
        """Получение списка документов."""
        query = filters.copy() if filters else {}
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
        filters: Optional[dict] = None
    ) -> List[dict]:
        """Список документов (без пагинации)."""
        return await self.get_queryset(filters=filters, sort_by=sort_by, order=order)

    async def list_with_meta(
        self,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        order: int = 1,
        filters: Optional[dict] = None
    ) -> dict:
        """Список документов с пагинацией."""
        all_docs = await self.get_queryset(filters=filters, sort_by=sort_by, order=order)
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

    async def get(self, object_id: str) -> Optional[dict]:
        """Получить документ по _id."""
        try:
            docs = await self.get_queryset(filters={"_id": ObjectId(object_id)})
            return docs[0] if docs else None
        except BaseException:
            return None

    async def create(self, data: dict) -> dict:
        """Создать документ."""
        print('?1')
        valid = await self._process_data(data=data)
        print('?2')

        res = await self.db.insert_one(valid)
        print('?3')

        if not res.inserted_id:
            raise HTTPException(500, "Failed to create object.")
        print('?4')

        created_old = await self.get(str(res.inserted_id))
        print('?5')
        created_raw_obj = await self.db.find_one({"_id": res.inserted_id})
        print('?6')

        if not created_raw_obj:
            raise HTTPException(500, "Failed to retrieve created object.")
        print('?7')

        created = await self.format_document(created_raw_obj)
        print('?8')

        return created

    async def update(self, object_id: str, data: dict) -> dict:
        """Обновляет объект по object_id."""
        print('?1')
        raw_existing_obj = await self.db.find_one({"_id": ObjectId(object_id)})
        if not raw_existing_obj:
            raise HTTPException(404, "Item not found for update.")
        try:
            print('?2')
            valid = await self._process_data(data=data, existing_obj=raw_existing_obj, partial=True)
            print('?3')
            for cf in self.computed_fields:
                if cf in valid:
                    del valid[cf]
            print('?4')
            id_field_key = self.detect_id_field()
            print('?5')
            res = await self.db.update_one({id_field_key: ObjectId(object_id)}, {"$set": valid})
            print('?6')
            if res.matched_count == 0:
                raise HTTPException(500, "Failed to update object.")
            print('?7')
            updated_raw = await self.db.find_one({id_field_key: ObjectId(object_id)})
            if not updated_raw:
                raise HTTPException(500, "Failed to retrieve updated object.")
            print('?8')
            return await self.format_document(updated_raw)
            print('?9')
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    async def delete(self, object_id: str) -> dict:
        """Удалить документ."""
        existing_obj = await self.get(object_id)
        if not existing_obj:
            raise HTTPException(404, "Item not found for deletion.")
        res = await self.db.delete_one({"_id": ObjectId(object_id)})
        if res.deleted_count == 0:
            raise HTTPException(500, "Failed to delete object.")
        return {"status": "success"}

    async def process_inlines(
            self, existing_doc: Optional[dict], update_data: dict, partial: bool = False) -> dict:
        """Рекурсивный мерж inline-данных с поддержкой вложенности."""
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

    async def process_inlines(
            self, existing_doc: Optional[dict], update_data: dict, partial: bool = False) -> dict:
        """Рекурсивный мерж inline-данных с поддержкой вложенности."""
        inline_data = {}
        try:
            logger.info(
                "Начало обработки инлайнов. partial=%s, update_data_keys=%s",
                partial,
                update_data.keys())

            for field, inline_cls in self.inlines.items():
                existing_inlines = existing_doc.get(
                    field, []) if existing_doc else []
                logger.debug(
                    "Обработка инлайна для поля: %s. Кол-во существующих: %d",
                    field,
                    len(existing_inlines))

                if field in update_data:
                    inline_inst = inline_cls(self.db)
                    update_inlines = update_data.pop(field)
                    logger.debug(
                        "Обнаружены обновленные инлайны для %s. Кол-во: %d",
                        field,
                        len(update_inlines) if isinstance(
                            update_inlines,
                            list) else 1)

                    if not isinstance(update_inlines, list):
                        update_inlines = [update_inlines]

                    merged_inlines = []

                    if existing_doc:
                        existing_by_id = {
                            item["id"]: item for item in existing_inlines if "id" in item}
                        logger.debug(
                            "Создана карта существующих инлайнов по ID. Размер: %d",
                            len(existing_by_id))

                        for item in update_inlines:
                            if not isinstance(item, dict):
                                logger.warning(
                                    "Пропущен некорректный элемент в update_inlines: %s", item)
                                continue

                            if "id" in item:
                                if item.get("_delete", False):
                                    existing_by_id.pop(item["id"], None)
                                    logger.info(
                                        "Удален инлайн с ID: %s", item["id"])
                                    continue

                                existing_item = existing_by_id.get(
                                    item["id"], {})
                                merged = {**existing_item, **item}
                                logger.debug(
                                    "Мерж существующего инлайна ID=%s с новыми данными", item["id"])

                                validated = await inline_inst.validate_data(merged, partial=False)
                                final_inline = {**merged, **validated}
                                logger.debug(
                                    "Валидация успешна для ID=%s", item["id"])

                                if inline_inst.inlines:
                                    sub_inlines = await inline_inst.process_inlines(existing_item, final_inline, partial=partial)
                                    final_inline.update(sub_inlines)
                                    logger.debug(
                                        "Обработаны вложенные инлайны для ID=%s", item["id"])

                                merged_inlines.append(final_inline)
                                existing_by_id.pop(item["id"], None)
                            else:
                                validated = await inline_inst.validate_data(item, partial=False)
                                full_validated = inline_inst.model.parse_obj(
                                    validated).dict()
                                final_inline = full_validated
                                logger.debug(
                                    "Создан новый валидированный инлайн без ID")

                                if inline_inst.inlines:
                                    sub_inlines = await inline_inst.process_inlines(None, final_inline, partial=False)
                                    final_inline.update(sub_inlines)
                                    logger.debug(
                                        "Обработаны вложенные инлайны для нового объекта")

                                merged_inlines.append(final_inline)

                        merged_inlines.extend(existing_by_id.values())
                        inline_data[field] = merged_inlines
                    else:
                        validated_items = []
                        for item in update_inlines:
                            if not isinstance(item, dict):
                                logger.warning(
                                    "Пропущен некорректный элемент в update_inlines: %s", item)
                                continue

                            validated = await inline_inst.validate_data(item, partial=False)
                            full_validated = inline_inst.model.parse_obj(
                                validated).dict()
                            final_inline = full_validated
                            logger.debug(
                                "Создан новый валидированный инлайн без существующего документа")

                            if inline_inst.inlines:
                                sub_inlines = await inline_inst.process_inlines(None, final_inline, partial=False)
                                final_inline.update(sub_inlines)
                                logger.debug(
                                    "Обработаны вложенные инлайны для нового объекта")

                            validated_items.append(final_inline)

                        inline_data[field] = validated_items
                else:
                    inline_data[field] = existing_inlines

            logger.info(
                "Завершена обработка инлайнов. Количество полей: %d",
                len(inline_data))
            return inline_data

        except Exception as e:
            logger.error(
                "Ошибка при обработке инлайнов: %s",
                str(e),
                exc_info=True)
            raise HTTPException(400, detail=str(e))

    async def get_inlines(self, doc: dict) -> dict:
        """Получение инлайнов из документа."""
        inl_data = {}
        try:
            for field, inline_cls in self.inlines.items():
                inline_inst = inline_cls(self.db)
                parent_id = doc.get("_id")
                if not parent_id:
                    inl_data[field] = []
                    continue
                filters = {"_id": parent_id}
                found = await inline_inst.get_queryset(filters=filters)
                inl_data[field] = [
                    await inline_inst.format_document(child) if "id" not in child else child
                    for child in found
                ]
            return inl_data
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    async def format_document(self, doc: dict) -> dict:
        """Формирование результирующего документа."""
        result = {"id": str(doc.get("_id", doc.get("id")))}
        for f in self.list_display:
            result[f] = doc.get(f)
        for cf in self.computed_fields:
            if method := getattr(self, f"get_{cf}", None):
                result[cf] = await method(doc)
        result.update(await self.get_inlines(doc))
        return result

    async def validate_data(self, data: dict, partial: bool = False) -> dict:
        """Валидация данных (без учёта инлайнов)."""
        errors: Dict[str, Any] = {}
        validated: dict = {}

        try:
            if partial:
                for field, val in data.items():
                    if field == "id" or field in self.read_only_fields:
                        continue
                    if field in self.model.__annotations__:
                        if field in self.inlines:
                            validated[field] = val
                            continue
                        field_type = self.model.__annotations__[field]
                        temp_model = create_model(
                            "TempModel", **{field: (field_type, ...)})
                        validated_field = temp_model(**{field: val})
                        validated[field] = validated_field.dict(
                            exclude_unset=True)[field]
            else:
                filtered_data = {k: v for k,
                                 v in data.items() if k not in self.inlines}
                obj = self.model(**filtered_data)
                validated.update(obj.dict(exclude_unset=True))
        except ValidationError as e:
            for err in e.errors():
                loc = err["loc"]
                ref = errors
                for part in loc[:-1]:
                    ref = ref.setdefault(part, {})
                ref[loc[-1]] = err["msg"]

        if errors:
            raise HTTPException(400, detail=errors)
        return validated

    async def _process_data(
            self, data: dict, existing_obj: Optional[dict] = None, partial: bool = False) -> dict:
        """Обрабатывает данные (валидация и мерж инлайнов)."""
        try:
            print('?11')
            valid = await self.validate_data(data, partial=partial)
            print('?12')
            if self.inlines:
                print('?13')
                inline_data = await self.process_inlines(existing_obj, data, partial=partial)
                print('?14')
                valid.update(inline_data)
                print('?15')
            return valid
        except Exception as e:
            raise HTTPException(400, detail=str(e))

    def _nested_find(self, doc: Any, target_id: str) -> bool:
        """Рекурсивный поиск id во вложенных структурах."""
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
        """Поиск словаря, содержащего элемент с нужным id."""
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
        """Поиск корневого документа по _id или вложенному id."""
        objs = await self.db.find({"_id": ObjectId(any_id)}).to_list(None)
        if objs:
            return objs[0]
        all_parents = await self.db.find({}).to_list(None)
        for parent in all_parents:
            if self._nested_find(parent, any_id):
                return parent
        return None

    async def get_parent_container(self, any_id: str) -> Optional[dict]:
        """Поиск словаря, в котором лежит элемент c нужным id."""
        root = await self.get_root_document(any_id)
        if not root:
            return None
        return self._find_container(root, any_id)

    def detect_id_field(self):
        """Определить ключ поля идентификатора."""
        return "id" if "id" in self.model.__fields__ else "_id"

    def __str__(self) -> str:
        """Строковое представление."""
        return self.verbose_name


class InlineAdmin(BaseAdminCore):
    """Базовый класс для инлайнов."""

    collection_name: str = ""
    dot_field_path: str = ""

    def __init__(self, db: AsyncIOMotorDatabase):
        """Инициализация."""
        super().__init__(db)
        if isinstance(db, AsyncIOMotorDatabase):
            self.db = db[self.collection_name]
        elif isinstance(db, AsyncIOMotorCollection):
            self.db = db

    async def _get_nested_field(self, doc: dict, dot_path: str) -> Any:
        """Получить значение поля по точечной нотации."""
        if not dot_path:
            return None
        current = doc
        for part in dot_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1
    ) -> List[dict]:
        """Извлечь список вложенных объектов."""
        filters = filters.copy() if filters else {}
        doc = await self.db.find_one({})
        cursor = self.db.find(filters)
        results: List[dict] = []
        async for doc in cursor:
            nested_data = await self._get_nested_field(doc, self.dot_field_path)
            if isinstance(nested_data, list):
                for item in nested_data:
                    results.append(item)
            elif isinstance(nested_data, dict):
                results.append(nested_data)
        id_field_key = self.detect_id_field()
        reverse_sort = (order == -1)
        if sort_by:
            results.sort(key=lambda x: x.get(sort_by), reverse=reverse_sort)
        else:
            results.sort(
                key=lambda x: x.get(id_field_key),
                reverse=reverse_sort)

        return results

    async def get(self, object_id: str) -> Optional[dict]:
        """Найти вложенный объект по его ID."""
        parent_doc = await self.db.find_one({f"{self.dot_field_path}.id": object_id})
        if not parent_doc:
            return None
        nested_array = await self._get_nested_field(parent_doc, self.dot_field_path) or []
        if isinstance(nested_array, list):
            for item in nested_array:
                if item.get("id") == object_id:
                    return await self.format_document(item)
        else:
            if nested_array.get("id") == object_id:
                return await self.format_document(nested_array)
        return None

    async def update(self, object_id: str, data: dict) -> dict:
        """Обновляет документ или вложенный объект (inline)."""
        existing_obj = await self.get(object_id)
        if not existing_obj:
            raise HTTPException(404, "Item not found for update.")

        valid = await self._process_data(data=data, partial=True)
        if not valid:
            raise HTTPException(400, "No valid fields to update.")

        id_field_key = self.detect_id_field()

        if not self.dot_field_path:
            filter_query = {id_field_key: ObjectId(object_id)}
            update_query = {"$set": valid}
            res = await self.db.update_one(filter_query, update_query)
        else:
            filter_query = {f"{self.dot_field_path}.id": object_id}
            update_query = {
                "$set": {f"{self.dot_field_path}.$.{key}": value for key, value in valid.items()}
            }
            res = await self.db.update_one(filter_query, update_query)

        if res.matched_count == 0:
            raise HTTPException(500, "Failed to update object.")

        updated = await self.get(object_id)
        if not updated:
            raise HTTPException(500, "Failed to retrieve updated object.")

        return updated

    async def delete(self, object_id: str) -> dict:
        """Удаляет документ или вложенный объект (inline)."""
        existing_obj = await self.get(object_id)
        if not existing_obj:
            raise HTTPException(404, "Item not found for deletion.")

        if not self.dot_field_path:
            res = await self.db.delete_one({"_id": ObjectId(object_id)})
        else:
            res = await self.db.update_one(
                {f"{self.dot_field_path}.id": object_id},
                {"$pull": {self.dot_field_path: {"id": object_id}}}
            )

        if (not self.dot_field_path and res.deleted_count == 0) or (
                self.dot_field_path and res.modified_count == 0):
            raise HTTPException(500, "Failed to delete object.")

        return {"status": "success"}


class BaseAdmin(BaseAdminCore):
    """Основной класс для админок."""

    collection_name: str
    inlines: Dict[str, Type[InlineAdmin]] = {}

    def __init__(self, db: AsyncIOMotorDatabase):
        """Инициализация."""
        super().__init__(db)
        self.db = db[self.collection_name]

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1
    ) -> List[dict]:
        """Получение списка документов."""
        filters = filters.copy() if filters else {}
        cursor = self.db.find(filters)
        id_field_key = self.detect_id_field()
        if sort_by:
            cursor = cursor.sort(sort_by, order)
        else:
            cursor = cursor.sort(id_field_key, -1)

        objs: List[dict] = []
        async for raw_doc in cursor:
            objs.append(await self.format_document(raw_doc))
        return objs
