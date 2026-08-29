# -*- coding: utf-8 -*-
"""
Модуль 2.1 «Контингент студентов».
Модели данных ИС колледжа (СПО).

12 таблиц:
  Department, Specialty, Group, Student, StudentDocument, ParentInfo,
  OrderType, Order, OrderItem, StudentStatusHistory, AcademicLeave,
  RegistryExport
"""

import re
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


# ==========================================================================
# Вспомогательные константы и валидаторы
# ==========================================================================

SNILS_REGEX = RegexValidator(
    regex=r'^\d{3}-\d{3}-\d{3} \d{2}$',
    message='СНИЛС должен иметь формат 000-000-000 00',
)


class StudentStatus(models.TextChoices):
    """Статусы обучающегося (текущее состояние контингента)."""
    STUDY = 'study', 'Обучается'
    ACADEMIC_LEAVE = 'academic_leave', 'Академический отпуск'
    EXPELLED = 'expelled', 'Отчислен'
    GRADUATED = 'graduated', 'Окончил обучение'


# ==========================================================================
# Справочники
# ==========================================================================

class Department(models.Model):
    """Отделение колледжа (всего 4)."""
    name = models.CharField('Название отделения', max_length=200)
    code = models.CharField('Код', max_length=20, unique=True, blank=True)
    head = models.CharField('Заведующий отделением', max_length=150, blank=True)

    class Meta:
        verbose_name = 'Отделение'
        verbose_name_plural = 'Отделения'
        ordering = ['name']

    def __str__(self):
        return self.name


class Specialty(models.Model):
    """Специальность СПО (8 специальностей, в т.ч. 09.02.05, 09.02.07, 13.02.03, 13.02.11)."""
    code = models.CharField('Код специальности', max_length=20, unique=True)  # 09.02.05
    name = models.CharField('Наименование', max_length=250)
    qualification = models.CharField('Квалификация', max_length=150, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='specialties',
        verbose_name='Отделение'
    )
    duration_months = models.PositiveSmallIntegerField('Срок обучения, мес.', default=46)

    class Meta:
        verbose_name = 'Специальность'
        verbose_name_plural = 'Специальности'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class Group(models.Model):
    """Учебная группа (всего 42)."""
    name = models.CharField('Название группы', max_length=20, unique=True)  # ИС-31
    specialty = models.ForeignKey(
        Specialty, on_delete=models.PROTECT, related_name='groups',
        verbose_name='Специальность'
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='groups',
        verbose_name='Отделение'
    )
    course = models.PositiveSmallIntegerField('Курс', default=1)
    enroll_year = models.PositiveSmallIntegerField('Год набора')
    curator = models.CharField('Куратор', max_length=150, blank=True)
    is_active = models.BooleanField('Действующая', default=True)

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
        ordering = ['name']

    def __str__(self):
        return self.name


# ==========================================================================
# Контингент студентов
# ==========================================================================

