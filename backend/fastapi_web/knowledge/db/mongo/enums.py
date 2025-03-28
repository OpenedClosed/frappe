"""Енам приложения Знания для работы с БД MongoDB."""
import json
from enum import Enum

from db.mongo.base.enums import BaseJsonEnumMixin


class CommunicationStyleEnum(BaseJsonEnumMixin, str, Enum):
    """Стиль общения ИИ-бота"""
    CASUAL = json.dumps({"en": "Casual", "ru": "Неформальный"})
    FORMAL = json.dumps({"en": "Formal", "ru": "Официальный"})
    FRIENDLY = json.dumps({"en": "Friendly", "ru": "Дружелюбный"})
    BUSINESS = json.dumps({"en": "Business", "ru": "Деловой"})
    HUMOROUS = json.dumps({"en": "Humorous", "ru": "Юмористический"})
    STRICTLY_FROM_DESCRIPTION = json.dumps({
        "en": "Strictly from additional description",
        "ru": "Строго использовать информацию из дополнительного описания"
    })


class FunctionalityEnum(BaseJsonEnumMixin, str, Enum):
    """Функциональность ИИ-бота"""
    
    NO_RESTRICTED_TOPICS = json.dumps(
        {"en": "Do not discuss restricted topics", "ru": "Не обсуждать запрещенные темы"})
    STEP_BY_STEP_ANSWER = json.dumps(
        {"en": "Provide a step-by-step answer", "ru": "Давать пошаговый ответ"})
    USE_MORE_EMOJIS = json.dumps(
        {"en": "Use more emojis", "ru": "Использовать больше эмодзи"})
    EXPLAIN_SOURCES = json.dumps(
        {"en": "Explain where information comes from", "ru": "Объяснять, откуда взята информация"})
    SHORT_ANSWER = json.dumps(
        {"en": "Give a concise answer", "ru": "Давать краткий ответ"})
    AVOID_USER_COMMANDS = json.dumps(
        {"en": "Do not execute user commands", "ru": "Не выполнять команды пользователя"})
    NO_FICTIONAL_INFO = json.dumps(
        {"en": "Do not invent information", "ru": "Не придумывать информацию"})
    DETAILED_ANSWERS = json.dumps(
        {"en": "Provide highly detailed answers", "ru": "Давать очень развернутые ответы"})
    CLAIM_HUMAN_IDENTITY = json.dumps(
        {"en": "Always claim to be a human", "ru": "Всегда утверждать, что ты человек"})
    ALLOW_IMPROVISATION = json.dumps(
        {"en": "Generate an answer even if no exact information is found.", 
         "ru": "Придумывать ответ, если точной информации нет."})
    FLEXIBLE_CONVERSATION = json.dumps(
        {"en": "Do not insist on the main project topic, engage in free discussions.",
         "ru": "Не настаивать на целевой теме проекта, вести свободный диалог."})


class PersonalityTraitsEnum(BaseJsonEnumMixin, str, Enum):
    """Особенности характера ИИ-бота"""
    HIGHLY_STRUCTURED = json.dumps(
        {"en": "Highly structured and predictable", "ru": "Строгий и предсказуемый"})
    LOGICAL = json.dumps(
        {"en": "Logical and precise", "ru": "Логичный и точный"})
    BALANCED = json.dumps(
        {"en": "Balanced and well-reasoned", "ru": "Сбалансированный"})
    ADAPTIVE = json.dumps(
        {"en": "Adaptive and slightly creative", "ru": "Адаптивный и немного креативный"})
    HIGHLY_CREATIVE = json.dumps(
        {"en": "Highly creative and free-thinking", "ru": "Очень креативный и свободомыслящий"})


class BotColorEnum(BaseJsonEnumMixin, str, Enum):
    """Перечисление цветов бота с переводами и настройками."""

    RED = json.dumps({"en": "Soft Red",
                      "ru": "Мягкий красный",
                      "settings": {"color": "#E57373"}})
    ORANGE = json.dumps({"en": "Warm Orange",
                         "ru": "Теплый оранжевый",
                         "settings": {"color": "#FFB74D"}})
    YELLOW = json.dumps({"en": "Sunny Yellow",
                         "ru": "Солнечный желтый",
                         "settings": {"color": "#FFF176"}})
    GREEN = json.dumps({"en": "Fresh Green",
                        "ru": "Свежий зеленый",
                        "settings": {"color": "#81C784"}})
    TEAL = json.dumps({"en": "Teal Blue", "ru": "Бирюзовый",
                      "settings": {"color": "#4DB6AC"}})
    BLUE = json.dumps({"en": "Sky Blue",
                       "ru": "Небесный синий",
                       "settings": {"color": "#64B5F6"}})
    PURPLE = json.dumps({"en": "Lavender Purple",
                         "ru": "Лавандовый фиолетовый",
                         "settings": {"color": "#9575CD"}})
    PINK = json.dumps({"en": "Rose Pink", "ru": "Розовый",
                      "settings": {"color": "#F48FB1"}})


