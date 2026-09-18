# -*- coding: utf-8 -*-
"""
Шаблонные фильтры защиты персональных данных.

  mask_snils   — маскирует СНИЛС: «123-456-789 01» → «***-***-789 01»
  mask_passport — маскирует паспорт: «45 07», «123456» → «** **», «****56»
  mask_tail    — маскирует значение, оставляя последние N символов
"""
from django import template
from django.conf import settings

register = template.Library()


def _masking_enabled():
    return getattr(settings, 'MASK_SENSITIVE_DATA', True)


@register.filter
def mask_snils(value):
    """СНИЛС: скрывает первые две группы цифр."""
    if not value or not _masking_enabled():
        return value
    text = str(value)
    parts = text.split()
    if len(parts) == 2 and parts[0].count('-') == 2:
        return f'***-***-{parts[0].split("-")[-1]} {parts[1]}'
    return text


@register.filter
def mask_tail(value, visible=2):
    """Оставляет видимыми последние N символов."""
    if not value or not _masking_enabled():
        return value
    text = str(value)
    visible = int(visible)
    if len(text) <= visible:
        return '*' * len(text)
    return '*' * (len(text) - visible) + text[-visible:]


@register.filter
def mask_passport(value):
    """Паспорт: серия и номер маскируются, видны последние 2 цифры."""
    if not value or not _masking_enabled():
        return value
    text = str(value).strip()
    return mask_tail(text, 2)
