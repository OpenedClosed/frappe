



# class ChatSessionAdmin(BaseAdmin):
#     """Админ для сессий чата. Поиск/фильтры/сортировка из базового ядра."""

#     model = ChatSession
#     collection_name = "chats"
#     permission_class = OperatorPermission()
#     icon = "pi pi-comments"

#     verbose_name = {
#         "en": "Chat Session", "pl": "Sesja czatu", "uk": "Сесія чату",
#         "ru": "Сессия чата", "ka": "ჩეთის სესია"
#     }
#     plural_name = {
#         "en": "Chat Sessions", "pl": "Sesje czatu", "uk": "Сесії чату",
#         "ru": "Сессии чата", "ka": "ჩეთის სესიები"
#     }

#     field_titles = {
#         "chat_id": {"en": "Chat ID", "pl": "ID czatu", "uk": "ID чату", "ru": "ID чата", "ka": "ჩეთის ID"},
#         "client_id_display": {"en": "Client ID", "pl": "ID klienta", "uk": "ID клієнта", "ru": "ID клиента", "ka": "კლიენტის ID"},
#         "client_source_display": {"en": "Client Source", "pl": "Źródło klienta", "uk": "Джерело клієнта", "ru": "Источник клиента", "ka": "კლიენტის წყარო"},
#         "client_name_display": {"en": "Client Name", "pl": "Nazwa klienta", "uk": "Ім'я клієнта", "ru": "Имя клиента", "ka": "კლიენტის სახელი"},
#         "company_name": {"en": "Company", "pl": "Firma", "uk": "Компанія", "ru": "Компания", "ka": "კომპანია"},
#         "status_display": {"en": "Status", "pl": "Status", "uk": "Статус", "ru": "Статус", "ka": "სტატუსი"},
#         "status_emoji": {"en": "Status Emoji", "pl": "Emoji statusu", "uk": "Емодзі статусу", "ru": "Эмодзи статуса", "ka": "სტატუსის ემოჯი"},
#         "duration_display": {"en": "Duration", "pl": "Czas trwania", "uk": "Тривалість", "ru": "Длительность", "ka": "ხანგრძლივობა"},
#         "participants_display": {"en": "Participants", "pl": "Uczestnicy", "uk": "Учасники", "ru": "Участники", "ka": "მონაწილეები"},
#         "created_at": {"en": "Created", "pl": "Utworzono", "uk": "Створено", "ru": "Создано", "ka": "შექმნის დრო"},
#         "last_activity": {"en": "Last Activity", "pl": "Ostatnia aktywność", "uk": "Остання активність", "ru": "Последняя активность", "ka": "ბოლო აქტივობა"},
#         "admin_marker": {"en": "Admin Marker", "pl": "Znacznik administratora", "uk": "Позначка адміністратора", "ru": "Админская метка", "ka": "ადმინის მარკერი"},
#         "read_state": {"en": "Read Status", "pl": "Stan przeczytania", "uk": "Статус прочитання", "ru": "Прочитано кем", "ka": "წაკითხვის სტატუსი"},
#         "updated_at": {"en": "Updated", "pl": "Zaktualizowano", "uk": "Оновлено", "ru": "Обновлён", "ka": "განახლდა"},
#         "is_unanswered": {"en": "Unanswered", "pl": "Bez odpowiedzi", "uk": "Без відповіді", "ru": "Неотвечён", "ka": "უპასუხო"},
#         "unanswered_messages_count": {"en": "Unanswered messages", "pl": "Nieodpowiedziane", "uk": "Невідповіді", "ru": "Неотвечённых", "ka": "უპასუხო შეტყობინებები"}
#     }

#     list_display = [
#         "chat_id", "client_id_display", "client_source_display",
#         "company_name", "status_emoji", "status_display",
#         "duration_display", "participants_display",
#         "created_at", "admin_marker",
#         "unanswered_messages_count",  # показываем в списке
#     ]
#     detail_fields = list_display + ["read_state"]
#     computed_fields = [
#         "client_id_display", "client_source_display", "client_name_display",
#         "status_display", "status_emoji",
#         "duration_display", "participants_display",
#         "updated_at", "is_unanswered", "unanswered_messages_count",
#     ]
#     read_only_fields = ["created_at", "last_activity"]
#     inlines = {"messages": ChatMessageInline, "client": ClientInline}

