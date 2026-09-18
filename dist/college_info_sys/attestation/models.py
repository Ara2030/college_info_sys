# -*- coding: utf-8 -*-
"""
Модуль «Промежуточная аттестация» (2.3).

Модели:
  Exam             — экзамен / зачёт (элемент расписания аттестации)
  ExamResult       — результат аттестации студента (ведомость)
  AcademicDebt     — академическая задолженность
  ScholarshipPeriod — период расчёта стипендии и список студентов

Ограничения расписания (ТЗ):
  - не более одного экзамена в день для группы;
  - интервал не менее 3 дней между экзаменами одной группы.
Проверки реализованы в forms/views и сервисе services.schedule.
"""
from django.db import models

from contingent.models import Group, Student, Order, OrderItem
from journal.models import Subject


class ExamType(models.TextChoices):
    EXAM = 'exam', 'Экзамен'
    CREDIT = 'credit', 'Зачёт'


class Exam(models.Model):
    """Экзамен или зачёт по дисциплине для группы."""
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='exams',
        verbose_name='Дисциплина'
    )
    group = models.ForeignKey(
        Group, on_delete=models.PROTECT, related_name='exams',
        verbose_name='Группа'
    )
    exam_type = models.CharField(
        'Вид аттестации', max_length=10, choices=ExamType.choices,
        default=ExamType.EXAM
    )
    date = models.DateField('Дата')
    time = models.TimeField('Время', null=True, blank=True)
    room = models.CharField('Аудитория', max_length=30, blank=True)
    teacher = models.CharField('Преподаватель', max_length=150, blank=True)
    form = models.CharField('Форма проведения', max_length=100, blank=True,
                            default='Билеты')
    note = models.CharField('Примечание', max_length=300, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Экзамен / зачёт'
        verbose_name_plural = 'Экзамены и зачёты'
        ordering = ['date', 'time', 'group__name']
        indexes = [
            models.Index(fields=['group', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        kind = self.get_exam_type_display()
        return f'{self.group.name} · {self.subject.name} ({kind}) · {self.date:%d.%m.%Y}'

    @property
    def is_exam(self):
        return self.exam_type == ExamType.EXAM

    @property
    def results_count(self):
        return self.results.count()

    @property
    def fail_count(self):
        return self.results.filter(grade__in=('2', 'fail')).count()


class ExamResult(models.Model):
    """Результат аттестации студента (строка ведомости)."""
    GRADE_CHOICES = [
        ('5', '5 (отлично)'),
        ('4', '4 (хорошо)'),
        ('3', '3 (удовлетворительно)'),
        ('2', '2 (неудовлетворительно)'),
        ('pass', 'Зачтено'),
        ('fail', 'Не зачтено'),
    ]

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='results',
        verbose_name='Экзамен'
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='exam_results',
        verbose_name='Студент'
    )
    grade = models.CharField('Результат', max_length=4, choices=GRADE_CHOICES, blank=True)
    present = models.BooleanField('Явился', default=True)
    comment = models.CharField('Примечание', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Результат аттестации'
        verbose_name_plural = 'Результаты аттестации'
        ordering = ['student__last_name', 'student__first_name']
        constraints = [
            models.UniqueConstraint(fields=['exam', 'student'], name='uniq_result_exam_student'),
        ]

    def __str__(self):
        return f'{self.student.short_name}: {self.get_grade_display() or "—"}'

    @property
    def is_fail(self):
        """Признак неудовлетворительного результата / неявки."""
        return self.grade in ('2', 'fail') or (not self.present)


class AcademicDebt(models.Model):
    """Академическая задолженность студента по дисциплине."""
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активна'
        CLEARED = 'cleared', 'Ликвидирована'

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='academic_debts',
        verbose_name='Студент'
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='academic_debts',
        verbose_name='Дисциплина'
    )
    exam = models.ForeignKey(
        Exam, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='debts', verbose_name='Экзамен'
    )
    status = models.CharField(
        'Статус', max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    deadline = models.DateField('Срок ликвидации', null=True, blank=True)
    created_at = models.DateField('Дата возникновения', auto_now_add=True)
    cleared_at = models.DateField('Дата ликвидации', null=True, blank=True)
    comment = models.CharField('Комментарий', max_length=300, blank=True)

    class Meta:
        verbose_name = 'Академическая задолженность'
        verbose_name_plural = 'Академические задолженности'
        ordering = ['-created_at', 'student__last_name']

    def __str__(self):
        return f'{self.student.short_name} — {self.subject.name} ({self.get_status_display()})'


class ScholarshipPeriod(models.Model):
    """Период расчёта стипендии и список студентов, имеющих право."""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        APPROVED = 'approved', 'Утверждён'

    name = models.CharField('Наименование', max_length=200)
    period_start = models.DateField('Период с')
    period_end = models.DateField('Период по')
    students = models.ManyToManyField(
        Student, blank=True, related_name='scholarship_periods',
        verbose_name='Студенты (имеют право на стипендию)'
    )
    status = models.CharField(
        'Статус', max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Стипендиальный период'
        verbose_name_plural = 'Стипендиальные периоды'
        ordering = ['-period_start']

    def __str__(self):
        return self.name

    @property
    def students_count(self):
        return self.students.count()
