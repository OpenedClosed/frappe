"""Кастомные виджеты для диалогов."""
from typing import Callable, Dict, List, Optional, Union

from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram_dialog import DialogManager
from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.kbd import SwitchInlineQuery, Url
from aiogram_dialog.widgets.text import Text
from urllib.parse import urlencode, urljoin
from telegram_bot.infra.create_bot import bot


class SwitchInlineQueryCurrentChat(SwitchInlineQuery):
    """Кнопка для переключения в текущий чат с inline-запросом."""

    async def _render_keyboard(
            self,
            data: Dict,
            manager: DialogManager,
    ) -> List[List[InlineKeyboardButton]]:
        return [
            [
                InlineKeyboardButton(
                    text=await self.text.render_text(data, manager),
                    switch_inline_query_current_chat=await self.switch_inline.render_text(data, manager),
                ),
            ],
        ]


class WebAppUrl(Url):
    """Кнопка для перехода в Web App с использованием токена авторизации."""

    def __init__(
            self,
            text: Text,
            url: Text,
            service: Text,
            id: Optional[str] = None,
            when: Union[str, Callable, None] = None,
    ):
        super().__init__(text=text, url=url, id=id, when=when)
        self.text = text
        self.url = url
        self.service = service

    async def _render_keyboard(
            self,
            data: Dict,
            manager: DialogManager,
    ) -> List[List[InlineKeyboardButton]]:
        user_id = str(manager.event.from_user.id)
        token = None
        text_service = None

        text_url = await self.url.render_text(data, manager)
        text_service = await self.service.render_text(data, manager)
        query_params = {
            "token": token,
            "service": text_service,
        }
        filtered_params = {k: v for k, v in query_params.items() if v is not None}
        query_string = urlencode(filtered_params)
        web_app_url = f"{text_url}?{query_string}"

        return [
            [
                InlineKeyboardButton(
                    text=await self.text.render_text(data, manager),
                    web_app=WebAppInfo(url=web_app_url),
                ),
            ],
        ]
