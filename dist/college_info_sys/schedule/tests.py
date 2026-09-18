# -*- coding: utf-8 -*-
"""Тесты модуля «Формирование расписания» (2.4)."""
from django.test import TestCase

from contingent.models import Department, Group, Specialty
from journal.models import Subject
from .models import (Curriculum, Room, ScheduleEntry, Teacher,
                     TeacherUnavailable, DAY_CHOICES, SLOT_TIMES)
from .services import (auto_build, check_all_conflicts, check_entry_conflicts,
                       entry_is_valid)


class ScheduleBaseTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        dep = Department.objects.create(name='ИТ', code='ИТ')
        spec = Specialty.objects.create(code='09.02.07', name='ИСП', department=dep)
        cls.group = Group.objects.create(name='ИС-41', specialty=spec, department=dep,
                                         course=4, enroll_year=2022)
        cls.group2 = Group.objects.create(name='ИС-42', specialty=spec, department=dep,
                                          course=4, enroll_year=2022)
        cls.subject = Subject.objects.create(name='Программирование', code='ПР')
        cls.teacher = Teacher.objects.create(last_name='Иванов', first_name='Иван',
                                             position='Преподаватель')
        cls.room = Room.objects.create(name='А-101', capacity=30)
        cls.room2 = Room.objects.create(name='А-102', capacity=30)


class ConflictDetectionTests(ScheduleBaseTestCase):
    """Автоматическая проверка конфликтов."""

    def setUp(self):
        self.entry = ScheduleEntry.objects.create(
            group=self.group, subject=self.subject, teacher=self.teacher,
            room=self.room, day_of_week=1, lesson_number=1, semester=1)

    def test_no_conflict_for_free_slot(self):
        trial = ScheduleEntry(group=self.group2, subject=self.subject,
                              teacher=self.teacher, room=self.room,
                              day_of_week=2, lesson_number=2, semester=1)
        self.assertEqual(check_entry_conflicts(trial), [])

    def test_group_conflict(self):
        trial = ScheduleEntry(group=self.group, subject=self.subject,
                              teacher=self.teacher, room=self.room2,
                              day_of_week=1, lesson_number=1, semester=1)
        errors = check_entry_conflicts(trial)
        self.assertTrue(any('группы' in e.lower() for e in errors), errors)

    def test_room_conflict(self):
        trial = ScheduleEntry(group=self.group2, subject=self.subject,
                              teacher=self.teacher, room=self.room,
                              day_of_week=1, lesson_number=1, semester=1)
        errors = check_entry_conflicts(trial)
        self.assertTrue(any('удитория' in e.lower() or 'аудитория' in e.lower()
                            for e in errors), errors)

    def test_teacher_conflict(self):
        trial = ScheduleEntry(group=self.group2, subject=self.subject,
                              teacher=self.teacher, room=self.room2,
                              day_of_week=1, lesson_number=1, semester=1)
        errors = check_entry_conflicts(trial)
        self.assertTrue(any('реподаватель' in e for e in errors), errors)

    def test_teacher_unavailable(self):
        TeacherUnavailable.objects.create(teacher=self.teacher, day_of_week=3,
                                          lesson_number=2, semester=1)
        trial = ScheduleEntry(group=self.group2, subject=self.subject,
                              teacher=self.teacher, room=self.room2,
                              day_of_week=3, lesson_number=2, semester=1)
        errors = check_entry_conflicts(trial)
        self.assertTrue(any('недоступен' in e for e in errors), errors)

    def test_check_all_conflicts_finds_none(self):
        self.assertEqual(check_all_conflicts(), [])

    def test_check_all_conflicts_detects_violation(self):
        # Создаём конфликтующую запись в обход проверки
        ScheduleEntry.objects.create(group=self.group2, subject=self.subject,
                                     teacher=self.teacher, room=self.room,
                                     day_of_week=1, lesson_number=1, semester=1)
        self.assertEqual(len(check_all_conflicts()), 2)


class AutoBuildTests(ScheduleBaseTestCase):
    """Автопостроение расписания по учебному плану."""

    def setUp(self):
        Curriculum.objects.create(group=self.group, subject=self.subject,
                                  teacher=self.teacher, hours_per_week=2, semester=1)

    def test_auto_build_creates_entries(self):
        created = auto_build(group=self.group, semester=1)
        self.assertEqual(len(created), 2)

    def test_auto_build_without_conflicts(self):
        auto_build(group=self.group, semester=1)
        self.assertEqual(check_all_conflicts(), [])

    def test_auto_build_respects_group_schedule(self):
        auto_build(group=self.group, semester=1)
        entries = ScheduleEntry.objects.filter(group=self.group)
        slots = [(e.day_of_week, e.lesson_number) for e in entries]
        self.assertEqual(len(slots), len(set(slots)), 'слоты группы не должны повторяться')

    def test_auto_build_two_groups_same_teacher(self):
        Curriculum.objects.create(group=self.group2, subject=self.subject,
                                  teacher=self.teacher, hours_per_week=1, semester=1)
        auto_build(group=self.group, semester=1)
        auto_build(group=self.group2, semester=1)
        self.assertEqual(check_all_conflicts(), [],
                         'преподаватель не должен вести две группы одновременно')


class ScheduleModelTests(ScheduleBaseTestCase):
    """Модели и вспомогательные функции."""

    def test_days_and_slots_constants(self):
        self.assertEqual(len(DAY_CHOICES), 6)
        self.assertEqual(len(SLOT_TIMES), 6)

    def test_room_str(self):
        self.assertEqual(str(self.room), 'А-101')

    def test_teacher_short_name(self):
        teacher = Teacher.objects.create(last_name='Петров', first_name='Пётр',
                                         middle_name='Петрович')
        self.assertEqual(teacher.short_name, 'Петров П. П.')

    def test_slot_busy_detected_via_conflicts(self):
        """Занятость слота группы определяется через проверку конфликтов."""
        ScheduleEntry.objects.create(group=self.group, subject=self.subject,
                                     teacher=self.teacher, room=self.room,
                                     day_of_week=4, lesson_number=3, semester=1)
        trial = ScheduleEntry(group=self.group, subject=self.subject,
                              teacher=self.teacher, room=self.room2,
                              day_of_week=4, lesson_number=3, semester=1)
        self.assertFalse(entry_is_valid(trial))
        free = ScheduleEntry(group=self.group, subject=self.subject,
                             teacher=self.teacher, room=self.room2,
                             day_of_week=5, lesson_number=3, semester=1)
        self.assertTrue(entry_is_valid(free))

    def test_curriculum_unique_per_semester(self):
        from django.db import IntegrityError
        Curriculum.objects.create(group=self.group, subject=self.subject,
                                  teacher=self.teacher, hours_per_week=2, semester=1)
        with self.assertRaises(IntegrityError):
            Curriculum.objects.create(group=self.group, subject=self.subject,
                                      teacher=self.teacher, hours_per_week=3, semester=1)
