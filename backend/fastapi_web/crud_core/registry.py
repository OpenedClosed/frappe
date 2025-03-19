"""Регистрация для сущностей приложения ядро CRUD создания."""


class BaseRegistry:
    def __init__(self, name):
        self.name = name
        self.registry = {}

    def register(self, name: str, registry_class):
        self.registry[name] = registry_class

    def get_registered(self):
        return self.registry


admin_registry = BaseRegistry("admin")
account_registry = BaseRegistry("account")
