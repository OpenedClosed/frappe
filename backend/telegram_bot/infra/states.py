"""Группы состояний диалогов."""
from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    START = State()

class PersonalAccount(StatesGroup):
    START = State()
