# -*- coding: utf-8 -*-
"""Админ-панель модуля «Авторизация и роли»."""
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student', 'employee', 'parent_of')
    search_fields = ('user__username',)
    autocomplete_fields = ('user',)


# Расширяем админку групп: показываем коды ролей и русские названия
admin.site.unregister(Group)


class GroupAdmin(BaseGroupAdmin):
    list_display = ('name',)
    search_fields = ('name',)


admin.site.register(Group, GroupAdmin)
