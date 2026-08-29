# -*- coding: utf-8 -*-
"""Формы модуля «Формирование расписания» (2.4)."""
from django import forms

from .models import ScheduleEntry
from .services import check_entry_conflicts


class ScheduleEntryForm(forms.ModelForm):
    """Создание занятия с автоматической проверкой конфликтов."""

    class Meta:
        model = ScheduleEntry
        fields = ('group', 'subject', 'teacher', 'room', 'day_of_week',
                  'lesson_number', 'week_type', 'semester', 'is_published', 'comment')
        widgets = {
            'day_of_week': forms.Select(),
            'lesson_number': forms.Select(choices=[(i, f'{i} пара') for i in range(1, 7)]),
            'semester': forms.NumberInput(attrs={'min': 1}),
            'comment': forms.TextInput(),
        }

    def clean(self):
        cleaned = super().clean()
        # Проверяем конфликты на лету
        entry = ScheduleEntry(
            group=cleaned.get('group'),
            subject=cleaned.get('subject'),
            teacher=cleaned.get('teacher'),
            room=cleaned.get('room'),
            day_of_week=cleaned.get('day_of_week'),
            lesson_number=cleaned.get('lesson_number'),
            week_type=cleaned.get('week_type', 'every'),
            semester=cleaned.get('semester', 1),
        )
        if entry.group and entry.day_of_week and entry.lesson_number:
            errors = check_entry_conflicts(
                entry,
                exclude=self.instance if self.instance and self.instance.pk else None,
            )
            for err in errors:
                self.add_error(None, err)
        return cleaned


class ScheduleReplaceForm(forms.Form):
    """Оперативная корректировка: замена преподавателя и/или аудитории."""

    teacher = forms.ModelChoiceField(
        queryset=None, label='Преподаватель',
        widget=forms.Select(attrs={'class': 'form-select'}))
    room = forms.ModelChoiceField(
        queryset=None, label='Аудитория',
        widget=forms.Select(attrs={'class': 'form-select'}))
    comment = forms.CharField(
        label='Комментарий к замене', required=False, max_length=300,
        widget=forms.TextInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, entry=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry = entry
        from .models import Room, Teacher
        self.fields['teacher'].queryset = Teacher.objects.filter(is_active=True).order_by('last_name')
        self.fields['room'].queryset = Room.objects.filter(is_available=True).order_by('name')
        if entry:
            self.fields['teacher'].initial = entry.teacher_id
            self.fields['room'].initial = entry.room_id

    def clean(self):
        cleaned = super().clean()
        entry = self.entry
        if not entry:
            return cleaned
        # Временная копия занятия с новыми преподавателем и аудиторией
        from .models import ScheduleEntry
        trial = ScheduleEntry(
            group=entry.group, subject=entry.subject,
            teacher=cleaned.get('teacher'), room=cleaned.get('room'),
            day_of_week=entry.day_of_week, lesson_number=entry.lesson_number,
            week_type=entry.week_type, semester=entry.semester,
        )
        from .services import check_entry_conflicts
        for err in check_entry_conflicts(trial, exclude=entry):
            self.add_error(None, err)
        return cleaned


class ScheduleBuildForm(forms.Form):
    """Автопостроение расписания группы на семестр."""

    group = forms.ModelChoiceField(
        queryset=None, label='Группа',
        widget=forms.Select(attrs={'class': 'form-select'}))
    semester = forms.IntegerField(
        label='Семестр', initial=1, min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}))
    week_type = forms.ChoiceField(
        choices=[('every', 'Каждую неделю'), ('odd', 'Нечётная'), ('even', 'Чётная')],
        label='Тип недели', initial='every',
        widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from contingent.models import Group
        self.fields['group'].queryset = Group.objects.order_by('name')
