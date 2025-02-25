"""Файл запуска бота."""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import MenuButtonWebApp, Message, WebAppInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from bot_conf.create_bot import bot, dp
from chats.routers import send_message
from fastapi_web.infra import settings
from utils.decorators import check_private_chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@dp.startup()
async def on_startup(*args, **kwargs):
    pass


@dp.shutdown()
async def on_shutdown(*args, **kwargs):
    pass


BOT_TRANSLATIONS = {
    "start_info_text": {
        "en": (
            "👋 Welcome to <b>PaNa Medica AI Assistant</b>! 🦷✨\n\n"
            "▶️ Tap the 💬 button below to start chatting with our dental assistant.\n"
            "<b>With this bot, you can:</b>\n"
            "    - Learn about services, pricing, and how to schedule an appointment 💳\n"
            "    - Get consultations about implants, prosthetics, and other procedures 🏷\n"
            "    - Book an in-person or online visit (for out-of-town patients) 📅\n"
            "    - Ask any questions about treatment, prevention, and oral care 🦷\n\n"
            "ℹ️ Use /help to learn more about additional features."
        ),
        "ru": (
            "👋 Добро пожаловать в <b>PaNa Medica AI Assistant</b>! 🦷✨\n\n"
            "▶️ Нажмите на кнопку 💬 внизу экрана, чтобы начать общение с нашим стоматологическим помощником.\n"
            "<b>С помощью этого бота вы можете:</b>\n"
            "    - Узнать о стоматологических услугах, ценах и процедуре записи на приём 💳\n"
            "    - Получить консультацию по имплантации, протезированию и другим процедурам 🏷\n"
            "    - Записаться на очный приём или онлайн-консультацию (для приезжих пациентов) 📅\n"
            "    - Задать любые вопросы о лечении, профилактике и уходе за зубами 🦷\n\n"
            "ℹ️ Используйте команду /help, чтобы узнать о дополнительных возможностях."
        ),
        "pl": (
            "👋 Witamy w <b>PaNa Medica AI Assistant</b>! 🦷✨\n\n"
            "▶️ Kliknij przycisk 💬 poniżej, aby rozpocząć rozmowę z naszym asystentem dentystycznym.\n"
            "<b>Dzięki temu botowi możesz:</b>\n"
            "    - Dowiedzieć się o usługach, cenach i jak umówić się na wizytę 💳\n"
            "    - Uzyskać konsultacje w zakresie implantów, protetyki i innych zabiegów 🏷\n"
            "    - Umówić się na wizytę stacjonarną lub online (dla pacjentów spoza miasta) 📅\n"
            "    - Zadawać pytania dotyczące leczenia, profilaktyki i higieny jamy ustnej 🦷\n\n"
            "ℹ️ Użyj /help, aby dowiedzieć się więcej o dodatkowych funkcjach."
        ),
        "uk": (
            "👋 Ласкаво просимо до <b>PaNa Medica AI Assistant</b>! 🦷✨\n\n"
            "▶️ Натисніть кнопку 💬 внизу екрана, щоб розпочати спілкування з нашим стоматологічним помічником.\n"
            "<b>За допомогою цього бота ви можете:</b>\n"
            "    - Дізнатися про послуги, ціни та як записатися на прийом 💳\n"
            "    - Отримати консультацію щодо імплантації, протезування та інших процедур 🏷\n"
            "    - Записатися на очний прийом або онлайн-консультацію (для пацієнтів з інших міст) 📅\n"
            "    - Поставити будь-які запитання стосовно лікування, профілактики та догляду за зубами 🦷\n\n"
            "ℹ️ Скористайтеся командою /help, щоб дізнатися більше про додаткові можливості."
        ),
        "ge": (
            "👋 კეთილი იყოს თქვენი მობრძანება <b>PaNa Medica AI Assistant</b>-ში! 🦷✨\n\n"
            "▶️ ქვემოთ მდებარე 💬 ღილაკზე დაჭერით, რათა დაიწყოთ საუბარი ჩვენს სტომატოლოგიურ ასისტენტთან.\n"
            "<b>ამ ბოტის საშუალებით შეგიძლიათ:</b>\n"
            "    - გაიგოთ მეტი მომსახურებების, ფასებისა და მიღებაზე ჩაწერის პროცედურის შესახებ 💳\n"
            "    - მიიღოთ კონსულტაცია იმპლანტაციაზე, პროთეზირებასა და სხვა პროცედურებზე 🏷\n"
            "    - ჩაეწეროთ კლინიკურ ან ონლაინ ვიზიტზე (თუ ქალაქგარეთ ხართ) 📅\n"
            "    - დაუსვათ ნებისმიერი შეკითხვა მკურნალობის, პროფილაქტიკისა და პირის ღრუს მოვლის შესახებ 🦷\n\n"
            "ℹ️ გამოიყენეთ /help მეტი ინფორმაციისთვის დამატებითი ფუნქციების შესახებ."
        ),
    },
    "help_info_text": {
        "en": (
            "ℹ️ <b>How to use PaNa Medica AI Assistant</b> 🦷\n\n"
            "This bot is your personal assistant for all questions related to <b>PaNa Medica</b>.\n"
            "Here’s what you can do:\n"
            "1. 📋 <b>Interactive Menu:</b> Tap the 💬 button below to access the assistant's interface.\n"
            "2. 💬 <b>Chat with AI:</b> Ask any questions about dental services, prices, booking, or online consultations.\n"
            "3. 📝 <b>Treatment Plan:</b> Get recommendations for procedures you're interested in.\n"
            "4. 🌐 <b>Additional Information:</b> Learn about gnatology, implants, prosthetics, and other services.\n\n"
            "If you need an administrator’s help, we’re always here for you! ☎️"
        ),
        "ru": (
            "ℹ️ <b>Как пользоваться PaNa Medica AI Assistant</b> 🦷\n\n"
            "Этот бот — ваш персональный помощник по всем вопросам, связанным с <b>PaNa Medica</b>.\n"
            "Вот что вы можете делать:\n"
            "1. 📋 <b>Интерактивное меню:</b> Нажмите на кнопку 💬 внизу экрана, чтобы открыть интерфейс ассистента.\n"
            "2. 💬 <b>Чат с ИИ:</b> Задавайте любые вопросы о стоматологических услугах, ценах, записи или онлайн-консультациях.\n"
            "3. 📝 <b>План лечения:</b> Получайте рекомендации по интересующим вас процедурам.\n"
            "4. 🌐 <b>Дополнительная информация:</b> Узнайте о гнатологии, имплантах, протезировании и других услугах.\n\n"
            "Если вам нужна помощь администратора, мы всегда готовы ответить! ☎️"
        ),
        "pl": (
            "ℹ️ <b>Jak korzystać z PaNa Medica AI Assistant</b> 🦷\n\n"
            "Ten bot to Twój osobisty asystent we wszystkich sprawach związanych z <b>PaNa Medica</b>.\n"
            "Co możesz zrobić:\n"
            "1. 📋 <b>Menu interaktywne:</b> Kliknij przycisk 💬 poniżej, aby otworzyć interfejs asystenta.\n"
            "2. 💬 <b>Czat z AI:</b> Zadawaj pytania dotyczące usług stomatologicznych, cen, rezerwacji lub konsultacji online.\n"
            "3. 📝 <b>Plan leczenia:</b> Uzyskaj rekomendacje dotyczące interesujących Cię zabiegów.\n"
            "4. 🌐 <b>Dodatkowe informacje:</b> Dowiedz się o gnatologii, implantach, protetyce i innych usługach.\n\n"
            "Jeśli potrzebujesz pomocy administratora, jesteśmy do Twojej dyspozycji! ☎️"
        ),
        "uk": (
            "ℹ️ <b>Як користуватися PaNa Medica AI Assistant</b> 🦷\n\n"
            "Цей бот — ваш персональний помічник з усіх питань, пов’язаних з <b>PaNa Medica</b>.\n"
            "Ось що ви можете робити:\n"
            "1. 📋 <b>Інтерактивне меню:</b> Натисніть кнопку 💬 внизу, щоб відкрити інтерфейс асистента.\n"
            "2. 💬 <b>Чат з ІІ:</b> Ставте будь-які запитання щодо стоматологічних послуг, цін, запису або онлайн-консультацій.\n"
            "3. 📝 <b>План лікування:</b> Отримуйте рекомендації щодо цікавих вам процедур.\n"
            "4. 🌐 <b>Додаткова інформація:</b> Дізнайтеся про гнатологію, імпланти, протезування та інші послуги.\n\n"
            "Якщо вам потрібна допомога адміністратора, ми завжди готові відповісти! ☎️"
        ),
        "ge": (
            "ℹ️ <b>როგორ გამოვიყენოთ PaNa Medica AI Assistant</b> 🦷\n\n"
            "ეს ბოტი თქვენი პირადი ასისტენტია ნებისმიერ შეკითხვაზე, რომელიც უკავშირდება <b>PaNa Medica</b>.\n"
            "აი რას შეგიძლიათ გააკეთოთ:\n"
            "1. 📋 <b>ინტერაქტიული მენიუ:</b> ქვემოთ მდებარე ღილაკზე 💬 დაჭერით, რათა გახსნათ ასისტენტის ინტერფეისი.\n"
            "2. 💬 <b>ჩეთი AI-სთან:</b> დასვით შეკითხვები სტომატოლოგიურ მომსახურებებზე, ფასებზე, ჩაწერაზე ან ონლაინ კონსულტაციაზე.\n"
            "3. 📝 <b>მკურნალობის გეგმა:</b> მიიღეთ რეკომენდაციები თქვენთვის საინტერესო პროცედურებზე.\n"
            "4. 🌐 <b>დამატებითი ინფორმაცია:</b> გაიგეთ მეტი გნატოლოგიის, იმპლანტაციის, პროთეზირების და სხვა მომსახურებების შესახებ.\n\n"
            "თუ ადმინისტრატორის დახმარება გჭირდებათ, ჩვენ ყოველთვის მზად ვართ! ☎️"
        ),
    }
}


