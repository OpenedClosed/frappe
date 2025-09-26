# Админ-API: как дергать Поиск (search / q)

Самая простая форма — строка:

```http
GET /api/<registry>/<entity>/?q=ivanov
# или
GET /api/<registry>/<entity>/?search=ivanov
```

**Важно:**

* Режим совпадения (`partial|exact`), логика по многословному запросу (`and|or`), список полей и любые *lookups* описаны на бэкенде в конфиге модели и **подхватываются автоматически**.
* Вам обычно **не нужно** передавать `mode/logic/fields` — только строку запроса.
* Если всё же нужно JSON:

  ```http
  GET /api/<registry>/<entity>/?search={"q":"some text"}
  ```
* Поиск работает и по вычисляемым полям: сервер сам делает пост-фильтрацию/объединение результатов.

---

## Поисковые поля для чатов

Поиск выполняется по следующим полям:

### Прямые поля:
- **`messages.message`** — текст сообщений в чате
- **`company_name`** — название компании
- **`chat_id`** — идентификатор чата

### Вычисляемые поля:
- **`client_name_display`** — имя клиента (берётся из master_clients)

### Lookup-поиск:
- **Поиск по имени в master_clients** — выполняется lookup в коллекцию `master_clients` по полю `name`, результат мапится на `client.client_id`

### Пример поискового запроса:
```http
GET /api/chat_sessions/chat_sessions/?q=Иван
```
Найдёт чаты, где:
- В тексте сообщений встречается "Иван"
- В названии компании есть "Иван"  
- ID чата содержит "Иван"
- Имя клиента содержит "Иван"
- В master_clients есть запись с именем "Иван"**фильтрами** и **сортировкой**

Базовые пути:
- `GET /api/<registry>/<entity>/` — список
- `GET /api/<registry>/<entity>/{id}` — один объект
- `GET /api/<registry>/info` — метаданные для UI (конфиги поиска/фильтров/сортировки и кастомные маршруты)

---

## Что можно передать в список

Query-параметры:
- `sort_by=<field>` — поле сортировки  
- `order=1|-1` — направление (1 = ASC, -1 = DESC)  
- `page=<int>&page_size=<int>` — пагинация  
- `filters=<JSON>` — фильтры (форматы ниже)  
- `search=<JSON | string>` — расширенный/декларативный поиск **или** просто строка  
- `q=<string>` — короткий поиск (то же, что `search="<строка>"`)

> Если передан `filters`/`search` **или** пара `page+page_size`, ответ будет с метаданными:
> ```json
> { "data": [ ... ], "meta": { "page": 1, "page_size": 20, "total_count": 137, "total_pages": 7 } }
> ```
> Иначе — **просто массив** элементов `[ ... ]`.

---

## Поиск (search / q)

Самая простая форма — строка:

