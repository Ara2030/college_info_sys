# -*- coding: utf-8 -*-
"""Шаблонные фильтры модуля расписания."""
from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """mapping.get(key) — доступ к элементу словаря по переменной."""
    try:
        return mapping.get(key)
    except AttributeError:
        return None
