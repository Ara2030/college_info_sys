# -*- coding: utf-8 -*-
"""Конфигурация приложения «Авторизация и роли»."""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Авторизация, роли и безопасность'

    def ready(self):
        # Подключаем сигналы аутентификации (журналирование входов)
        from . import signals  # noqa: F401
