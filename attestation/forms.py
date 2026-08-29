# -*- coding: utf-8 -*-
"""Формы модуля «Промежуточная аттестация» (2.3)."""
from django import forms

from contingent.models import Student
from .models import Exam, ExamResult
from .services import validate_exam_date


class ExamForm(forms.ModelForm):
    """Экзамен / зачёт с проверкой ограничений расписания."""

    class Meta:
        model = Exam
        fields = ('subject', 'group', 'exam_type', 'date', 'time', 'room',
                  'teacher', 'form', 'note')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'room': forms.TextInput(attrs={'placeholder': 'Аудитория'}),
            'teacher': forms.TextInput(attrs={'placeholder': 'Фамилия И.О.'}),
            'note': forms.TextInput(attrs={'placeholder': 'Примечание'}),
        }

    def clean(self):
        cleaned = super().clean()
        group = cleaned.get('group')
        day = cleaned.get('date')
        exam_type = cleaned.get('exam_type')
        if group and day:
            errors = validate_exam_date(group, day, exam_type,
                                        exclude=self.instance if self.instance.pk else None)
            for err in errors:
                self.add_error('date', err)
        return cleaned


class ExamResultForm(forms.ModelForm):
    """Строка ведомости: студент + результат + явка."""

    student_name = forms.CharField(label='Студент', required=False, disabled=True)

    class Meta:
        model = ExamResult
        fields = ('student', 'grade', 'present')
        widgets = {
            'student': forms.HiddenInput(),
            'grade': forms.Select(choices=ExamResult.GRADE_CHOICES,
                                  attrs={'class': 'form-select form-select-sm'}),
            'present': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.student_id:
            self.fields['student_name'].initial = self.instance.student.short_name


def exam_result_formset_factory(students):
    from django.forms import formset_factory
    initial = [{'student': s.pk, 'student_name': s.short_name,
                'grade': '', 'present': True} for s in students]
    return formset_factory(ExamResultForm, extra=0, can_delete=False)(initial=initial)


class ScheduleBuildForm(forms.Form):
    """Автоматическое построение расписания: группа + дисциплины + дата старта."""

    group = forms.ModelChoiceField(
        queryset=None, label='Группа', widget=forms.Select(attrs={'class': 'form-select'}))
    subjects = forms.ModelMultipleChoiceField(
        queryset=None, label='Дисциплины',
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8}))
    exam_type = forms.ChoiceField(
        choices=[('exam', 'Экзамен'), ('credit', 'Зачёт')],
        label='Вид аттестации', initial='exam',
        widget=forms.Select(attrs={'class': 'form-select'}))
    start_date = forms.DateField(
        label='Дата начала', widget=forms.DateInput(attrs={'type': 'date'}))
    room = forms.CharField(label='Аудитория', required=False,
                           widget=forms.TextInput(attrs={'class': 'form-control'}))
    teacher = forms.CharField(label='Преподаватель', required=False,
                              widget=forms.TextInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from contingent.models import Group
        from journal.models import Subject
        self.fields['group'].queryset = Group.objects.order_by('name')
        self.fields['subjects'].queryset = Subject.objects.order_by('name')


class ScholarshipForm(forms.Form):
    """Формирование списка студентов на стипендию за период."""

    period_start = forms.DateField(
        label='Период с', widget=forms.DateInput(attrs={'type': 'date'}))
    period_end = forms.DateField(
        label='Период по', widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('period_start') and data.get('period_end') \
                and data['period_start'] > data['period_end']:
            self.add_error('period_end', 'Дата окончания раньше даты начала.')
        return data
