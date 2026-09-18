# -*- coding: utf-8 -*-
"""Тесты модуля «Контингент студентов» (2.1)."""
from datetime import date

from django.test import TestCase

from .models import (Department, Specialty, Group, Student, StudentStatus,
                     ParentInfo, Order, OrderType, OrderItem, RegistryExport)
from .services.orders import post_order, render_order_text
from .services.registry_export import build_registry_xml, xml_to_string, checksum


class ContingentBaseTestCase(TestCase):
    """Общая тестовая база: отделение, специальность, группа, студент."""

    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name='ИТ-отделение', code='ИТ')
        cls.specialty = Specialty.objects.create(
            code='09.02.07', name='Информационные системы и программирование',
            qualification='Разработчик', department=cls.department)
        cls.group = Group.objects.create(
            name='ИС-11', specialty=cls.specialty, department=cls.department,
            course=1, enroll_year=2025)
        cls.student = Student.objects.create(
            last_name='Иванов', first_name='Иван', middle_name='Иванович',
            birth_date=date(2007, 5, 15), gender='М',
            snils='123-456-789 01', group=cls.group, specialty=cls.specialty,
            status=StudentStatus.STUDY, student_card_number='ИС-11-001',
            enroll_date=date(2025, 9, 1), phone='+7 (900) 111-22-33',
            education_doc_series='77АБ', education_doc_number='123456',
            social_card_number='SC-1234567')


class StudentModelTests(ContingentBaseTestCase):
    """Модель студента: вычисляемые свойства и связи."""

    def test_full_name(self):
        self.assertEqual(self.student.full_name, 'Иванов Иван Иванович')

    def test_short_name(self):
        self.assertEqual(self.student.short_name, 'Иванов И. И.')

    def test_age_calculation(self):
        self.assertIsNotNone(self.student.age)
        self.assertGreaterEqual(self.student.age, 18)

    def test_full_address_with_empty_fields(self):
        self.student.address_city = 'Москва'
        self.student.address_street = 'Ленина'
        self.assertIn('Москва', self.student.full_address)

    def test_str_representation(self):
        self.assertEqual(str(self.student), 'Иванов Иван Иванович')

    def test_unique_snils(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Student.objects.create(
                last_name='Петров', first_name='Пётр', birth_date=date(2007, 1, 1),
                snils='123-456-789 01', group=self.group, specialty=self.specialty,
                student_card_number='ИС-11-002')


class ParentInfoTests(ContingentBaseTestCase):
    """Родители (законные представители)."""

    def test_create_parent(self):
        parent = ParentInfo.objects.create(
            student=self.student, relation='mother', last_name='Иванова',
            first_name='Мария', phone='+7 (900) 222-33-44')
        self.assertEqual(self.student.parents.count(), 1)
        self.assertEqual(parent.relation, 'mother')

    def test_parent_full_name(self):
        parent = ParentInfo.objects.create(
            student=self.student, last_name='Иванова', first_name='Мария',
            middle_name='Петровна')
        self.assertEqual(parent.full_name, 'Иванова Мария Петровна')


class OrderTests(ContingentBaseTestCase):
    """Приказы и движение контингента."""

    def setUp(self):
        self.order_type = OrderType.objects.create(
            code='expel', name='Отчисление', template_text='Отчислить: {student}',
            file_code='01-10', file_title='Приказы об отчислении')
        self.order = Order.objects.create(
            number='Т-001', date=date(2026, 6, 15), order_type=self.order_type,
            title='Об отчислении')
        OrderItem.objects.create(order=self.order, student=self.student,
                                 action='expel', basis='заявление')

    def test_order_item_created(self):
        self.assertEqual(self.order.items.count(), 1)

    def test_post_order_changes_status(self):
        post_order(self.order)
        self.student.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.student.status, StudentStatus.EXPELLED)
        self.assertEqual(self.order.status, Order.Status.POSTED)

    def test_post_order_writes_history(self):
        post_order(self.order)
        self.assertTrue(self.student.status_history.filter(order=self.order).exists())

    def test_post_order_twice_raises(self):
        post_order(self.order)
        with self.assertRaises(ValueError):
            post_order(self.order)

    def test_render_order_text_from_template(self):
        text = render_order_text(self.order)
        self.assertIn('Иванов Иван Иванович', text)

    def test_order_type_file_ref(self):
        self.assertIn('01-10', self.order_type.file_ref)


class RegistryExportTests(ContingentBaseTestCase):
    """Выгрузка в Реестр СПО (XML + XSD)."""

    def test_build_xml_contains_student(self):
        root = build_registry_xml([self.student])
        xml = xml_to_string(root)
        self.assertIn('РеестрСПО', xml)
        self.assertIn('Иванов', xml)

    def test_xml_contains_education_doc_and_social_card(self):
        root = build_registry_xml([self.student])
        xml = xml_to_string(root)
        self.assertIn('ДокументОбОбразовании', xml)
        self.assertIn('СоциальнаяКарта', xml)

    def test_xml_serialization(self):
        xml = xml_to_string(build_registry_xml([self.student]))
        self.assertTrue(xml.startswith('<?xml'))

    def test_checksum_is_sha256(self):
        digest = checksum(b'data')
        self.assertEqual(len(digest), 64)


class StudentFormTests(ContingentBaseTestCase):
    """Валидация формы студента."""

    def test_snils_validation_error(self):
        from .forms import StudentForm
        form = StudentForm(data={
            'last_name': 'Тест', 'first_name': 'Тест', 'birth_date': '2007-01-01',
            'snils': 'неверный', 'group': self.group.pk, 'specialty': self.specialty.pk,
            'student_card_number': 'X-1', 'enroll_date': '2025-09-01'})
        self.assertFalse(form.is_valid())
        self.assertIn('snils', form.errors)

    def test_group_specialty_mismatch(self):
        from .forms import StudentForm
        other_spec = Specialty.objects.create(
            code='13.02.03', name='Электрические станции',
            department=self.department)
        form = StudentForm(data={
            'last_name': 'Тест', 'first_name': 'Тест', 'birth_date': '2007-01-01',
            'snils': '111-222-333 44', 'group': self.group.pk,
            'specialty': other_spec.pk, 'student_card_number': 'X-2',
            'enroll_date': '2025-09-01'})
        self.assertFalse(form.is_valid())
