# -*- coding: utf-8 -*-
"""
Сервисы модуля «Кадровый учёт» (2.5).

  build_tarification_from_curriculum(period) — тарификация из учебного плана
  build_salary_export(period, author=None)   — выгрузка в «1С:Зарплата» (JSON)
  apply_hr_order(order)                      — применение приказа по личному составу
"""
import hashlib
import json
from datetime import date

from django.core.files.base import ContentFile
from django.utils import timezone

from .models import (Employee, HROrder, SalaryExport, TarificationItem,
                     TarificationPeriod)


def build_tarification_from_curriculum(period: TarificationPeriod):
    """
    Автоматическая тарификация из учебного плана (schedule.Curriculum):
    для каждого пункта плана (группа + дисциплина + преподаватель + часы/нед)
    создаётся строка тарификации. Часы в год = часы/нед × 34 учебные недели.
    Возвращает количество созданных строк.
    """
    from schedule.models import Curriculum

    created = 0
    for cur in Curriculum.objects.select_related('group', 'subject', 'teacher'):
        employee = None
        if cur.teacher.employee:
            employee = cur.teacher.employee
        else:
            # Пытаемся найти сотрудника по ФИО преподавателя
            employee = Employee.objects.filter(
                last_name=cur.teacher.last_name,
                first_name=cur.teacher.first_name,
            ).first()
        if employee is None:
            continue
        total_hours = int(cur.hours_per_week * 34)
        item, was_created = TarificationItem.objects.get_or_create(
            period=period, employee=employee, subject=cur.subject,
            defaults={
                'hours_per_week': cur.hours_per_week,
                'total_hours': total_hours,
                'groups': cur.group.name,
            },
        )
        if was_created:
            created += 1
    return created


def build_salary_export(period: TarificationPeriod, author=None) -> SalaryExport:
    """
    Формирование выгрузки в «1С:Зарплата».

    Формат (JSON, имитация протокола обмена):
      {
        "Отправитель": {"Организация": "...", "Документ": "НагрузкаПедагогов"},
        "Период": {"Год": ..., "Наименование": ...},
        "Сотрудники": [
          {"ФИО": ..., "Должность": ..., "Категория": ...,
           "СНИЛС": ..., "Нагрузка": [{"Дисциплина": ..., "ЧасовВГод": ..., "Группы": ...}]},
          ...
        ]
      }
    """
    employees = (Employee.objects.filter(status=Employee.Status.ACTIVE)
                 .prefetch_related('tarification')
                 .order_by('last_name', 'first_name'))

    payload = {
        'Отправитель': {
            'Организация': 'ГБПОУ «Колледж»',
            'Документ': 'НагрузкаПедагогов',
            'ВерсияФормата': '1.0',
        },
        'Период': {
            'УчебныйГод': period.year_start,
            'Наименование': period.name,
        },
        'Сотрудники': [],
    }

    total_hours = 0
    count = 0
    for emp in employees:
        items = list(emp.tarification.filter(period=period))
        if not items:
            continue
        payload['Сотрудники'].append({
            'ФИО': emp.full_name,
            'Должность': emp.position,
            'Категория': emp.get_category_display(),
            'СНИЛС': emp.snils,
            'Нагрузка': [
                {'Дисциплина': i.subject.name,
                 'ЧасовВНеделю': float(i.hours_per_week),
                 'ЧасовВГод': i.total_hours,
                 'Группы': i.groups}
                for i in items
            ],
        })
        count += 1
        total_hours += sum(i.total_hours for i in items)

    data = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')

    export = SalaryExport(
        tarification=period,
        file_name=f'salary_1c_{period.year_start}_{timezone.now():%Y%m%d_%H%M%S}.json',
        checksum=hashlib.sha256(data).hexdigest(),
        status=SalaryExport.Status.READY,
        employee_count=count,
        total_hours=total_hours,
        comment=f'Сформировано {timezone.now():%d.%m.%Y %H:%M}. '
                f'Сотрудников с нагрузкой: {count}, часов: {total_hours}.',
    )
    export.json_file.save(export.file_name, ContentFile(data), save=False)
    export.save()
    return export


def apply_hr_order(order: HROrder):
    """
    Применение приказа по личному составу к карточке сотрудника:
      hire      — установить дату приёма, статус «Работает», должность;
      transfer  — обновить должность;
      dismiss   — установить дату увольнения и статус «Уволен».
    """
    emp = order.employee
    today = order.date

    if order.order_type == HROrder.Type.HIRE:
        emp.status = Employee.Status.ACTIVE
        emp.hire_date = today
        emp.dismissal_date = None
        emp.dismissal_reason = ''
        if order.position:
            emp.position = order.position

    elif order.order_type == HROrder.Type.TRANSFER:
        if order.position:
            emp.position = order.position

    elif order.order_type == HROrder.Type.DISMISS:
        emp.status = Employee.Status.DISMISSED
        emp.dismissal_date = today
        emp.dismissal_reason = order.basis or ''

    emp.save()
    return order