#     # Поиск (включаем computed client_name_display + lookup в master_clients)
#     search_config = {
#         "mode": "partial",
#         "logic": "or",
#         "fields": [
#             {"path": "messages.message"},
#             {"path": "company_name"},
#             {"path": "chat_id"},
#             {"path": "client_name_display"},   # << computed
#             {"lookup": {
#                 "collection": "master_clients",
#                 "query_field": "name",
#                 "project_field": "client_id",
#                 "map_to": "client.client_id",
#                 "operator": "regex"
#             }}
#         ]
#     }

#     # Классический список — оставим (ядро само объединит)
#     search_fields = ["messages.message", "company_name", "chat_id"]
#     searchable_computed_fields = ["is_unanswered", "client_name_display"]
#     default_search_mode = "partial"
#     default_search_combine = "or"

#     # Фильтры
#     filter_config = {
#         "channel": {
#             "type": "multienum",
#             "title": {"en": "Channel", "pl": "Kanał", "uk": "Канал", "ru": "Канал", "ka": "არხი"},
#             "paths": ["client.source.en", "client.source"],
#             "choices": [
#                 {"value": "Telegram",  "title": {"en": "Telegram",  "pl": "Telegram",  "uk": "Telegram",  "ru": "Telegram",  "ka": "ტელეგრამი"}},
#                 {"value": "WhatsApp",  "title": {"en": "WhatsApp",  "pl": "WhatsApp",  "uk": "WhatsApp",  "ru": "WhatsApp",  "ka": "უოთსაპი"}},
#                 {"value": "Web",       "title": {"en": "Website",   "pl": "Strona",    "uk": "Сайт",      "ru": "Сайт",     "ka": "ვებ-საიტი"}},
#                 {"value": "Instagram", "title": {"en": "Instagram", "pl": "Instagram", "uk": "Instagram", "ru": "Instagram", "ka": "ინსტაგრამი"}},
#                 {"value": "Internal",  "title": {"en": "Internal",  "pl": "Wewnętrzny","uk": "Внутрішній","ru": "Внутренний","ka": "შიდა"}}
#             ]
#         },
#         # Универсальный диапазон по дате обновления (last_activity)
#         "updated": {
#             "type": "range",
#             "title": {"en": "Updated", "pl": "Zaktualizowano", "uk": "Оновлено", "ru": "Обновлён", "ka": "განახლდა"},
#             "paths": ["last_activity"],
#             # фронт шлёт: {"from": "...ISO...", "to": "...ISO..."}
#         },
#         "client_type": {
#             "type": "multienum",
#             "title": {"en": "Type", "pl": "Typ", "uk": "Тип", "ru": "Тип", "ka": "ტიპი"},
#             "paths": ["client.metadata.type", "metadata.client_type"],
#             "choices": [
#                 {"value": "lead",    "title": {"en": "Lead", "pl": "Lead", "uk": "Лід", "ru": "Лид", "ka": "ლიდი"}},
#                 {"value": "account", "title": {"en": "Account", "pl": "Konto", "uk": "Кабінет", "ru": "Клиент ЛК", "ka": "კაბინეტი"}}
#             ]
#         },
#         "status": {
#             "kind": "computed_to_search",
#             "title": {"en": "Answer", "pl": "Odpowiedź", "uk": "Відповідь", "ru": "Ответ", "ka": "პასუხი"},
#             "mapping": {
#                 "unanswered": {
#                     "title": {"en": "Unanswered", "pl": "Bez odpowiedzi", "uk": "Без відповіді", "ru": "Неотвечён", "ka": "უპასუხო"},
#                     "__search": {"q": "true",  "mode": "exact", "fields": ["is_unanswered"]}
#                 },
#                 "answered": {
#                     "title": {"en": "Answered", "pl": "Odpowiedziane", "uk": "Відповідь надана", "ru": "Отвечён", "ka": "პასუხგაცემული"},
#                     "__search": {"q": "false", "mode": "exact", "fields": ["is_unanswered"]}
#                 }
#             }
#         }
#     }

#     sort_config = {
#         "default_field": "updated_at",
#         "default_order": -1,
#         "allow": ["updated_at", "last_activity", "created_at"],
#         "strategies": {
#             "updated_at": {
#                 "type": "array_last_match_ts",
#                 "array": "messages",
#                 "role_field": "sender_role",
#                 "role_value": "client",
#                 "timestamp_field": "timestamp",
#                 "fallbacks": ["last_activity", "created_at"]
#             }
#         }
#     }

