# -*- coding: utf-8 -*-
"""
Сервисы модуля «Электронный журнал» (2.2).

Расчётные функции:
  student_average_grade(student)     — средний балл студента
  student_attendance_percent(student) — процент посещаемости студента
  student_is_low_performance(student) — критерий низкой успеваемости (ТЗ):
        посещаемость < 60% ИЛИ средний балл < 3,5
  group_report(group)                — отчёт по группе
  low_performance_students(...)      — выборка отстающих
"""
from datetime import date

from django.db.models import Avg, Count, F, Q

from contingent.models import Student

from .models import (Attendance, Grade, Lesson, LOW_ATTENDANCE_PERCENT,
                     LOW_AVG_GRADE, NUMERIC_GRADES)


def student_average_grade(student):
    """Средний балл студента по всем числовым оценкам (2–5)."""
    grades = [g.numeric_value for g in student.grades.all()
              if g.numeric_value is not None]
    if not grades:
        return None
    return round(sum(grades) / len(grades), 2)


def student_attendance_percent(student):
    """Процент посещённых занятий от общего числа занятий студента."""
    total = student.attendance.count()
    if total == 0:
        return None
    present = student.attendance.filter(present=True).count()
    return round(present / total * 100, 1)


def student_is_low_performance(student):
    """True, если студент отстаёт: <60% посещаемости ИЛИ средний балл < 3,5."""
    avg = student_average_grade(student)
    attend = student_attendance_percent(student)

    if avg is not None and avg < LOW_AVG_GRADE:
        return True
    if attend is not None and attend < LOW_ATTENDANCE_PERCENT:
        return True
    return False


def group_students_stats(group):
    """
    Список студентов группы со статистикой для отчёта:
    [{student, avg_grade, attendance_percent, is_low, grades_count, lessons_count}]
    """
    students = group.students.select_related('group', 'specialty').order_by(
        'last_name', 'first_name')
    result = []
    for student in students:
        avg = student_average_grade(student)
        attend = student_attendance_percent(student)
        result.append({
            'student': student,
            'avg_grade': avg,
            'attendance_percent': attend,
            'is_low': student_is_low_performance(student),
            'grades_count': student.grades.count(),
            'lessons_count': student.attendance.count(),
        })
    return result


def group_report(group):
    """Сводный отчёт по группе: статистика + итоги."""
    stats = group_students_stats(group)
    avg_values = [s['avg_grade'] for s in stats if s['avg_grade'] is not None]
    attend_values = [s['attendance_percent'] for s in stats
                     if s['attendance_percent'] is not None]
    return {
        'students': stats,
        'students_total': len(stats),
        'low_count': sum(1 for s in stats if s['is_low']),
        'group_avg': (round(sum(avg_values) / len(avg_values), 2)
                      if avg_values else None),
        'group_attendance': (round(sum(attend_values) / len(attend_values), 1)
                             if attend_values else None),
        'lessons_count': Lesson.objects.filter(group=group).count(),
        'generated_at': date.today(),
    }


def low_performance_students(groups=None):
    """
    Студенты с низкой успеваемостью (для уведомлений преподавателей).
    groups — опциональный фильтр по группам (QuerySet).
    """
    students = Student.objects.select_related('group', 'specialty').prefetch_related(
        'grades', 'attendance').order_by('group__name', 'last_name', 'first_name')
    if groups is not None:
        students = students.filter(group__in=groups)
    return [s for s in students if student_is_low_performance(s)]