@dp.message(Command("start"))
@check_private_chat
async def start(message: Message, command: CommandObject):
    """
    Обработчик команды '/start' для PaNa Medica AI Assistant.
    """
    user_lang = message.from_user.language_code
    start_text = BOT_TRANSLATIONS["start_info_text"].get(user_lang, BOT_TRANSLATIONS["start_info_text"]["en"])
    await message.answer(start_text, parse_mode=ParseMode.HTML)


@dp.message(Command("help"))
@check_private_chat
async def help(message: Message, command: CommandObject):
    """
    Обработчик команды '/help' для PaNa Medica AI Assistant.
    """
    user_lang = message.from_user.language_code
    help_text = BOT_TRANSLATIONS["help_info_text"].get(user_lang, BOT_TRANSLATIONS["help_info_text"]["en"])
    await message.answer(help_text, parse_mode=ParseMode.HTML)



async def main():
    """
    Основная функция запуска Telegram-бота с веб-сервером для Webhook.
    """
    aiohttp_app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot).register(
        aiohttp_app,
        path="/webhook")
    aiohttp_app.router.add_post("/webhook/send_message", send_message)


    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=9999)
    await site.start()

    web_app_url = f"{settings.FRONTEND_URL}/telegram-chat"
    web_app_url = "https://aihubworks.com/chats/telegram-chat"

    web_app_info = WebAppInfo(url=web_app_url)
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="💬", web_app=web_app_info))
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Работа бота остановлена с клавиатуры.")
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")