#     STATUS_EMOJI_MAP = {
#         "Brief In Progress": "📋🛠️",
#         "Brief Completed": "📋✅",
#         "New Session": "💬🆕",
#         "Waiting for AI": "🤖⏳",
#         "Waiting for Client (AI)": "🤖✅",
#         "Waiting for Consultant": "👨‍⚕️❗",
#         "Read by Consultant": "👨‍⚕️⚠️",
#         "Waiting for Client": "👨‍⚕️✅",
#         "Closed – No Messages": "📪🚫",
#         "Closed by Timeout": "📪⌛️",
#         "Closed by Operator": "📪🔒"
#     }

#     # -------- computed --------
#     async def get_status_display(self, obj: dict, current_user=None) -> dict:
#         chat_session = ChatSession(**obj)
#         redis_key = f"chat:session:{chat_session.chat_id}"
#         status = await calculate_chat_status(chat_session, redis_key)
#         val = status.value
#         if isinstance(val, str):
#             try:
#                 val = json.loads(val)
#             except Exception:
#                 val = {"en": str(val)}
#         return val

#     async def get_status_emoji(self, obj: dict, current_user=None) -> str:
#         status_value = await self.get_status_display(obj)
#         en_label = status_value.get("en") if isinstance(status_value, dict) else None
#         return self.STATUS_EMOJI_MAP.get(en_label, "❓")

#     async def get_duration_display(self, obj: dict, current_user=None) -> dict:
#         created_at, last_activity = obj.get("created_at"), obj.get("last_activity")
#         if not created_at or not last_activity:
#             return {"en": "0h 0m", "ru": "0ч 0м", "pl": "0g 0m", "uk": "0г 0хв", "ka": "0სთ 0წთ"}
#         duration = last_activity - created_at
#         hours, remainder = divmod(duration.total_seconds(), 3600)
#         minutes, _ = divmod(remainder, 60)
#         return {
#             "en": f"{int(hours)}h {int(minutes)}m",
#             "ru": f"{int(hours)}ч {int(minutes)}м",
#             "pl": f"{int(hours)}g {int(minutes)}m",
#             "uk": f"{int(hours)}г {int(minutes)}хв",
#             "ka": f"{int(hours)}სთ {int(minutes)}წთ"
#         }

#     async def get_client_id_display(self, obj: dict, current_user=None) -> str:
#         client_data = obj.get("client")
#         value = "N/A"
#         if isinstance(client_data, dict):
#             client = Client(**client_data)
#             master = await get_master_client_by_id(client.client_id)
#             if master:
#                 value = master.client_id
#         return value

#     async def get_client_name_display(self, obj: dict, current_user=None) -> str:
#         """
#         Вычисляемое имя клиента: берём из master_clients по client_id.
#         Нужно для поиска по имени, даже если в документе чата его нет.
#         """
#         client_data = obj.get("client")
#         if not isinstance(client_data, dict):
#             return ""
#         try:
#             client = Client(**client_data)
#         except Exception:
#             return ""
#         master = await get_master_client_by_id(client.client_id)
#         return (master.name or "") if master else ""

#     async def get_client_source_display(self, obj: dict, current_user=None) -> str:
#         client_data = obj.get("client")
#         value = "Unknown"
#         if isinstance(client_data, dict):
#             client = Client(**client_data)
#             src = client.source
#             try:
#                 if isinstance(src, str):
#                     parsed = json.loads(src)
#                     value = parsed.get("en") or parsed.get("ru") or "Unknown"
#                 elif isinstance(src, dict):
#                     value = src.get("en") or src.get("ru") or "Unknown"
#                 else:
#                     parsed = json.loads(getattr(src, "value", "{}"))
#                     value = parsed.get("en") or parsed.get("ru") or "Unknown"
#             except Exception:
#                 value = "Unknown"
#         return value

#     async def get_participants_display(self, obj: dict, current_user=None) -> str:
#         messages = obj.get("messages", [])
#         if not messages:
#             return json.dumps([], ensure_ascii=False, cls=DateTimeEncoder)
#         sender_data = await build_sender_data_map(messages, extra_client_id=obj.get("client", {}).get("client_id"))
#         participants = [{"client_id": cid, "sender_info": data} for cid, data in sender_data.items()]
#         return json.dumps(participants, ensure_ascii=False, cls=DateTimeEncoder)

