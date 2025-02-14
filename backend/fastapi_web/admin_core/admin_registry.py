"""Регистрация для сущностей админ-панели."""


class AdminRegistry:
    """Класс регистрации моделей админ-панели."""

    def __init__(self):
        self.registry = {}

    def register(self, name: str, admin_class):
        self.registry[name] = admin_class

    def get_registered_admins(self):
        return self.registry


admin_registry = AdminRegistry()