class Student(models.Model):
    """Личная карточка студента (контингент, 950 студентов)."""
    GENDER_CHOICES = [
        ('М', 'Мужской'),
        ('Ж', 'Женский'),
    ]

    last_name = models.CharField('Фамилия', max_length=100)
    first_name = models.CharField('Имя', max_length=100)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    birth_date = models.DateField('Дата рождения')
    gender = models.CharField('Пол', max_length=1, choices=GENDER_CHOICES, blank=True)
    snils = models.CharField('СНИЛС', max_length=14, unique=True, validators=[SNILS_REGEX])
    citizenship = models.CharField('Гражданство', max_length=100, default='Россия')

    group = models.ForeignKey(
        Group, on_delete=models.PROTECT, related_name='students',
        verbose_name='Группа'
    )
    specialty = models.ForeignKey(
        Specialty, on_delete=models.PROTECT, related_name='students',
        verbose_name='Специальность'
    )
    status = models.CharField(
        'Статус', max_length=20, choices=StudentStatus.choices,
        default=StudentStatus.STUDY, db_index=True
    )

    student_card_number = models.CharField('Номер личного дела', max_length=20, unique=True)
    enroll_date = models.DateField('Дата зачисления', null=True, blank=True)

    phone = models.CharField('Телефон', max_length=20, blank=True)
    email = models.EmailField('E-mail', blank=True)

    # Адрес (разбит по полям — удобно для выгрузки в Реестр СПО)
    address_index = models.CharField('Индекс', max_length=6, blank=True)
    address_city = models.CharField('Город', max_length=120, blank=True)
    address_street = models.CharField('Улица', max_length=150, blank=True)
    address_house = models.CharField('Дом', max_length=20, blank=True)
    address_flat = models.CharField('Квартира', max_length=10, blank=True)

    note = models.TextField('Примечание', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'
        ordering = ['last_name', 'first_name', 'middle_name']
        indexes = [
            models.Index(fields=['group']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()

    # ----- Вычисляемые свойства (используются в шаблонах и выгрузках) -----

    @property
    def full_name(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()

    @property
    def short_name(self):
        return f'{self.last_name} {self.first_name[:1]}. {self.middle_name[:1]}.'.strip()

    @property
    def age(self):
        """Возраст студента на текущую дату."""
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    @property
    def course(self):
        """Курс (1-4) с учётом учебного года, начинающегося 1 сентября."""
        if not self.enroll_date:
            return 1
        today = date.today()
        months = (today.year - self.enroll_date.year) * 12 + (today.month - self.enroll_date.month)
        return min(4, max(1, months // 12 + 1))

    @property
    def full_address(self):
        """Полный адрес одной строкой для Реестра СПО."""
        parts = [
            self.address_index,
            self.address_city,
            self.address_street,
            f'д. {self.address_house}' if self.address_house else '',
            f'кв. {self.address_flat}' if self.address_flat else '',
        ]
        return ', '.join(p for p in parts if p)

    @property
    def identity_document(self):
        """Основной документ, удостоверяющий личность (паспорт по умолчанию)."""
        return self.documents.filter(is_main=True).first() or self.documents.first()

    def clean(self):
        """Проверка: группа должна относиться к специальности студента."""
        super().clean()
        if self.group_id and self.specialty_id and self.group.specialty_id != self.specialty_id:
            raise ValidationError({
                'group': f'Группа {self.group.name} относится к специальности '
                         f'{self.group.specialty}, а указана специальность {self.specialty}.'
            })


class StudentDocument(models.Model):
    """Документы студента (паспорт, свидетельство о рождении и т.д.)."""
    DOC_TYPES = [
        ('passport', 'Паспорт'),
        ('birth_certificate', 'Свидетельство о рождении'),
        ('snils_cert', 'СНИЛС'),
        ('diploma', 'Аттестат / диплом'),
        ('other', 'Прочее'),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='documents',
        verbose_name='Студент'
    )
    doc_type = models.CharField('Тип документа', max_length=30, choices=DOC_TYPES, default='passport')
    series = models.CharField('Серия', max_length=20, blank=True)
    number = models.CharField('Номер', max_length=30)
    issue_date = models.DateField('Дата выдачи', null=True, blank=True)
    issued_by = models.CharField('Кем выдан', max_length=300, blank=True)
    issue_code = models.CharField('Код подразделения', max_length=20, blank=True)
    is_main = models.BooleanField('Основной документ', default=False)

    class Meta:
        verbose_name = 'Документ студента'
        verbose_name_plural = 'Документы студентов'
        ordering = ['-is_main', 'doc_type']

    def __str__(self):
        return f'{self.get_doc_type_display()} {self.series} {self.number}'


class ParentInfo(models.Model):
    """Сведения о родителях / законных представителях."""
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='parents',
        verbose_name='Студент'
    )
    last_name = models.CharField('Фамилия', max_length=100)
    first_name = models.CharField('Имя', max_length=100)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Родитель'
        verbose_name_plural = 'Родители'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()


# ==========================================================================
# Приказы и движение контингента
# ==========================================================================

class OrderType(models.Model):
    """Тип приказа (шаблон): зачисление, отчисление, перевод и т.д."""
    code = models.CharField('Код', max_length=30, unique=True)  # enroll, expel, ...
    name = models.CharField('Наименование', max_length=200)
    document_name = models.CharField('Название документа', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Тип приказа'
        verbose_name_plural = 'Типы приказов'
        ordering = ['name']

    def __str__(self):
        return self.name


class Order(models.Model):
    """Приказ по контингенту студентов."""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        POSTED = 'posted', 'Проведён'

    number = models.CharField('Номер приказа', max_length=30)
    date = models.DateField('Дата приказа')
    order_type = models.ForeignKey(
        OrderType, on_delete=models.PROTECT, related_name='orders',
        verbose_name='Тип приказа'
    )
    title = models.CharField('Заголовок', max_length=300, blank=True)
    status = models.CharField(
        'Статус', max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    comment = models.TextField('Комментарий', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='Автор'
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Приказ'
        verbose_name_plural = 'Приказы'
        ordering = ['-date', '-id']
        constraints = [
            models.UniqueConstraint(fields=['number', 'date'], name='uniq_order_number_date'),
        ]

    def __str__(self):
        return f'Приказ №{self.number} от {self.date:%d.%m.%Y}'

    @property
    def students_count(self):
        return self.items.count()


class OrderItem(models.Model):
    """Пункт приказа (одна строка = один студент + действие)."""
    ACTION_CHOICES = [
        ('enroll', 'Зачислить'),
        ('expel', 'Отчислить'),
        ('transfer', 'Перевести'),
        ('academic_leave', 'Академ. отпуск'),
        ('recover', 'Восстановить'),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items',
        verbose_name='Приказ'
    )
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name='order_items',
        verbose_name='Студент'
    )
    action = models.CharField('Действие', max_length=30, choices=ACTION_CHOICES)
    group_from = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='Из группы'
    )
    group_to = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='В группу'
    )
    basis = models.CharField('Основание', max_length=300, blank=True)  # заявление, приказ МОН и т.д.
    comment = models.CharField('Примечание', max_length=300, blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Пункт приказа'
        verbose_name_plural = 'Пункты приказа'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.get_action_display()}: {self.student.short_name}'


class StudentStatusHistory(models.Model):
    """Журнал движения контингента (история изменения статусов)."""
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='status_history',
        verbose_name='Студент'
    )
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='status_changes', verbose_name='Приказ'
    )
    status_from = models.CharField('Было', max_length=20, choices=StudentStatus.choices, blank=True)
    status_to = models.CharField('Стало', max_length=20, choices=StudentStatus.choices)
    date = models.DateField('Дата изменения', auto_now_add=True)
    comment = models.CharField('Комментарий', max_length=300, blank=True)

    class Meta:
        verbose_name = 'Запись движения контингента'
        verbose_name_plural = 'Движение контингента'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.student.short_name}: {self.get_status_from_display()} → {self.get_status_to_display()}'


class AcademicLeave(models.Model):
    """Академический отпуск студента."""
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='academic_leaves',
        verbose_name='Студент'
    )
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='academic_leaves', verbose_name='Приказ'
    )
    date_from = models.DateField('Начало')
    date_to = models.DateField('Окончание', null=True, blank=True)
    reason = models.CharField('Причина', max_length=300, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    comment = models.CharField('Комментарий', max_length=300, blank=True)

    class Meta:
        verbose_name = 'Академический отпуск'
        verbose_name_plural = 'Академические отпуска'
        ordering = ['-date_from']

    def __str__(self):
        return f'{self.student.short_name}: {self.date_from:%d.%m.%Y} — {self.date_to:%d.%m.%Y}'


# ==========================================================================
# Выгрузка в Реестр СПО
# ==========================================================================

class RegistryExport(models.Model):
    """Журнал выгрузок контингента в Реестр СПО (XML)."""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Сформирован'
        READY = 'ready', 'Готов к отправке'
        SENT = 'sent', 'Отправлен'
        ERROR = 'error', 'Ошибка валидации'

    created_at = models.DateTimeField('Дата формирования', auto_now_add=True)
    period_start = models.DateField('Период с')
    period_end = models.DateField('Период по')
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exports', verbose_name='Группа'
    )
    student_status = models.CharField('Статус студентов', max_length=30, blank=True)

    student_count = models.PositiveIntegerField('Студентов в выгрузке', default=0)
    order_count = models.PositiveIntegerField('Приказов в выгрузке', default=0)

    file_name = models.CharField('Имя файла', max_length=255)
    xml_file = models.FileField('XML-файл', upload_to='registry_exports/%Y/%m/')
    checksum = models.CharField('Контрольная сумма SHA-256', max_length=64, blank=True)

    status = models.CharField(
        'Статус', max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    validation_errors = models.TextField('Ошибки валидации', blank=True)
    comment = models.TextField('Комментарий', blank=True)

    class Meta:
        verbose_name = 'Выгрузка в Реестр СПО'
        verbose_name_plural = 'Выгрузки в Реестр СПО'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.file_name} ({self.created_at:%d.%m.%Y %H:%M})'