```http
GET /api/<registry>/<entity>/?q=ivanov
# или
GET /api/<registry>/<entity>/?search=ivanov
````

**Важно:**

* Режим совпадения (`partial|exact`), логика по многословному запросу (`and|or`), список полей и любые *lookups* описаны на бэкенде в конфиге модели и **подхватываются автоматически**.
* Вам обычно **не нужно** передавать `mode/logic/fields` — только строку запроса.
* Если всё же нужно JSON:

  ```http
  GET /api/<registry>/<entity>/?search={"q":"some text"}
  ```
* Поиск работает и по вычисляемым полям: сервер сам делает пост-фильтрацию/объединение результатов.

---

## Фильтры (`filters=<JSON>`)

Отправляйте URL-кодированный JSON:

```js
const filters = { /* см. форматы ниже */ };
fetch(`/api/<registry>/<entity>/?filters=${encodeURIComponent(JSON.stringify(filters))}`);
```

Поддерживаемые формы (универсальные):

### 1) multienum

```json
{ "status": ["active","blocked"] }
// или со структурой:
{ "status": [ { "value":"active" }, { "value":"blocked" } ] }
```

### 2) range / daterange

```json
{ "created_at": { "from":"2025-01-01T00:00:00Z", "to":"2025-01-31T23:59:59Z" } }
```

Также поддерживаются пресеты:

```json
{ "created_at": { "preset":"week" } }   // "week" | "month" | "3m"|"3months"|"90d"
```

### 3) generic-операторы

```json
{
  "name":   { "op":"contains", "value":"Clinic" },
  "type":   { "op":"in", "values":["A","B"] },
  "score":  { "op":"range", "gte":10, "lte":100 },
  "active": { "op":"eq", "value": true }
}
```

### 4) computed\_to\_search

Ключи маппинга превращаются в поиск по вычисляемым полям на сервере:

```json
{ "answer_state": ["unanswered"] }
```

### 5) enum\_lookup

Значения — ключи кейсов; сервер сам делает lookup в другой коллекции и фильтрует по `map_to`:

```json
{ "region": ["europe","asia"] }
```

---

## Доступные фильтры для чатов

### Канал (`channel`) — multienum
Фильтрация по источнику чата:
```json
{ "channel": ["Telegram", "WhatsApp", "Web", "Instagram", "Internal"] }
```

**Доступные значения:**
- `Telegram` — Телеграм
- `WhatsApp` — ВотсАп  
- `Web` — Сайт
- `Instagram` — Инстаграм
- `Internal` — Внутренний

### Дата обновления (`updated`) — range
Фильтрация по дате последней активности:
```json
{ "updated": { "from":"2025-01-01T00:00:00Z", "to":"2025-01-31T23:59:59Z" } }
```

Или с пресетами:
```json
{ "updated": { "preset":"week" } }   // "week" | "month" | "3m"|"3months"|"90d"
```

### Тип клиента (`client_type`) — multienum
Фильтрация по типу клиента:
```json
{ "client_type": ["lead", "account"] }
```

**Доступные значения:**
- `lead` — Лид
- `account` — Клиент ЛК

### Статус ответа (`status`) — computed_to_search
Фильтрация по статусу ответа на сообщения:
```json
{ "status": ["unanswered", "answered"] }
```

**Доступные значения:**
- `unanswered` — Неотвечён
- `answered` — Отвечён

### Пример комбинированных фильтров:
```json
{
  "channel": ["Telegram", "WhatsApp"],
  "updated": { "preset": "week" },
  "client_type": ["lead"],
  "status": ["unanswered"]
}
```

> Приведение типов делается на сервере: строки `"true"/"false"`, числа `"123"`, даты в ISO-виде — распознаются.

---

## Сортировка

```http
GET /api/<registry>/<entity>/?sort_by=updated_at&order=-1
```

Рекомендации:

* Используйте разрешённые поля из `/info` → `model.query_ui.sort.config.allow`.
* Значения по умолчанию — из `default_field` и `default_order`.
* Если поле сортировки вычисляемое или под стратегией (например, «последний релевантный timestamp»), сервер сам посчитает и отсортирует — для фронта это прозрачно.
* Неизвестное `sort_by` будет заменено на дефолт.

---

## Поля сортировки для чатов

### Доступные поля:
- **`updated_at`** (по умолчанию) — дата обновления с умной стратегией
- **`last_activity`** — дата последней активности в чате
- **`created_at`** — дата создания чата

### Направление сортировки:
- **`order=1`** — по возрастанию (ASC)
- **`order=-1`** — по убыванию (DESC, по умолчанию)

### Умная стратегия для `updated_at`:
При сортировке по `updated_at` используется стратегия `array_last_match_ts`:
- Ищется последнее сообщение от клиента (`sender_role: "client"`)
- Используется timestamp этого сообщения
- Если таких сообщений нет, используются fallback-поля: `last_activity`, затем `created_at`

### Пример:
```http
GET /api/chat_sessions/chat_sessions/?sort_by=created_at&order=1
```

---

## Пагинация

```http
GET /api/<registry>/<entity>/?page=1&page_size=50
```

Ответ всегда с `data` + `meta` (см. выше).

---

## Что приходит в элементах списка

* Всегда есть `"id"` — строковый `_id`.
* Поля из `list_display` + вычисляемые (`computed_fields`) уже **подставлены** в удобном виде.
* Даты — в ISO (`...Z`).
* Вложенные инлайны (если есть) приходят как массивы/объекты.

Пример (усеченно):

```json
{
  "id":"650c1e...",
  "name":"Item A",
  "status_display":{"en":"Active","ru":"Активен"},
  "created_at":"2025-01-10T12:00:00Z"
}
```

---

## Где брать схемы для форм и подсказки

`GET /api/<registry>/info`
Там на сущности:

* `model.query_ui.search.config` — как бэкенд ищет (поля, логика, lookups).
* `model.query_ui.filters.config` — доступные фильтры и их формы.
* `model.query_ui.sort.config` — сортировка (allow/дефолты/стратегии).
* `routes` — список CRUD и кастомных методов (`method`, `path`, `name`).

---

## Быстрые рецепты

**Строковый поиск + фильтр + сортировка + пагинация:**

```http
GET /api/<registry>/<entity>/
  ?q=john
  &filters=%7B%22status%22%3A%5B%22active%22%5D%2C%22created_at%22%3A%7B%22preset%22%3A%22week%22%7D%7D
  &sort_by=updated_at
  &order=-1
  &page=1
  &page_size=50
