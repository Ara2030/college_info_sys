# -*- coding: utf-8 -*-
"""Тесты модуля «Промежуточная аттестация» (2.3)."""
from datetime import date, timedelta

from django.test import TestCase

from contingent.models import Department, Group, Specialty, Student, StudentStatus
from journal.models import Subject
from .models import AcademicDebt, Exam, ExamResult, ExamType, ScholarshipPeriod
from .services import (build_schedule, create_exam_results, generate_debt_order,
                       has_recent_exam, is_group_busy, student_eligible_for_scholarship,
                       sync_debts_from_exam, validate_exam_date,
                       EXAM_MIN_GAP_DAYS)


class AttestationBaseTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        dep = Department.objects.create(name='ИТ', code='ИТ')
        spec = Specialty.objects.create(code='09.02.07', name='ИСП', department=dep)
        cls.group = Group.objects.create(name='ИС-31', specialty=spec, department=dep,
                                         course=3, enroll_year=2023)
        cls.subject = Subject.objects.create(name='Базы данных', code='БД')
        cls.students = [
            Student.objects.create(
                last_name=f'Тестов{i}', first_name='Иван', birth_date=date(2005, 1, 1),
                snils=f'300-400-50{i} 0{i}', group=cls.group, specialty=spec,
                status=StudentStatus.STUDY, student_card_number=f'ИС-31-00{i}',
                enroll_date=date(2023, 9, 1))
            for i in range(3)
        ]


class ExamScheduleConstraintTests(AttestationBaseTestCase):
    """Ограничения расписания экзаменов (ТЗ)."""

    def test_schedule_creates_exams_with_gap(self):
        exams = build_schedule(group=self.group, subjects=[self.subject],
                               exam_type=ExamType.EXAM, start_date=date(2030, 6, 1))
        self.assertEqual(len(exams), 1)

    def test_no_exam_in_occupied_day(self):
        day = date(2030, 6, 10)
        Exam.objects.create(subject=self.subject, group=self.group,
                            exam_type=ExamType.EXAM, date=day)
        errors = validate_exam_date(self.group, day, ExamType.EXAM)
        self.assertTrue(errors)
        self.assertTrue(is_group_busy(self.group, day))

    def test_gap_less_than_three_days_rejected(self):
        day = date(2030, 6, 10)
        Exam.objects.create(subject=self.subject, group=self.group,
                            exam_type=ExamType.EXAM, date=day)
        for delta in (1, 2):
            errors = validate_exam_date(self.group, day + timedelta(days=delta),
                                        ExamType.EXAM)
            self.assertTrue(errors, f'интервал {delta} дн. должен быть отклонён')
        self.assertTrue(has_recent_exam(self.group, day + timedelta(days=2)))

    def test_gap_of_three_days_allowed(self):
        day = date(2030, 6, 10)
        Exam.objects.create(subject=self.subject, group=self.group,
                            exam_type=ExamType.EXAM, date=day)
        errors = validate_exam_date(self.group, day + timedelta(days=EXAM_MIN_GAP_DAYS),
                                    ExamType.EXAM)
        self.assertFalse(errors)

    def test_credit_without_gap_constraint(self):
        day = date(2030, 6, 10)
        Exam.objects.create(subject=self.subject, group=self.group,
                            exam_type=ExamType.CREDIT, date=day)
        errors = validate_exam_date(self.group, day + timedelta(days=1),
                                    ExamType.CREDIT)
        self.assertFalse(errors)

    def test_auto_schedule_builds_several_exams(self):
        subjects = [Subject.objects.create(name=f'Дисциплина {i}', code=f'Д{i}')
                    for i in range(3)]
        exams = build_schedule(group=self.group, subjects=subjects,
                               exam_type=ExamType.EXAM, start_date=date(2030, 6, 1))
        self.assertEqual(len(exams), 3)
        dates = sorted(e.date for e in exams)
        for i in range(1, len(dates)):
            self.assertGreaterEqual((dates[i] - dates[i - 1]).days, EXAM_MIN_GAP_DAYS)


