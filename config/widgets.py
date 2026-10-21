# -*- coding: utf-8 -*-
"""Общие виджеты форм.

Проблема: при LANGUAGE_CODE='ru-ru' Django рендерит дату в виджете как
«27.11.2008», а браузер понимает только ISO-формат «2008-11-27» внутри
<input type="date">. Невалидное значение браузер считает пустым полем:
обязательное поле блокирует отправку формы (кнопка «Сохранить» молчит),
а необязательное — молча очищается при сохранении.
"""
from django import forms


class DateInput(forms.DateInput):
    """Поле выбора даты <input type="date"> со значением в формате ISO."""
    input_type = 'date'

    def __init__(self, attrs=None, format=None):
        attrs = dict(attrs or {})
        attrs.setdefault('type', 'date')
        super().__init__(attrs=attrs, format=format or '%Y-%m-%d')


class TimeInput(forms.TimeInput):
    """Поле выбора времени <input type="time"> со значением в формате HH:MM."""
    input_type = 'time'

    def __init__(self, attrs=None, format=None):
        attrs = dict(attrs or {})
        attrs.setdefault('type', 'time')
        super().__init__(attrs=attrs, format=format or '%H:%M')
