# -*- coding: utf-8 -*-
"""Формы модуля «Отчётность и интеграция» (2.6)."""
from django import forms

from .models import StatReport, SmevRequest


class StatReportForm(forms.Form):
    """Параметры формирования статистического отчёта."""

    report_type = forms.ChoiceField(
        choices=StatReport.Type.choices, label='Тип отчёта',
        widget=forms.Select(attrs={'class': 'form-select'}))
    period_year = forms.IntegerField(
        label='Отчётный год', initial=2026, min_value=2020, max_value=2100,
        widget=forms.NumberInput(attrs={'class': 'form-control'}))


class SmevRequestForm(forms.ModelForm):
    """Запрос сведений через СМЭВ."""

    class Meta:
        model = SmevRequest
        fields = ('registry', 'identifier', 'person_name')
        widgets = {
            'registry': forms.Select(attrs={'class': 'form-select'}),
            'identifier': forms.TextInput(attrs={'class': 'form-control'}),
            'person_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
