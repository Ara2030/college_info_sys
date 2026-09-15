# -*- coding: utf-8 -*-
"""
Middleware безопасности и аудита.

  SecurityHeadersMiddleware — дополнительные защитные заголовки (CSP, Permissions-Policy)
  AuditLogMiddleware        — журналирование действий (POST/PUT/DELETE, доступ)
"""
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied

logger = logging.getLogger('college.security')


def get_client_ip(request):
    """IP-адрес клиента с учётом прокси."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class SecurityHeadersMiddleware:
    """
    Добавляет защитные заголовки:
      - Content-Security-Policy (ограничение источников скриптов и стилей);
      - Permissions-Policy (отключение ненужных API браузера);
      - Cross-Origin-Opener-Policy.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # CSP: разрешаем только собственные ресурсы и CDN Bootstrap
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=(), payment=()')
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        return response


class AuditLogMiddleware:
    """
    Журналирует действия пользователей: изменения (POST/PUT/DELETE),
    отказы в доступе и экспорт данных. Записи сохраняются в AuditLog.
    """

    EXCLUDED_PATHS = ('/static/', '/media/', '/favicon.ico', '/admin/jsi18n/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._log(request, response)
        except Exception:  # noqa: BLE001 — аудит не должен ломать запросы
            logger.exception('Ошибка записи журнала аудита')
        return response

    def _log(self, request, response):
        path = request.path
        if any(path.startswith(p) for p in self.EXCLUDED_PATHS):
            return
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        action = None
        description = ''

        if response.status_code in (401, 403) or isinstance(
                getattr(response, 'exception', None), PermissionDenied):
            action = 'access_denied'
            description = f'Отказ в доступе: {request.method} {path}'
        elif request.method == 'POST':
            if 'login' in path and response.status_code in (301, 302) and user:
                return  # вход логируется отдельно сигналами
            if 'logout' in path:
                action = 'logout'
                description = 'Выход из системы'
            elif any(k in path for k in ('delete',)):
                action = 'delete'
            elif any(k in path for k in ('new', 'create')):
                action = 'create'
            elif any(k in path for k in ('edit', 'update', 'post', 'build', 'replace',
                                         'generate', 'clear', 'publish')):
                action = 'update'
            else:
                action = 'update'
            description = description or f'{request.method} {path}'
        elif 'export' in path or 'download' in path or 'print' in path:
            action = 'export'
            description = f'Экспорт/печать: {path}'
        elif request.method == 'GET' and path.startswith('/accounts/users/'):
            action = 'view'
            description = f'Просмотр: {path}'

        if not action:
            return

        from .models import AuditLog
        AuditLog.objects.create(
            user=user,
            username=(user.username if user else ''),
            action=action,
            description=description[:500],
            path=path[:500],
            method=request.method,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        )
        if action in ('access_denied',):
            logger.warning('Отказ в доступе: %s %s (пользователь: %s, IP: %s)',
                           request.method, path,
                           user.username if user else 'аноним', get_client_ip(request))
