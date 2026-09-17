# -*- coding: utf-8 -*-
"""Тесты модуля «Электронный журнал» (2.2)."""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from contingent.models import Department, Specialty, Group, Student, StudentStatus
from .models import Subject, Lesson, Grade, Attendance
from .services import (student_average_grade, student_attendance_percent,
                       student_is_low_performance, group_report,
                       LOW_AVG_GRADE, LOW_ATTENDANCE_PERCENT)


class JournalBaseTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        dep = Department.objects.create(name='ИТ', code='ИТ')
        spec = Specialty.objects.create(code='09.02.07', name='ИСП', department=dep)
        cls.group = Group.objects.create(name='ИС-21', specialty=spec, department=dep,
                                         course=2, enroll_year=2024)
        cls.subject = Subject.objects.create(name='Математика', code='МА')
        cls.students = []
        for i in range(3):
            cls.students.append(Student.objects.create(
                last_name=f'Студент{i}', first_name='Тест', birth_date=date(2006, 1, 1),
                snils=f'100-200-30{i} 0{i}', group=cls.group, specialty=spec,
                status=StudentStatus.STUDY, student_card_number=f'ИС-21-00{i}',
                enroll_date=date(2024, 9, 1)))


class GradeModelTests(JournalBaseTestCase):
    """Оценки и их числовые значения."""

    def test_numeric_value_for_number(self):
        lesson = Lesson.objects.create(subject=self.subject, group=self.group,
                                       date=date(2026, 10, 1))
        grade = Grade.objects.create(lesson=lesson, student=self.students[0], value='5')
        self.assertEqual(grade.numeric_value, 5)

    def test_numeric_value_for_na(self):
        lesson = Lesson.objects.create(subject=self.subject, group=self.group,
                                       date=date(2026, 10, 1))
        grade = Grade.objects.create(lesson=lesson, student=self.students[0], value='n')
        self.assertIsNone(grade.numeric_value)

    def test_grade_choices(self):
        choices = dict(Grade._meta.get_field('value').choices)
        self.assertIn('5', choices)
        self.assertIn('n', choices)


class AverageGradeTests(JournalBaseTestCase):
    """Расчёт среднего балла."""

    def test_average_of_grades(self):
        for i, value in enumerate(('5', '4', '3')):
            lesson = Lesson.objects.create(subject=self.subject, group=self.group,
                                           date=date(2026, 10, 1 + i))
            Grade.objects.create(lesson=lesson, student=self.students[0], value=value)
        # средний балл по оценкам 5,4,3 = 4.0
        self.assertEqual(student_average_grade(self.students[0]), 4.0)

    def test_average_none_without_grades(self):
        self.assertIsNone(student_average_grade(self.students[1]))

    def test_average_ignores_na(self):
        for i, value in enumerate(('5', 'n')):
            Grade.objects.create(
                lesson=Lesson.objects.create(subject=self.subject, group=self.group,
                                             date=date(2026, 11, 1 + i)),
                student=self.students[0], value=value)
        self.assertEqual(student_average_grade(self.students[0]), 5.0)


class AttendanceTests(JournalBaseTestCase):
    """Расчёт посещаемости."""

    def test_attendance_percent_100(self):
        for i in range(2):
            lesson = Lesson.objects.create(subject=self.subject, group=self.group,
                                           date=date(2026, 10, 1 + i))
            Attendance.objects.create(lesson=lesson, student=self.students[0],
                                      present=True)
        self.assertEqual(student_attendance_percent(self.students[0]), 100.0)

    def test_attendance_percent_50(self):
        for i in range(2):
            lesson = Lesson.objects.create(subject=self.subject, group=self.group,
                                           date=date(2026, 10, 1 + i))
            Attendance.objects.create(lesson=lesson, student=self.students[0],
                                      present=(i == 0))
        self.assertEqual(student_attendance_percent(self.students[0]), 50.0)

    def test_attendance_none_without_records(self):
        self.assertIsNone(student_attendance_percent(self.students[2]))


class LowPerformanceTests(JournalBaseTestCase):
    """Критерии низкой успеваемости (ТЗ: <60% или <3,5)."""

    def test_low_by_attendance(self):
        # Посещаемость 50% -> низкая
        for i in range(2):
            lesson = Lesson.objects.create(subject=self.subject, group=self.group,
                                           date=date(2026, 10, 1 + i))
            Attendance.objects.create(lesson=lesson, student=self.students[0],
                                      present=(i == 0))
        self.assertTrue(student_is_low_performance(self.students[0]))

    def test_low_by_grade(self):
        lesson = Lesson.objects.create(subject=self.subject, group=self.group,
                                       date=date(2026, 10, 1))
        Grade.objects.create(lesson=lesson, student=self.students[1], value='3')
        Attendance.objects.create(lesson=lesson, student=self.students[1], present=True)
        self.assertTrue(student_is_low_performance(self.students[1]))

    def test_not_low_for_good_student(self):
        for i in range(3):
            lesson = Lesson.objects.create(subject=self.subject, group=self.group,
                                           date=date(2026, 10, 1 + i))
            Grade.objects.create(lesson=lesson, student=self.students[2], value='5')
            Attendance.objects.create(lesson=lesson, student=self.students[2],
                                      present=True)
        self.assertFalse(student_is_low_performance(self.students[2]))

    def test_constants_from_spec(self):
        self.assertEqual(LOW_AVG_GRADE, 3.5)
        self.assertEqual(LOW_ATTENDANCE_PERCENT, 60.0)


class GroupReportTests(JournalBaseTestCase):
    """Отчёт по группе."""

    def test_report_structure(self):
        report = group_report(self.group)
        self.assertEqual(report['students_total'], 3)
        self.assertIn('group_avg', report)
        self.assertIn('low_count', report)


class LessonViewTests(JournalBaseTestCase):
    """Создание занятия через веб-интерфейс."""

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_superuser('tester', 't@t.ru', 'testpass12345')
        self.client.force_login(self.user)

    def test_lesson_create_saves_marks_and_attendance(self):
        post = {
            'subject': self.subject.pk, 'group': self.group.pk,
            'date': '2026-10-20', 'lesson_number': '1',
            'topic': 'Тестовое занятие', 'teacher': 'Тест',
            'marks-TOTAL_FORMS': '3', 'marks-INITIAL_FORMS': '0',
            'marks-MIN_NUM_FORMS': '0', 'marks-MAX_NUM_FORMS': '1000',
        }
        for i, s in enumerate(self.students):
            post[f'marks-{i}-student'] = s.pk
            post[f'marks-{i}-student_name'] = s.short_name
            post[f'marks-{i}-value'] = '5' if i < 2 else ''
            post[f'marks-{i}-present'] = 'on' if i != 2 else ''
        response = self.client.post(reverse('journal:lesson_create'), post)
        self.assertEqual(response.status_code, 302)
        lesson = Lesson.objects.get(topic='Тестовое занятие')
        self.assertEqual(lesson.grades.filter(value='5').count(), 2)
        self.assertEqual(lesson.attendance.count(), 3)
        self.assertEqual(lesson.attendance.filter(present=False).count(), 1)

    def test_low_performance_page(self):
        response = self.client.get(reverse('journal:low_performance'))
        self.assertEqual(response.status_code, 200)
