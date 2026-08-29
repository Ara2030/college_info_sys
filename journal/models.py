# -*- coding: utf-8 -*-
"""
Модуль «Электронный журнал» (2.2).
Модели: дисциплины, учебные занятия, оценки текущего контроля, посещаемость.

Расчётные показатели (средний балл, процент посещаемости, критерий
низкой успеваемости) вынесены в методы моделей и сервис journal/services.py.
"""
from django.core.exceptions import ValidationError
from django.db import models

from contingent.models import Group, Student

# Критерии низкой успеваемости (по ТЗ)
LOW_ATTENDANCE_PERCENT = 60.0   # менее 60% посещаемости
LOW_AVG_GRADE = 3.5             # средний балл ниже 3,5

GRADE_CHOICES = [
    ('5', '5'),
    ('4', '4'),
    ('3', '3'),
    ('2', '2'),
    ('n', 'н/а'),
]
NUMERIC_GRADES = {'5', '4', '3', '2'}


class Subject(models.Model):
    """Дисциплина учебного плана."""
    name = models.CharField('Название дисциплины', max_length=250)
    code = models.CharField('Код', max_length=30, blank=True)
    teacher = models.CharField('Преподаватель', max_length=150, blank=True)

    class Meta:
        verbose_name = 'Дисциплина'
        verbose_name_plural = 'Дисциплины'
        ordering = ['name']

    def __str__(self):
        return self.name


class Lesson(models.Model):
    """Учебное занятие (строка журнала): группа + дисциплина + дата."""
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='lessons',
        verbose_name='Дисциплина'
    )
    group = models.ForeignKey(
        Group, on_delete=models.PROTECT, related_name='lessons',
        verbose_name='Группа'
    )
    date = models.DateField('Дата занятия')
    lesson_number = models.PositiveSmallIntegerField('Номер пары', default=1)
    topic = models.CharField('Тема занятия', max_length=300, blank=True)
    teacher = models.CharField('Преподаватель', max_length=150, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Учебное занятие'
        verbose_name_plural = 'Учебные занятия'
        ordering = ['date', 'lesson_number', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['subject', 'group', 'date', 'lesson_number'],
                name='uniq_lesson_subject_group_date_num',
            ),
        ]

    def __str__(self):
        return f'{self.group.name} · {self.subject.name} · {self.date:%d.%m.%Y}'

    def clean(self):
        super().clean()
        if not (1 <= self.lesson_number <= 6):
            raise ValidationError({'lesson_number': 'Номер пары должен быть от 1 до 6.'})

    # ----- Расчётные показатели занятия -----

    @property
    def grades_count(self):
        """Сколько оценок выставлено за занятие."""
        return self.grades.exclude(value='').count()

    @property
    def present_count(self):
        return self.attendance.filter(present=True).count()

    @property
    def attendance_count(self):
        return self.attendance.count()


class Grade(models.Model):
    """Оценка текущего контроля: занятие + студент + значение."""
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name='grades',
        verbose_name='Занятие'
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='grades',
        verbose_name='Студент'
    )
    value = models.CharField('Оценка', max_length=2, choices=GRADE_CHOICES, blank=True)

    class Meta:
        verbose_name = 'Оценка'
        verbose_name_plural = 'Оценки'
        ordering = ['student__last_name', 'student__first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['lesson', 'student'], name='uniq_grade_lesson_student'
            ),
        ]

    def __str__(self):
        return f'{self.student.short_name}: {self.value or "—"}'

    @property
    def numeric_value(self):
        """Числовое значение оценки (None для «н/а» и пустой)."""
        return int(self.value) if self.value in NUMERIC_GRADES else None


class Attendance(models.Model):
    """Посещаемость: занятие + студент + факт присутствия."""
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name='attendance',
        verbose_name='Занятие'
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='attendance',
        verbose_name='Студент'
    )
    present = models.BooleanField('Присутствовал', default=True)

    class Meta:
        verbose_name = 'Посещаемость'
        verbose_name_plural = 'Посещаемость'
        constraints = [
            models.UniqueConstraint(
                fields=['lesson', 'student'], name='uniq_att_lesson_student'
            ),
        ]

    def __str__(self):
        return f'{self.student.short_name}: {"✓" if self.present else "—"}'
