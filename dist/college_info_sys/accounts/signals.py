# -*- coding: utf-8 -*-
"""Сигналы аутентификации: журналирование входов и попыток входа."""
import logging

from django.contrib.auth.signals import (user_logged_in, user_logged_out,
                                         user_login_failed)
from django.dispatch import receiver

from .middleware import get_client_ip

logger = logging.getLogger('college.security')


def _meta(request, attr, default=''):
    """Безопасное извлечение метаданных запроса (request может быть None)."""
    if request is None:
        return default
    return getattr(request, attr, default) or default


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    from .models import AuditLog, LoginAttempt
    ip = get_client_ip(request) if request is not None else None
    ua = _meta(request, 'META', {})
    ua = (ua.get('HTTP_USER_AGENT', '') if isinstance(ua, dict) else '')[:300]
    try:
        LoginAttempt.objects.create(username=user.username, ip_address=ip,
                                    user_agent=ua, success=True)
        AuditLog.objects.create(
            user=user, username=user.username, action=AuditLog.Action.LOGIN,
            description='Успешный вход в систему', ip_address=ip, user_agent=ua,
            path=_meta(request, 'path')[:500], method=_meta(request, 'method', 'POST'))
    except Exception:  # noqa: BLE001 — аудит не должен ломать вход
        logger.exception('Ошибка журналирования входа')
    logger.info('Вход: %s (IP: %s)', user.username, ip)


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request=None, **kwargs):
    from .models import AuditLog, LoginAttempt
    username = (credentials or {}).get('username', '')
    ip = get_client_ip(request) if request is not None else None
    ua = _meta(request, 'META', {})
    ua = (ua.get('HTTP_USER_AGENT', '') if isinstance(ua, dict) else '')[:300]
    try:
        LoginAttempt.objects.create(username=username, ip_address=ip,
                                    user_agent=ua, success=False)
        AuditLog.objects.create(
            username=username, action=AuditLog.Action.LOGIN_FAILED,
            description='Неудачная попытка входа', ip_address=ip, user_agent=ua,
            path=_meta(request, 'path')[:500], method=_meta(request, 'method', 'POST'))
    except Exception:  # noqa: BLE001
        logger.exception('Ошибка журналирования неудачного входа')
    logger.warning('Неудачная попытка входа: %s (IP: %s)', username, ip)


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if not user:
        return
    from .models import AuditLog
    try:
        AuditLog.objects.create(
            user=user, username=user.username, action=AuditLog.Action.LOGOUT,
            description='Выход из системы',
            ip_address=get_client_ip(request) if request is not None else None,
            path=_meta(request, 'path')[:500], method=_meta(request, 'method', 'POST'))
    except Exception:  # noqa: BLE001
        logger.exception('Ошибка журналирования выхода')
    logger.info('Выход: %s', user.username)
