# -*- coding: utf-8 -*-
"""
Модуль «Формирование расписания» (2.4).

Модели:
  Room                — аудитории (доступность, вместимость, тип)
  Teacher             — преподаватели
  Curriculum          — учебный план: группа + дисциплина + преподаватель + часы
  TeacherUnavailable  — ограничения времени работы преподавателя
  ScheduleEntry       — занятие в расписании (день, пара, неделя, семестр)

Ограничения и конфликты:
  - одновременное занятие аудитории в двух группах;
  - одновременное занятие преподавателя в двух группах;
  - занятие группы в то же время, что и другое занятие группы;
  - недоступность преподавателя (TeacherUnavailable).
Проверки в services.check_entry_conflicts, автопостроение — services.auto_build.
"""
from django.db import models

from contingent.models import Group
from journal.models import Subject

# Дни недели (1 — понедельник ... 6 — суббота)
DAY_CHOICES = [
    (1, 'Понедельник'), (2, 'Вторник'), (3, 'Среда'),
    (4, 'Четверг'), (5, 'Пятница'), (6, 'Суббота'),
]

# Время пар (фиксированное расписание звонков)
SLOT_TIMES = {
    1: '08:30 – 10:00',
    2: '10:10 – 11:40',
    3: '12:10 – 13:40',
    4: '14:00 – 15:30',
    5: '15:40 – 17:10',
    6: '17:20 – 18:50',
}

WEEK_TYPE_CHOICES = [
    ('every', 'Каждую неделю'),
    ('odd', 'Нечётная неделя'),
    ('even', 'Чётная неделя'),
]


class Room(models.Model):
    """Аудитория: номер, корпус, вместимость, тип, доступность."""
    class Type(models.TextChoices):
        LECTURE = 'lecture', 'Кабинет'
        LAB = 'lab', 'Лаборатория'
        COMPUTER = 'computer', 'Компьютерный класс'

    name = models.CharField('Номер аудитории', max_length=20, unique=True)
    building = models.CharField('Корпус', max_length=50, blank=True)
    capacity = models.PositiveSmallIntegerField('Вместимость', default=30)
    room_type = models.CharField('Тип', max_length=20, choices=Type.choices,
                                 default=Type.LECTURE)
    is_available = models.BooleanField('Доступна', default=True)

    class Meta:
        verbose_name = 'Аудитория'
        verbose_name_plural = 'Аудитории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Teacher(models.Model):
    """Преподаватель."""
    last_name = models.CharField('Фамилия', max_length=100)
    first_name = models.CharField('Имя', max_length=100)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    position = models.CharField('Должность', max_length=150, blank=True)
    department = models.CharField('Отделение/кафедра', max_length=150, blank=True)
    email = models.EmailField('E-mail', blank=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.short_name

    @property
    def short_name(self):
        parts = [self.last_name]
        if self.first_name:
            parts.append(self.first_name[0] + '.')
        if self.middle_name:
            parts.append(self.middle_name[0] + '.')
        return ' '.join(parts)

    @property
    def full_name(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()


class Curriculum(models.Model):
    """Учебный план: дисциплина группы, распределённая по преподавателю."""
    class ExamType(models.TextChoices):
        EXAM = 'exam', 'Экзамен'
        CREDIT = 'credit', 'Зачёт'

    group = models.ForeignKey(
        Group, on_delete=models.PROTECT, related_name='curriculum',
        verbose_name='Группа'
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='curriculum',
        verbose_name='Дисциплина'
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.PROTECT, related_name='curriculum',
        verbose_name='Преподаватель'
    )
    hours_per_week = models.PositiveSmallIntegerField('Часов в неделю', default=2)
    semester = models.PositiveSmallIntegerField('Семестр', default=1)
    exam_type = models.CharField(
        'Вид отчётности', max_length=10, choices=ExamType.choices,
        default=ExamType.CREDIT
    )

    class Meta:
        verbose_name = 'Пункт учебного плана'
        verbose_name_plural = 'Учебный план'
        ordering = ['group__name', 'subject__name']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'subject', 'semester'],
                name='uniq_curriculum_group_subject_semester'),
        ]

    def __str__(self):
        return f'{self.group.name} · {self.subject.name} ({self.hours_per_week} ч/нед)'


class TeacherUnavailable(models.Model):
    """Ограничение времени работы преподавателя: слот, когда он не может вести."""
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name='unavailable',
        verbose_name='Преподаватель'
    )
    day_of_week = models.PositiveSmallIntegerField('День недели', choices=DAY_CHOICES)
    lesson_number = models.PositiveSmallIntegerField('Номер пары')
    semester = models.PositiveSmallIntegerField('Семестр', default=1)
    comment = models.CharField('Причина', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Недоступность преподавателя'
        verbose_name_plural = 'Недоступность преподавателей'
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'day_of_week', 'lesson_number', 'semester'],
                name='uniq_teacher_unavailable'),
        ]

    def __str__(self):
        return f'{self.teacher.short_name} — {self.get_day_of_week_display()}, пара {self.lesson_number}'


class ScheduleEntry(models.Model):
    """Занятие в расписании (одна ячейка сетки)."""
    group = models.ForeignKey(
        Group, on_delete=models.PROTECT, related_name='schedule_entries',
        verbose_name='Группа'
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='schedule_entries',
        verbose_name='Дисциплина'
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.PROTECT, related_name='schedule_entries',
        verbose_name='Преподаватель'
    )
    room = models.ForeignKey(
        Room, on_delete=models.PROTECT, related_name='schedule_entries',
        verbose_name='Аудитория'
    )
    day_of_week = models.PositiveSmallIntegerField('День недели', choices=DAY_CHOICES)
    lesson_number = models.PositiveSmallIntegerField('Номер пары')
    week_type = models.CharField(
        'Неделя', max_length=5, choices=WEEK_TYPE_CHOICES, default='every'
    )
    semester = models.PositiveSmallIntegerField('Семестр', default=1)
    is_published = models.BooleanField('Опубликовано', default=False)
    comment = models.CharField('Комментарий', max_length=300, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Занятие в расписании'
        verbose_name_plural = 'Занятия в расписании'
        ordering = ['day_of_week', 'lesson_number', 'group__name']
        indexes = [
            models.Index(fields=['group', 'semester']),
            models.Index(fields=['teacher', 'semester']),
            models.Index(fields=['room', 'semester']),
        ]

    def __str__(self):
        return (f'{self.get_day_of_week_display()} {self.lesson_number} пара · '
                f'{self.group.name} · {self.subject.name}')

    @property
    def slot_time(self):
        return SLOT_TIMES.get(self.lesson_number, '')

    @property
    def day_name(self):
        return dict(DAY_CHOICES).get(self.day_of_week, '')
