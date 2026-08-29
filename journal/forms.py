# -*- coding: utf-8 -*-
"""Формы модуля «Электронный журнал» (2.2)."""
from django import forms

from contingent.models import Student
from .models import Grade, Lesson


class LessonForm(forms.ModelForm):
    """Реквизиты занятия: дисциплина, группа, дата, пара, тема."""

    class Meta:
        model = Lesson
        fields = ('subject', 'group', 'date', 'lesson_number', 'topic', 'teacher')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'lesson_number': forms.NumberInput(attrs={'min': 1, 'max': 6}),
            'topic': forms.TextInput(attrs={'placeholder': 'Тема занятия'}),
            'teacher': forms.TextInput(attrs={'placeholder': 'Фамилия И.О.'}),
        }


class GradeForm(forms.ModelForm):
    """Одна строка журнала: студент + оценка + посещаемость."""

    student_name = forms.CharField(
        label='Студент', required=False, disabled=True, widget=forms.TextInput()
    )

    class Meta:
        model = Grade
        fields = ('student', 'value')
        widgets = {
            'student': forms.HiddenInput(),
            'value': forms.Select(choices=Grade._meta.get_field('value').choices,
                                  attrs={'class': 'form-select form-select-sm'}),
        }

    present = forms.BooleanField(
        label='Присутствовал', required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.student_id:
            self.fields['student_name'].initial = self.instance.student.short_name
            self.fields['present'].initial = True


def grade_formset_factory(students):
    """
    Формсет строк журнала для переданного списка студентов группы.
    Возвращает (formset, extra) — каждая строка содержит оценку и посещаемость.
    """
    from django.forms import formset_factory

    initial = []
    for student in students:
        initial.append({
            'student': student.pk,
            'student_name': student.short_name,
            'value': '',
            'present': True,
        })

    FormSet = formset_factory(
        GradeForm, extra=0, can_delete=False,
    )
    return FormSet(initial=initial)
