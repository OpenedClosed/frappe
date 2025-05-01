"""Енам приложения Пользователи для работы с БД MongoDB."""
from enum import Enum


class RoleEnum(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    STAFF = "staff"
    MAIN_OPERATOR = "main_operator"
    CLIENT = "client"