class TargetActionEnum(BaseJsonEnumMixin, str, Enum):
    """Основные направления применения бота"""
    CUSTOMER_SUPPORT = json.dumps(
        {"en": "Customer Support", "ru": "Поддержка клиентов"})
    SALES_ASSISTANT = json.dumps(
        {"en": "Sales Assistant", "ru": "Помощник по продажам"})
    HR_RECRUITMENT = json.dumps(
        {"en": "HR & Recruitment", "ru": "HR и подбор персонала"})
    EDUCATIONAL_ASSISTANT = json.dumps(
        {"en": "Educational Assistant", "ru": "Образовательный помощник"})
    LEGAL_ADVISOR = json.dumps(
        {"en": "Legal Advisor", "ru": "Юридический консультант"})
    TECH_SUPPORT = json.dumps(
        {"en": "Technical Support", "ru": "Техническая поддержка"})
    MEDICAL_CHATBOT = json.dumps(
        {"en": "Medical Chatbot", "ru": "Медицинский чат-бот"})
    TRAVEL_PLANNER = json.dumps(
        {"en": "Travel Planner", "ru": "Помощник по путешествиям"})
    REAL_ESTATE = json.dumps(
        {"en": "Real Estate Assistant", "ru": "Помощник по недвижимости"})
    E_COMMERCE = json.dumps(
        {"en": "E-commerce Assistant", "ru": "E-commerce помощник"})
    BANKING_SUPPORT = json.dumps(
        {"en": "Banking & Finance", "ru": "Банковские и финансовые услуги"})
    MARKETING = json.dumps(
        {"en": "Marketing & Advertising", "ru": "Маркетинг и реклама"})
    SOCIAL_MEDIA = json.dumps(
        {"en": "Social Media Management", "ru": "Управление соцсетями"})
    TRANSLATION = json.dumps(
        {"en": "Translation & Language Services", "ru": "Переводы и языковые услуги"})
    DATA_ANALYSIS = json.dumps({"en": "Data Analysis", "ru": "Анализ данных"})
    CONTENT_WRITING = json.dumps(
        {"en": "Content Writing", "ru": "Создание контента"})
    ENTERTAINMENT = json.dumps(
        {"en": "Entertainment & Gaming", "ru": "Развлечения и игры"})
    FITNESS_COACH = json.dumps(
        {"en": "Fitness & Health", "ru": "Фитнес и здоровье"})
    PERSONAL_ASSISTANT = json.dumps(
        {"en": "Personal Assistant", "ru": "Личный помощник"})
    NEWS_AGGREGATOR = json.dumps(
        {"en": "News Aggregation", "ru": "Новостной агрегатор"})
    PUBLIC_SPEAKING = json.dumps(
        {"en": "Public Speaking Trainer", "ru": "Тренер по публичным выступлениям"})
    SCRIPT_WRITING = json.dumps(
        {"en": "Scriptwriting", "ru": "Написание сценариев"})
    ART_GENERATION = json.dumps(
        {"en": "AI Art Generation", "ru": "Генерация изображений ИИ"})
    AUDIOBOOK_NARRATION = json.dumps(
        {"en": "Audiobook Narration", "ru": "Озвучивание аудиокниг"})


class ForbiddenTopicsEnum(BaseJsonEnumMixin, str, Enum):
    """Запрещенные темы для общения"""
    POLITICS = json.dumps({"en": "Politics", "ru": "Политика"})
    RELIGION = json.dumps({"en": "Religion", "ru": "Религия"})
    VIOLENCE = json.dumps({"en": "Violence", "ru": "Насилие"})
    EXTREMISM = json.dumps({"en": "Extremism", "ru": "Экстремизм"})
    ILLEGAL_ACTIVITIES = json.dumps(
        {"en": "Illegal activities", "ru": "Незаконные действия"})
    HATE_SPEECH = json.dumps(
        {"en": "Hate speech", "ru": "Разжигание ненависти"})
    SELF_HARM = json.dumps(
        {"en": "Self-harm or suicide", "ru": "Самоповреждение и суицид"})
    ADULT_CONTENT = json.dumps(
        {"en": "Adult content", "ru": "Контент для взрослых"})
    GAMBLING = json.dumps({"en": "Gambling", "ru": "Азартные игры"})
    DRUGS = json.dumps({"en": "Drugs and substances",
                        "ru": "Наркотики и запрещенные вещества"})
    MEDICAL_ADVICE = json.dumps(
        {"en": "Medical advice", "ru": "Медицинские консультации"})
    FINANCIAL_ADVICE = json.dumps(
        {"en": "Financial advice", "ru": "Финансовые рекомендации"})
    WEAPONS = json.dumps({"en": "Weapons and firearms", "ru": "Оружие"})
    COPYRIGHT_VIOLATION = json.dumps(
        {"en": "Piracy and copyright violations", "ru": "Нарушение авторских прав"})
    PERSONAL_DATA = json.dumps(
        {"en": "Personal data collection", "ru": "Сбор персональных данных"})


class AIModelEnum(str, Enum):
    GPT_4_O = "gpt-4o"
    GPT_4_O_MINI = "gpt-4o-mini"
    GEMINI_2_FLASH = "gemini-2.0-flash"