```

**Сложные фильтры через fetch:**

```js
const filters = {
  "name":   { "op":"contains", "value":"Clinic" },
  "type":   { "op":"in", "values":["A","B"] },
  "created_at": { "from":"2025-01-01T00:00:00Z", "to":"2025-01-31T23:59:59Z" }
};
fetch(`/api/<registry>/<entity>/?filters=${encodeURIComponent(JSON.stringify(filters))}`);
```

**Только поиск:**

```http
GET /api/<registry>/<entity>/?search=invoice  // эквивалентно ?q=invoice
```

---

### TL;DR

* Для поиска: отправляй **только строку** в `q` или `search`. Конфиг (режим/логика/поля/lookup) задаёт бэкенд.
* Для фильтров: шли **URL-кодированный JSON**; смотри формы в `/info`.
* Для сортировки: `sort_by` из `allow` и `order` `1|-1`.
* Пагинация: `page` + `page_size` ⇒ ответ `data` + `meta`.

---

## Примеры для чатов

### Поиск неотвеченных Telegram-чатов за неделю:
```http
GET /api/chat_sessions/chat_sessions/
  ?filters=%7B%22channel%22%3A%5B%22Telegram%22%5D%2C%22updated%22%3A%7B%22preset%22%3A%22week%22%7D%2C%22status%22%3A%5B%22unanswered%22%5D%7D
  &sort_by=updated_at
  &order=-1
```

### Поиск по тексту с фильтрацией лидов:
```js
const filters = {
  "channel": ["Telegram", "WhatsApp"],
  "client_type": ["lead"],
  "updated": { "preset": "month" }
};
fetch(`/api/chat_sessions/chat_sessions/?q=запись&filters=${encodeURIComponent(JSON.stringify(filters))}`);
```

### Получение отвеченных чатов с пагинацией:
```http
GET /api/chat_sessions/chat_sessions/
  ?filters=%7B%22status%22%3A%5B%22answered%22%5D%7D
  &sort_by=last_activity
  &order=-1
  &page=1
  &page_size=20
```

### Поиск чатов конкретной компании:
```js
const filters = {
  "company_name": { "op": "contains", "value": "Стоматология" }
};
fetch(`/api/chat_sessions/chat_sessions/?filters=${encodeURIComponent(JSON.stringify(filters))}`);
```
