# -*- coding: utf-8 -*-
"""Тесты модуля «Кадровый учёт» (2.5)."""
import json
from datetime import date

from django.test import TestCase

from contingent.models import Department, Group, Specialty
from journal.models import Subject
from schedule.models import Curriculum, Teacher
from .models import (Employee, HROrder, SalaryExport, StaffPosition,
                     StaffingUnit, TarificationItem, TarificationPeriod)
from .services import (apply_hr_order, build_salary_export,
                       build_tarification_from_curriculum)


class HrBaseTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        dep = Department.objects.create(name='ИТ', code='ИТ')
        spec = Specialty.objects.create(code='09.02.07', name='ИСП', department=dep)
        cls.group = Group.objects.create(name='ИС-51', specialty=spec, department=dep,
                                         course=1, enroll_year=2025)
        cls.subject = Subject.objects.create(name='Информатика', code='ИН')
        cls.teacher = Teacher.objects.create(last_name='Сидоров', first_name='Сергей',
                                             position='Преподаватель')
        cls.employee = Employee.objects.create(
            last_name='Сидоров', first_name='Сергей', middle_name='Петрович',
            category=Employee.Category.TEACHER, position='Преподаватель',
            status=Employee.Status.ACTIVE, hire_date=date(2020, 9, 1),
            snils='555-666-777 88', teacher=cls.teacher)


class EmployeeModelTests(HrBaseTestCase):
    """Карточка сотрудника (Т-2)."""

    def test_full_name(self):
        self.assertEqual(self.employee.full_name, 'Сидоров Сергей Петрович')

    def test_short_name(self):
        self.assertEqual(self.employee.short_name, 'Сидоров С. П.')

    def test_default_citizenship(self):
        self.assertEqual(self.employee.citizenship, 'Россия')

    def test_default_status_active(self):
        self.assertEqual(self.employee.status, Employee.Status.ACTIVE)

    def test_employee_form_without_citizenship(self):
        """Форма не должна требовать гражданство (баг исправлен)."""
        from .forms import EmployeeForm
        form = EmployeeForm(data={
            'last_name': 'Тест', 'first_name': 'Тест', 'category': 'support',
            'position': 'Тестировщик', 'status': 'active',
            'hire_date': '2026-01-10', 'children_count': '0'})
        self.assertTrue(form.is_valid(), form.errors)


class StaffingTests(HrBaseTestCase):
    """Штатное расписание."""

    def test_position_rates(self):
        position = StaffPosition.objects.create(title='Преподаватель', rate_count=10,
                                                salary=42000)
        StaffingUnit.objects.create(position=position, employee=self.employee, rate=1)
        self.assertEqual(position.filled_rate, 1)
        self.assertEqual(position.vacancy_rate, 9)

    def test_vacancy_unit(self):
        position = StaffPosition.objects.create(title='Лаборант', rate_count=2)
        unit = StaffingUnit.objects.create(position=position, employee=None, rate=1)
        self.assertTrue(unit.is_vacancy)


class TarificationTests(HrBaseTestCase):
    """Тарификация педагогической нагрузки."""

    def setUp(self):
        self.period = TarificationPeriod.objects.create(
            name='Тарификация 2025/2026', year_start=2025)

    def test_import_from_curriculum(self):
        Curriculum.objects.create(group=self.group, subject=self.subject,
                                  teacher=self.teacher, hours_per_week=2, semester=1)
        count = build_tarification_from_curriculum(self.period)
        self.assertEqual(count, 1)
        item = self.period.items.first()
        self.assertEqual(item.employee, self.employee)
        self.assertEqual(item.total_hours, 68)  # 2 ч/нед × 34 недели

    def test_period_total_hours(self):
        TarificationItem.objects.create(period=self.period, employee=self.employee,
                                        subject=self.subject, hours_per_week=2,
                                        total_hours=68)
        self.assertEqual(self.period.total_hours, 68)


class SalaryExportTests(HrBaseTestCase):
    """Интеграция с «1С:Зарплата»."""

    def setUp(self):
        self.period = TarificationPeriod.objects.create(
            name='Тарификация', year_start=2025)
        TarificationItem.objects.create(period=self.period, employee=self.employee,
                                        subject=self.subject, hours_per_week=2,
                                        total_hours=68, groups='ИС-51')

    def test_export_creates_file(self):
        export = build_salary_export(self.period)
        self.assertTrue(export.json_file)
        self.assertEqual(export.employee_count, 1)
        self.assertEqual(export.total_hours, 68)

    def test_export_json_structure(self):
        export = build_salary_export(self.period)
        data = json.loads(export.json_file.read().decode('utf-8'))
        self.assertEqual(data['Отправитель']['Документ'], 'НагрузкаПедагогов')
        self.assertEqual(len(data['Сотрудники']), 1)
        employee_data = data['Сотрудники'][0]
        self.assertEqual(employee_data['ФИО'], 'Сидоров Сергей Петрович')
        self.assertEqual(employee_data['Нагрузка'][0]['ЧасовВГод'], 68)

    def test_export_checksum(self):
        export = build_salary_export(self.period)
        self.assertEqual(len(export.checksum), 64)


class HROrderTests(HrBaseTestCase):
    """Приказы по личному составу."""

    def test_dismiss_order(self):
        order = HROrder.objects.create(
            number='УВ-1', date=date(2026, 6, 1), order_type=HROrder.Type.DISMISS,
            employee=self.employee, basis='по собственному желанию')
        apply_hr_order(order)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, Employee.Status.DISMISSED)
        self.assertEqual(self.employee.dismissal_date, date(2026, 6, 1))

    def test_hire_order(self):
        self.employee.status = Employee.Status.DISMISSED
        self.employee.save()
        order = HROrder.objects.create(
            number='ПР-1', date=date(2026, 9, 1), order_type=HROrder.Type.HIRE,
            employee=self.employee, position='Старший преподаватель')
        apply_hr_order(order)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, Employee.Status.ACTIVE)
        self.assertEqual(self.employee.position, 'Старший преподаватель')

    def test_transfer_order(self):
        order = HROrder.objects.create(
            number='ПЕР-1', date=date(2026, 3, 1), order_type=HROrder.Type.TRANSFER,
            employee=self.employee, position='Методист')
        apply_hr_order(order)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.position, 'Методист')
        self.assertEqual(self.employee.status, Employee.Status.ACTIVE)
