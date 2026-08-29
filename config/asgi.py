"""
ASGI config for college_sys project.

Он выставляет ASGI callable как переменную уровня модуля ``application``.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
