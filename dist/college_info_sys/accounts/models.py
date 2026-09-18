# -*- coding: utf-8 -*-
"""
Модели модуля «Авторизация и роли».

UserProfile — связь пользователя с объектами системы.
AuditLog    — журнал действий (аудит безопасности).
LoginAttempt — попытки входа (защита от перебора паролей).
"""
from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Профиль пользователя: связь с ролями и объектами системы."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='profile', verbose_name='Пользователь')

    student = models.OneToOneField(
        'contingent.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='user_profile', verbose_name='Студент (если пользователь — студент)')

    employee = models.OneToOneField(
        'hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='user_profile', verbose_name='Сотрудник (если пользователь — сотрудник)')

    parent_of = models.ForeignKey(
        'contingent.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='parent_profiles', verbose_name='Ребёнок (если пользователь — родитель)')

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return self.user.username

    @property
    def role_names(self):
        """Человекочитаемый список ролей пользователя."""
        from .roles import ROLE_LABELS
        names = [g.name for g in self.user.groups.all()]
        return [ROLE_LABELS.get(n, n) for n in names if n in ROLE_LABELS]


class AuditLog(models.Model):
    """Журнал действий пользователей (аудит безопасности)."""
    class Action(models.TextChoices):
        LOGIN = 'login', 'Вход в систему'
        LOGOUT = 'logout', 'Выход из системы'
        LOGIN_FAILED = 'login_failed', 'Неудачная попытка входа'
        LOCKOUT = 'lockout', 'Блокировка (превышены попытки входа)'
        CREATE = 'create', 'Создание'
        UPDATE = 'update', 'Изменение'
        DELETE = 'delete', 'Удаление'
        VIEW = 'view', 'Просмотр'
        EXPORT = 'export', 'Экспорт данных'
        ACCESS_DENIED = 'access_denied', 'Отказ в доступе'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs', verbose_name='Пользователь')
    username = models.CharField('Логин (как введён)', max_length=150, blank=True)
    action = models.CharField('Действие', max_length=20, choices=Action.choices)
    description = models.CharField('Описание', max_length=500, blank=True)
    object_type = models.CharField('Объект', max_length=100, blank=True)
    object_id = models.CharField('Идентификатор объекта', max_length=50, blank=True)
    path = models.CharField('URL', max_length=500, blank=True)
    method = models.CharField('Метод', max_length=10, blank=True)
    ip_address = models.GenericIPAddressField('IP-адрес', null=True, blank=True)
    user_agent = models.CharField('User-Agent', max_length=300, blank=True)
    created_at = models.DateTimeField('Время', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Запись журнала аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'{self.created_at:%d.%m.%Y %H:%M} {self.username or "—"} — {self.get_action_display()}'


class LoginAttempt(models.Model):
    """Попытка входа в систему (для защиты от перебора паролей)."""
    username = models.CharField('Логин', max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField('IP-адрес', null=True, blank=True)
    user_agent = models.CharField('User-Agent', max_length=300, blank=True)
    success = models.BooleanField('Успешно', default=False)
    created_at = models.DateTimeField('Время', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Попытка входа'
        verbose_name_plural = 'Попытки входа'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['username', 'created_at'])]

    def __str__(self):
        status = 'успешно' if self.success else 'неудача'
        return f'{self.created_at:%d.%m.%Y %H:%M} {self.username} — {status}'