#     async def get_updated_at(self, obj: dict, current_user=None) -> datetime:
#         def role_en(msg_role) -> str:
#             try:
#                 return json.loads(msg_role)["en"] if isinstance(msg_role, str) else msg_role.en_value
#             except Exception:
#                 return "Unknown"
#         messages = obj.get("messages") or []
#         for msg in reversed(messages):
#             role = msg.get("sender_role")
#             if role_en(role) == SenderRole.CLIENT.en_value:
#                 return msg.get("timestamp") or obj.get("last_activity") or obj.get("created_at")
#         return obj.get("last_activity") or obj.get("created_at") or datetime.utcnow()

#     async def get_is_unanswered(self, obj: dict, current_user=None) -> bool:
#         def role_en(msg_role) -> str:
#             try:
#                 return json.loads(msg_role)["en"] if isinstance(msg_role, str) else msg_role.en_value
#             except Exception:
#                 return "Unknown"
#         msgs = obj.get("messages") or []
#         if not msgs:
#             return False
#         last_role = role_en(msgs[-1].get("sender_role"))
#         return last_role == SenderRole.CLIENT.en_value

#     async def get_unanswered_messages_count(self, obj: dict, current_user=None) -> int:
#         """
#         Счётчик «неотвеченных сообщений» в рамках сессии:
#         считаем подряд идущие в конце диалога клиентские сообщения до первого ответа ИИ/консультанта.
#         """
#         def role_en(msg_role) -> str:
#             try:
#                 return json.loads(msg_role)["en"] if isinstance(msg_role, str) else msg_role.en_value
#             except Exception:
#                 return "Unknown"
#         msgs = obj.get("messages") or []
#         if not msgs:
#             return 0
#         cnt = 0
#         for i in range(len(msgs) - 1, -1, -1):
#             if role_en(msgs[i].get("sender_role")) == SenderRole.CLIENT.en_value:
#                 cnt += 1
#             else:
#                 break
#         return cnt

#     # -------- тестовый роут (оставляем как просил) --------
#     @admin_route(
#         path="/unanswered_count",
#         method="GET",
#         auth=True,
#         permission_action="read",
#         summary="Unanswered chats count",
#         description="Количество неотвеченных чатов с учётом активных фильтров/поиска.",
#         tags=["stats"],
#         status_code=200,
#         response_model=None,
#         name="chat_sessions_unanswered_count",
#     )
#     async def unanswered_count(self, *, data: dict, current_user: Any, request, path_params, query_params):
#         raw_filters = query_params.get("filters")
#         raw_search = query_params.get("search")
#         raw_q = query_params.get("q")

#         parsed_filters: Optional[dict] = None
#         if raw_filters:
#             try:
#                 parsed_filters = json.loads(raw_filters)
#             except Exception:
#                 raise Exception("Invalid filters JSON")

#         parsed_search: Optional[dict] = None
#         if raw_search:
#             try:
#                 parsed_search = json.loads(raw_search) if str(raw_search).strip().startswith("{") else {"q": str(raw_search)}
#             except Exception:
#                 parsed_search = {"q": str(raw_search)}
#         elif raw_q:
#             parsed_search = {"q": str(raw_q)}

#         combined = {"__filters": parsed_filters or {}, "__search": parsed_search or {}} if (parsed_filters or parsed_search) else {}

#         base_filter = await self.permission_class.get_base_filter(current_user)
#         plain, search_params, filter_params = self.extract_advanced(combined)
#         mongo_filters, post_filters = await self.build_mongo_filters(filter_params, current_user)
#         search_mongo, computed_for_search, q, mode, combine = await self.build_declarative_search(search_params)

#         query: Dict[str, Any] = {**(plain or {}), **base_filter, **mongo_filters}
#         if search_mongo:
#             query = {"$and": [query, search_mongo]} if query else search_mongo

#         query = {"$and": [query, {"messages": {"$exists": True, "$ne": []}}]} if query else {"messages": {"$exists": True, "$ne": []}}

#         raw_docs: List[dict] = [d async for d in self.db.find(query)]

#         if computed_for_search:
#             flags = await asyncio.gather(*[
#                 self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in raw_docs
#             ])
#             raw_docs = [d for d, ok in zip(raw_docs, flags) if ok]

#         flags = await asyncio.gather(*[self.get_is_unanswered(d) for d in raw_docs])
#         count = sum(1 for x in flags if x)
#         return {"count": count}


