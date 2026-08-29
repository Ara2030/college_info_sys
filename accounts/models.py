# -*- coding: utf-8 -*-
"""
Модели модуля «Авторизация и роли».

UserProfile — связь пользователя с объектами системы:
  студент (student), сотрудник/преподаватель (employee),
  ребёнок для родителя (parent_of).
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
