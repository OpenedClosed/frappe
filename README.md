# PaNa Medica AI

**PaNa Medica AI** — это проект, предоставляющий ИИ-помощника для стоматологической клиники. Приложение включает:

- **Чат с ИИ-помощником**, разработанный на **FastAPI**, который отвечает на вопросы о процедурах, услугах, записи и другой информации о стоматологии.
- **MongoDB** для хранения сообщений и истории чатов, обеспечивая удобный доступ к диалогам.
- **Redis** для управления сессиями чата, позволяя пользователям продолжать диалог без потери контекста.
- **Веб-интерфейс** на **Nuxt 3** с использованием **vue-advanced-chat** для пациентов и административной зоны.
- **Telegram-бот** и **мини-приложение**, упрощающие взаимодействие прямо в Telegram.

**PaNa Medica AI** помогает автоматизировать первичную консультацию и ответы на частые вопросы, снижая нагрузку на персонал и улучшая качество обслуживания пациентов.


## Стек технологий
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/-MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)
![Redis](https://img.shields.io/badge/-Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Nuxt.js](https://img.shields.io/badge/-Nuxt.js-00DC82?style=flat-square&logo=nuxt.js&logoColor=white)
![Docker](https://img.shields.io/badge/-Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/-Nginx-009639?style=flat-square&logo=nginx&logoColor=white)

## Локальный запуск

### Подготовка окружения
1. Клонируйте репозиторий:
   ```bash
   git clone git@github.com:OpenedClosed/DrivingSchool.git
   ```
2. Убедитесь, что у вас установлены Python 3.10+, Node.js, Yarn и Docker.
3. Создайте виртуальное окружение для backend:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Для Linux/Mac
   venv\Scripts\activate  # Для Windows
   ```
4. Установите зависимости для backend:
   ```bash
   pip install -r backend/infra/requirements.txt
   ```

### Запуск backend
Перейдите в директорию backend и выполните команду:
```bash
cd backend/fastapi_web
uvicorn main:app --host localhost --reload
```
Backend будет доступен по адресу: http://localhost:8000

### Запуск Telegram-бота
Перейдите в директорию с ботом и запустите его:
```bash
cd backend/telegram_bot
python -m bot
```

### Запуск фронтенда
1. Установите зависимости:
   ```bash
   cd frontend
   yarn
   ```
2. Запустите дев-сервер:
   ```bash
   yarn dev
   ```
Фронтенд будет доступен по адресу: http://localhost:3000

## Запуск на продакшене
На продакшене используется **Docker Compose**. Убедитесь, что Docker и Docker Compose установлены.

1. Перейдите в директорию с файлом `docker-compose.yml`:
   ```bash
   cd infra
   ```
2. Запустите приложение с помощью Docker Compose:
   ```bash
   docker-compose up -d
   ```

### Состав контейнеров:
- **mongo**: база данных для хранения сообщений и истории чатов.
- **redis**: поддержка сессий чатов.
- **redis_storage**: поддержка сессий Telegram-бота.
- **backend**: сервер FastAPI.
- **bot**: Telegram-бот.
- **frontend**: веб-интерфейс для клиентов.
- **nginx**: маршрутизация запросов.

### Доступ:
- **Web**: https://panamed-aihubworks.com/
- **Telegram-бот**: доступ через Telegram.

## Структура проекта
- **.github/workflows** — CI/CD настройки для GitHub Actions.
- **backend**:
  - **fastapi_web** — исходный код FastAPI.
  - **telegram_bot** — исходный код Telegram-бота.
  - **infra** — инфраструктурные файлы (docker-compose.yml, requirements.txt).
- **frontend** — исходный код Nuxt 3.
- **mongo** — данные MongoDB (volume).
- **nginx** — конфигурация Nginx.
- **README.md** — документация.

## Контакты
Для вопросов и предложений обращайтесь по почте: opendoor200179@gmail.com.

