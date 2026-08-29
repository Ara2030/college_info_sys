# -*- coding: utf-8 -*-
"""
Сервисы модуля «Промежуточная аттестация» (2.3).

  Расписание:
    is_group_busy(group, date)          — занят ли день группы
    nearest_free_exam_date(...)         — ближайшая свободная дата с учётом интервала
    build_schedule(...)                 — автоматическое построение расписания

  Задолженности:
    sync_debts_from_exam(exam)          — создать задолженности по итогам экзамена
    generate_debt_order(...)            — сформировать приказ о задолженностях

  Стипендия:
    student_eligible_for_scholarship(student, period) — право на стипендию
    build_scholarship_list(period)      — собрать список студентов
"""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from contingent.models import Group, Student, Order, OrderType, OrderItem
from journal.models import Subject

from .models import AcademicDebt, Exam, ExamResult, ExamType, ScholarshipPeriod

# Ограничения расписания (ТЗ)
EXAM_MIN_GAP_DAYS = 3      # интервал не менее 3 дней между экзаменами группы
MAX_EXAMS_PER_DAY = 1      # не более одного экзамена в день для группы
DEBT_DEADLINE_DAYS = 30    # срок ликвидации задолженности по умолчанию


# ==========================================================================
# Расписание
# ==========================================================================

def is_group_busy(group, day, exclude=None, exam_type=None):
    """Есть ли уже экзамен/зачёт у группы в этот день."""
    qs = Exam.objects.filter(group=group, date=day)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    if exam_type is not None:
        qs = qs.filter(exam_type=exam_type)
    return qs.exists()


def has_recent_exam(group, day, exclude=None, min_gap=EXAM_MIN_GAP_DAYS):
    """Есть ли у группы экзамен ближе, чем min_gap дней до/после day."""
    qs = Exam.objects.filter(
        group=group,
        exam_type=ExamType.EXAM,
        date__range=(day - timedelta(days=min_gap - 1),
                     day + timedelta(days=min_gap - 1)),
    )
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    return qs.exists()


def nearest_free_exam_date(group, start_day, exclude=None):
    """Первая дата >= start_day, свободная и с интервалом >= 3 дней от экзаменов."""
    day = start_day
    while True:
        if not is_group_busy(group, day, exclude, exam_type=ExamType.EXAM) \
                and not has_recent_exam(group, day, exclude):
            return day
        day += timedelta(days=1)


def build_schedule(*, group, subjects, exam_type=ExamType.EXAM,
                   start_date=None, time=None, room='', teacher='',
                   form='Билеты', note='') -> list:
    """
    Автоматическое построение расписания экзаменов/зачётов для группы.

    Экзамены: интервал не менее 3 дней, не более одного в день.
    Зачёты:   не более одного в день (без ограничения интервала).
    Возвращает список созданных Exam.
    """
    start_date = start_date or date.today() + timedelta(days=7)
    created = []

    if exam_type == ExamType.EXAM:
        day = start_date
        for subject in subjects:
            day = nearest_free_exam_date(group, day)
            exam = Exam.objects.create(
                subject=subject, group=group, exam_type=exam_type,
                date=day, time=time, room=room, teacher=teacher or subject.teacher,
                form=form, note=note,
            )
            created.append(exam)
            day += timedelta(days=EXAM_MIN_GAP_DAYS)
    else:
        day = start_date
        for subject in subjects:
            while is_group_busy(group, day, exam_type=ExamType.CREDIT):
                day += timedelta(days=1)
            exam = Exam.objects.create(
                subject=subject, group=group, exam_type=exam_type,
                date=day, time=time, room=room, teacher=teacher or subject.teacher,
                form='Зачёт', note=note,
            )
            created.append(exam)
            day += timedelta(days=1)
    return created


