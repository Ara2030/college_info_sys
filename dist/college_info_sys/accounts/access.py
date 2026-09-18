# -*- coding: utf-8 -*-
"""
Система разграничения доступа (модуль «Авторизация и роли»).

  has_role(user, roles)            — проверка роли пользователя
  RoleRequiredMixin                — миксин для class-based views
  role_required(*roles)            — декоратор для function-based views
"""
from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def has_role(user, roles):
    """True, если пользователь входит в одну из ролей (групп) или суперадмин."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def user_roles(user):
    """Множество кодов ролей пользователя."""
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {'admin'}
    return set(user.groups.values_list('name', flat=True))


class RoleRequiredMixin:
    """Миксин для class-based views: проверяет авторизацию и роль.

    Использование:
        class StudentCreateView(RoleRequiredMixin, CreateView):
            roles = CONTINGENT_EDIT
    """
    roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{settings.LOGIN_URL}?next={request.path}')
        if not has_role(request.user, self.roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def role_required(*roles):
    """Декоратор для function-based views."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not has_role(request.user, roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