class ExamResultTests(AttestationBaseTestCase):
    """Ведомости и результаты."""

    def setUp(self):
        self.exam = Exam.objects.create(subject=self.subject, group=self.group,
                                        exam_type=ExamType.EXAM, date=date(2030, 6, 20))

    def test_results_created_for_group(self):
        created = create_exam_results(self.exam)
        self.assertEqual(created, 3)
        self.assertEqual(self.exam.results.count(), 3)

    def test_result_creation_idempotent(self):
        create_exam_results(self.exam)
        create_exam_results(self.exam)
        self.assertEqual(self.exam.results.count(), 3)

    def test_fail_detection_for_two(self):
        result = ExamResult.objects.create(exam=self.exam, student=self.students[0],
                                           grade='2', present=True)
        self.assertTrue(result.is_fail)

    def test_fail_detection_for_absence(self):
        result = ExamResult.objects.create(exam=self.exam, student=self.students[1],
                                           grade='', present=False)
        self.assertTrue(result.is_fail)

    def test_pass_not_fail(self):
        result = ExamResult.objects.create(exam=self.exam, student=self.students[2],
                                           grade='5', present=True)
        self.assertFalse(result.is_fail)


class AcademicDebtTests(AttestationBaseTestCase):
    """Академические задолженности."""

    def setUp(self):
        self.exam = Exam.objects.create(subject=self.subject, group=self.group,
                                        exam_type=ExamType.EXAM, date=date(2030, 6, 20))
        create_exam_results(self.exam)

    def test_debt_created_for_failed_result(self):
        ExamResult.objects.filter(exam=self.exam, student=self.students[0]).update(grade='2')
        debts = sync_debts_from_exam(self.exam)
        self.assertEqual(len(debts), 1)
        self.assertEqual(debts[0].student, self.students[0])
        self.assertEqual(debts[0].status, AcademicDebt.Status.ACTIVE)

    def test_no_debt_for_successful_result(self):
        for s in self.students:
            ExamResult.objects.filter(exam=self.exam, student=s).update(grade='5')
        debts = sync_debts_from_exam(self.exam)
        self.assertEqual(len(debts), 0)

    def test_debt_not_duplicated(self):
        ExamResult.objects.filter(exam=self.exam, student=self.students[0]).update(grade='2')
        sync_debts_from_exam(self.exam)
        sync_debts_from_exam(self.exam)
        self.assertEqual(AcademicDebt.objects.filter(student=self.students[0]).count(), 1)

    def test_generate_debt_order(self):
        ExamResult.objects.filter(exam=self.exam, student=self.students[0]).update(grade='2')
        sync_debts_from_exam(self.exam)
        order = generate_debt_order()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.order_type.code, 'academic_debt')

    def test_generate_order_without_debts_raises(self):
        with self.assertRaises(ValueError):
            generate_debt_order()


class ScholarshipTests(AttestationBaseTestCase):
    """Право на стипендию."""

    def setUp(self):
        self.period = ScholarshipPeriod.objects.create(
            name='Тестовая стипендия', period_start=date(2030, 6, 1),
            period_end=date(2030, 6, 30))
        self.exam = Exam.objects.create(subject=self.subject, group=self.group,
                                        exam_type=ExamType.EXAM, date=date(2030, 6, 20))

    def test_eligible_without_results_and_debts(self):
        self.assertTrue(student_eligible_for_scholarship(self.students[0], self.period))

    def test_not_eligible_with_three(self):
        ExamResult.objects.create(exam=self.exam, student=self.students[0], grade='3')
        self.assertFalse(student_eligible_for_scholarship(self.students[0], self.period))

    def test_not_eligible_with_debt(self):
        AcademicDebt.objects.create(student=self.students[1], subject=self.subject,
                                    status=AcademicDebt.Status.ACTIVE)
        self.assertFalse(student_eligible_for_scholarship(self.students[1], self.period))

    def test_eligible_with_excellent_grades(self):
        ExamResult.objects.create(exam=self.exam, student=self.students[2], grade='5')
        self.assertTrue(student_eligible_for_scholarship(self.students[2], self.period))