def validate_exam_date(group, day, exam_type=ExamType.EXAM, exclude=None):
    """Проверка ограничений для ручного добавления. Возвращает список ошибок."""
    errors = []
    if is_group_busy(group, day, exclude):
        errors.append('В этот день у группы уже назначен экзамен или зачёт '
                      '(не более одного в день).')
    if exam_type == ExamType.EXAM and has_recent_exam(group, day, exclude):
        errors.append(f'Интервал между экзаменами группы должен быть не менее '
                      f'{EXAM_MIN_GAP_DAYS} дней.')
    return errors


# ==========================================================================
# Ведомости и результаты
# ==========================================================================

def create_exam_results(exam) -> int:
    """Создать пустые строки ведомости для всех студентов группы."""
    created = 0
    for student in exam.group.students.all():
        _, was_created = ExamResult.objects.get_or_create(exam=exam, student=student)
        if was_created:
            created += 1
    return created


def sync_debts_from_exam(exam):
    """Создать академические задолженности по неудовлетворительным результатам."""
    created = []
    for result in exam.results.select_related('student'):
        if not result.is_fail:
            continue
        debt, was_created = AcademicDebt.objects.get_or_create(
            student=result.student, subject=exam.subject,
            status=AcademicDebt.Status.ACTIVE,
            defaults={
                'exam': exam,
                'deadline': date.today() + timedelta(days=DEBT_DEADLINE_DAYS),
                'comment': f'{exam.get_exam_type_display()}: {exam.subject.name} '
                           f'от {exam.date:%d.%m.%Y}',
            },
        )
        if was_created:
            created.append(debt)
    return created


def generate_debt_order(debts=None, number=None, author=None) -> Order:
    """
    Автоматическое формирование приказа об академических задолженностях.
    Использует модуль приказов контингента (Order + OrderItem).
    """
    if debts is None:
        debts = AcademicDebt.objects.filter(status=AcademicDebt.Status.ACTIVE)
    debts = list(debts)
    if not debts:
        raise ValueError('Нет активных академических задолженностей.')

    order_type, _ = OrderType.objects.get_or_create(
        code='academic_debt',
        defaults={'name': 'Академическая задолженность',
                  'document_name': 'Приказ о ликвидации академических задолженностей'},
    )
    today = date.today()
    order = Order.objects.create(
        number=number or str(today.year) + f'-{today:%m%d}-ЗД',
        date=today,
        order_type=order_type,
        title='О ликвидации академических задолженностей по итогам промежуточной аттестации',
        status=Order.Status.POSTED,
        created_by=author,
        comment=f'Автоматически сформирован {today:%d.%m.%Y}. '
                f'Задолженностей: {len(debts)}.',
    )
    for debt in debts:
        OrderItem.objects.create(
            order=order, student=debt.student,
            action='debt', basis=f'{debt.subject.name}',
            comment=f'Срок ликвидации: {debt.deadline:%d.%m.%Y}',
        )
    return order


# ==========================================================================
# Стипендия
# ==========================================================================

def student_eligible_for_scholarship(student, period: ScholarshipPeriod) -> bool:
    """
    Право на стипендию (по итогам промежуточной аттестации за период):
      - нет активных академических задолженностей;
      - по всем результатам аттестации в периоде нет оценок 2 и 3,
        нет незачётов и неявок.
    """
    if student.academic_debts.filter(status=AcademicDebt.Status.ACTIVE).exists():
        return False
    results = ExamResult.objects.filter(
        student=student,
        exam__date__range=(period.period_start, period.period_end),
    )
    for r in results:
        if r.grade in ('2', '3', 'fail'):
            return False
        if not r.present:
            return False
    return True


def build_scholarship_list(*, name=None, period_start, period_end,
                           author=None) -> ScholarshipPeriod:
    """Собрать список студентов, имеющих право на стипендию, за период."""
    period = ScholarshipPeriod.objects.create(
        name=name or f'Стипендия {period_start:%m.%Y} – {period_end:%m.%Y}',
        period_start=period_start,
        period_end=period_end,
        status=ScholarshipPeriod.Status.DRAFT,
    )
    eligible = []
    for student in Student.objects.select_related('group'):
        if student_eligible_for_scholarship(student, period):
            eligible.append(student)
    period.students.set(eligible)
    return period
