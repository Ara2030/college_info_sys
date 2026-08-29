# -*- coding: utf-8 -*-
"""
Модуль «Кадровый учёт» (2.5).

Модели:
  Employee          — личная карточка сотрудника (форма Т-2)
  StaffPosition     — должность в штатном расписании
  StaffingUnit      — единица штатного расписания (ставка + сотрудник)
  TarificationPeriod / TarificationItem — тарификация педагогической нагрузки
  HROrder           — приказ по личному составу (приём, перевод, увольнение)
  SalaryExport      — выгрузка в «1С:Зарплата» (нагрузка для расчёта ЗП)
"""
from django.db import models

from contingent.models import Group
from journal.models import Subject
from schedule.models import Teacher


class Employee(models.Model):
    """Личная карточка сотрудника (форма Т-2)."""
    class Category(models.TextChoices):
        TEACHER = 'teacher', 'Педагогический работник'
        MANAGEMENT = 'management', 'АУП (руководство)'
        SUPPORT = 'support', 'Вспомогательный персонал'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Работает'
        DISMISSED = 'dismissed', 'Уволен'

    class Gender(models.TextChoices):
        M = 'М', 'Мужской'
        F = 'Ж', 'Женский'

    # Общие сведения (раздел I формы Т-2)
    last_name = models.CharField('Фамилия', max_length=100)
    first_name = models.CharField('Имя', max_length=100)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    gender = models.CharField('Пол', max_length=1, choices=Gender.choices, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    birth_place = models.CharField('Место рождения', max_length=200, blank=True)
    citizenship = models.CharField('Гражданство', max_length=100, default='Россия')

    # Документы
    snils = models.CharField('СНИЛС', max_length=14, blank=True)
    inn = models.CharField('ИНН', max_length=12, blank=True)
    passport_series = models.CharField('Паспорт: серия', max_length=10, blank=True)
    passport_number = models.CharField('Паспорт: номер', max_length=20, blank=True)
    passport_issued = models.CharField('Паспорт: кем выдан', max_length=300, blank=True)
    passport_date = models.DateField('Паспорт: дата выдачи', null=True, blank=True)

    # Кадровые данные
    category = models.CharField(
        'Категория', max_length=15, choices=Category.choices, default=Category.SUPPORT)
    position = models.CharField('Должность', max_length=200)
    department = models.CharField('Отделение / подразделение', max_length=200, blank=True)
    status = models.CharField(
        'Статус', max_length=10, choices=Status.choices, default=Status.ACTIVE)
    hire_date = models.DateField('Дата приёма на работу', null=True, blank=True)
    dismissal_date = models.DateField('Дата увольнения', null=True, blank=True)
    dismissal_reason = models.CharField('Основание увольнения', max_length=300, blank=True)

    # Образование, контакты, адрес
    education = models.CharField('Образование', max_length=200, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    email = models.EmailField('E-mail', blank=True)
    address = models.CharField('Адрес', max_length=300, blank=True)
    family_status = models.CharField('Семейное положение', max_length=100, blank=True)
    children_count = models.PositiveSmallIntegerField('Детей', default=0)
    military = models.CharField('Воинский учёт', max_length=100, blank=True)

    # Связь с модулем расписания (для тарификации)
    teacher = models.OneToOneField(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='employee', verbose_name='Профиль преподавателя (расписание)')

    note = models.TextField('Примечание', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
        ordering = ['last_name', 'first_name', 'middle_name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()

    @property
    def short_name(self):
        parts = [self.last_name]
        if self.first_name:
            parts.append(self.first_name[0] + '.')
        if self.middle_name:
            parts.append(self.middle_name[0] + '.')
        return ' '.join(parts)


class StaffPosition(models.Model):
    """Должность в штатном расписании."""
    title = models.CharField('Наименование должности', max_length=200)
    department = models.CharField('Отделение / подразделение', max_length=200, blank=True)
    rate_count = models.DecimalField(
        'Количество ставок', max_digits=4, decimal_places=1, default=1)
    salary = models.DecimalField('Оклад (руб.)', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Должность (штатное расписание)'
        verbose_name_plural = 'Штатное расписание'
        ordering = ['title']

    def __str__(self):
        return f'{self.title} ({self.rate_count} ст.)'

    @property
    def filled_rate(self):
        """Занято ставок сотрудниками."""
        return sum(u.rate for u in self.units.all())

    @property
    def vacancy_rate(self):
        return max(0, self.rate_count - self.filled_rate)


class StaffingUnit(models.Model):
    """Единица штатного расписания: ставка, занятая сотрудником (или вакансия)."""
    position = models.ForeignKey(
        StaffPosition, on_delete=models.CASCADE, related_name='units',
        verbose_name='Должность')
    employee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='staffing_units', verbose_name='Сотрудник')
    rate = models.DecimalField('Ставка', max_digits=3, decimal_places=2, default=1)
    date_from = models.DateField('Назначен с', null=True, blank=True)
    note = models.CharField('Примечание', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Единица штатного расписания'
        verbose_name_plural = 'Единицы штатного расписания'
        ordering = ['position__title']

    def __str__(self):
        who = self.employee.full_name if self.employee else 'Вакансия'
        return f'{self.position.title} — {who} ({self.rate})'

    @property
    def is_vacancy(self):
        return self.employee is None


class TarificationPeriod(models.Model):
    """Период тарификации педагогической нагрузки (учебный год)."""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        APPROVED = 'approved', 'Утверждена'

    name = models.CharField('Наименование', max_length=200)
    year_start = models.PositiveSmallIntegerField('Учебный год (начало)')
    status = models.CharField(
        'Статус', max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Период тарификации'
        verbose_name_plural = 'Тарификация'
        ordering = ['-year_start']

    def __str__(self):
        return self.name

    @property
    def total_hours(self):
        return sum(i.total_hours for i in self.items.all())


class TarificationItem(models.Model):
    """Строка тарификации: педагог + дисциплина + часы."""
    period = models.ForeignKey(
        TarificationPeriod, on_delete=models.CASCADE, related_name='items',
        verbose_name='Период')
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='tarification',
        verbose_name='Преподаватель')
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name='tarification',
        verbose_name='Дисциплина')
    hours_per_week = models.DecimalField(
        'Часов в неделю', max_digits=4, decimal_places=1, default=0)
    total_hours = models.PositiveIntegerField('Часов в год', default=0)
    groups = models.CharField('Группы', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Строка тарификации'
        verbose_name_plural = 'Строки тарификации'
        ordering = ['employee__last_name', 'subject__name']
        constraints = [
            models.UniqueConstraint(
                fields=['period', 'employee', 'subject'],
                name='uniq_tarification_period_employee_subject'),
        ]

    def __str__(self):
        return f'{self.employee.short_name} — {self.subject.name} ({self.total_hours} ч)'


class HROrder(models.Model):
    """Приказ по личному составу: приём, перевод, увольнение."""
    class Type(models.TextChoices):
        HIRE = 'hire', 'Приём на работу'
        TRANSFER = 'transfer', 'Перевод'
        DISMISS = 'dismiss', 'Увольнение'

    number = models.CharField('Номер приказа', max_length=30)
    date = models.DateField('Дата приказа')
    order_type = models.CharField(
        'Тип', max_length=10, choices=Type.choices, default=Type.HIRE)
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='hr_orders',
        verbose_name='Сотрудник')
    position = models.CharField('Должность (по приказу)', max_length=200, blank=True)
    basis = models.CharField('Основание', max_length=300, blank=True)
    text = models.TextField('Текст приказа', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Приказ по личному составу'
        verbose_name_plural = 'Приказы по личному составу'
        ordering = ['-date', '-id']
        constraints = [
            models.UniqueConstraint(fields=['number', 'date'], name='uniq_hr_order_number_date'),
        ]

    def __str__(self):
        return f'Приказ №{self.number} от {self.date:%d.%m.%Y} ({self.get_order_type_display()})'


class SalaryExport(models.Model):
    """Выгрузка в «1С:Зарплата»: данные о нагрузке для расчёта ЗП."""
    class Status(models.TextChoices):
        READY = 'ready', 'Готов к передаче'
        SENT = 'sent', 'Передан в 1С'
        ERROR = 'error', 'Ошибка'

    tarification = models.ForeignKey(
        TarificationPeriod, on_delete=models.CASCADE, related_name='salary_exports',
        verbose_name='Период тарификации')
    created_at = models.DateTimeField('Дата формирования', auto_now_add=True)
    file_name = models.CharField('Имя файла', max_length=255)
    json_file = models.FileField('JSON-файл', upload_to='salary_exports/%Y/%m/')
    checksum = models.CharField('Контрольная сумма SHA-256', max_length=64, blank=True)
    status = models.CharField(
        'Статус', max_length=10, choices=Status.choices, default=Status.READY)
    employee_count = models.PositiveIntegerField('Сотрудников', default=0)
    total_hours = models.PositiveIntegerField('Часов всего', default=0)
    comment = models.TextField('Комментарий', blank=True)

    class Meta:
        verbose_name = 'Выгрузка в 1С:Зарплата'
        verbose_name_plural = 'Выгрузки в 1С:Зарплата'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.file_name} ({self.created_at:%d.%m.%Y %H:%M})'
