"""
WSGI config for college_sys project.

Он выставляет WSGI callable как переменную уровня модуля ``application``.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
