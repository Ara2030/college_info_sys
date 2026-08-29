# -*- coding: utf-8 -*-
"""Формы модуля «Кадровый учёт» (2.5)."""
from django import forms

from .models import Employee, HROrder, StaffPosition, TarificationPeriod, TarificationItem


class EmployeeForm(forms.ModelForm):
    """Личная карточка сотрудника (форма Т-2)."""

    class Meta:
        model = Employee
        fields = ('last_name', 'first_name', 'middle_name', 'gender', 'birth_date',
                  'birth_place', 'citizenship', 'snils', 'inn',
                  'passport_series', 'passport_number', 'passport_issued', 'passport_date',
                  'category', 'position', 'department', 'status',
                  'hire_date', 'dismissal_date', 'dismissal_reason',
                  'education', 'phone', 'email', 'address',
                  'family_status', 'children_count', 'military', 'note')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'passport_date': forms.DateInput(attrs={'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'dismissal_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }


class StaffPositionForm(forms.ModelForm):
    """Должность в штатном расписании."""

    class Meta:
        model = StaffPosition
        fields = ('title', 'department', 'rate_count', 'salary')
        widgets = {
            'rate_count': forms.NumberInput(attrs={'step': '0.5', 'min': '0.5'}),
            'salary': forms.NumberInput(attrs={'step': '100'}),
        }


class TarificationPeriodForm(forms.ModelForm):
    """Период тарификации + импорт из учебного плана."""

    import_from_plan = forms.BooleanField(
        label='Автоматически заполнить из учебного плана', required=False,
        help_text='Создаст строки тарификации по пунктам учебного плана '
                  '(группа + дисциплина + преподаватель + часы).',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = TarificationPeriod
        fields = ('name', 'year_start')
        widgets = {
            'year_start': forms.NumberInput(attrs={'min': 2020, 'max': 2100}),
        }


class TarificationItemForm(forms.ModelForm):
    class Meta:
        model = TarificationItem
        fields = ('employee', 'subject', 'hours_per_week', 'total_hours', 'groups')
        widgets = {
            'hours_per_week': forms.NumberInput(attrs={'step': '0.5'}),
            'total_hours': forms.NumberInput(),
        }


class HROrderForm(forms.ModelForm):
    """Приказ по личному составу."""

    class Meta:
        model = HROrder
        fields = ('number', 'date', 'order_type', 'employee', 'position', 'basis', 'text')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'text': forms.Textarea(attrs={'rows': 3}),
        }
