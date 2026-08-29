# -*- coding: utf-8 -*-
"""
Представления модуля «Электронный журнал» (2.2).

Журналы занятий по группам и дисциплинам, фиксация оценок и посещаемости,
отчёты об успеваемости (для администрации и родителей),
уведомления преподавателей о студентах с низкой успеваемостью.
"""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView

from contingent.models import Group, Student
from .forms import LessonForm, grade_formset_factory
from .models import Subject, Lesson, Grade, Attendance
from .services import (group_report, low_performance_students,
                       student_average_grade, student_attendance_percent,
                       student_is_low_performance)

from accounts.access import RoleRequiredMixin
from accounts.roles import JOURNAL_EDIT, LOW_PERF_VIEW


# ---------------- Журналы занятий ----------------

class JournalGroupListView(ListView):
    """Список групп, для которых ведутся журналы."""
    model = Group
    template_name = 'journal/group_list.html'
    context_object_name = 'groups'
    paginate_by = 24

    def get_queryset(self):
        return Group.objects.select_related('specialty', 'department').order_by('name')


class JournalGroupView(DetailView):
    """Журнал группы: дисциплины и проведённые занятия."""
    model = Group
    template_name = 'journal/group_detail.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group = self.object
        ctx['lessons'] = (Lesson.objects.filter(group=group)
                          .select_related('subject').order_by('-date', '-lesson_number'))
        ctx['subjects'] = (Subject.objects
                           .filter(lessons__group=group).distinct()
                           .annotate(lessons_count=Count('lessons', filter=Q(lessons__group=group)))
                           .order_by('name'))
        ctx['students'] = group.students.order_by('last_name', 'first_name')
        return ctx


class LessonCreateView(RoleRequiredMixin, CreateView):
    """Создание занятия с отметками оценок и посещаемости."""
    roles = JOURNAL_EDIT
    model = Lesson
    form_class = LessonForm
    template_name = 'journal/lesson_form.html'
    success_url = reverse_lazy('journal:group_list')

    def get_initial(self):
        initial = super().get_initial()
        group_id = self.request.GET.get('group')
        if group_id:
            initial['group'] = group_id
        subject_id = self.request.GET.get('subject')
        if subject_id:
            initial['subject'] = subject_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group_id = self.request.POST.get('group') or self.request.GET.get('group')
        students = Group.objects.filter(pk=group_id).first().students.order_by(
            'last_name', 'first_name') if group_id else Student.objects.none()
        ctx['students'] = students
        if self.request.POST:
            ctx['marks_formset'] = grade_formset_factory(students).__class__(
                self.request.POST, prefix='marks')
        else:
            ctx['marks_formset'] = grade_formset_factory(students)
        return ctx

    def form_valid(self, form):
        lesson = form.save()
        students = lesson.group.students.order_by('last_name', 'first_name')
        formset = grade_formset_factory(students).__class__(
            self.request.POST, prefix='marks')
        if formset.is_valid():
            self._save_marks(lesson, formset)
        messages.success(self.request, f'Занятие {lesson} сохранено.')
        return redirect('journal:lesson_detail', pk=lesson.pk)

    def _save_marks(self, lesson, formset):
        for form in formset.forms:
            data = form.cleaned_data
            if not data.get('student'):
                continue
            student = data['student']
            Grade.objects.update_or_create(
                lesson=lesson, student=student,
                defaults={'value': data.get('value', '') or ''},
            )
            Attendance.objects.update_or_create(
                lesson=lesson, student=student,
                defaults={'present': data.get('present', True)},
            )


class LessonDetailView(DetailView):
    """Журнал одного занятия: оценки и посещаемость группы."""
    model = Lesson
    template_name = 'journal/lesson_detail.html'
    context_object_name = 'lesson'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson = self.object
        students = lesson.group.students.order_by('last_name', 'first_name')
        grades = {g.student_id: g for g in lesson.grades.all()}
        attendance = {a.student_id: a for a in lesson.attendance.all()}
        rows = []
        for s in students:
            grade = grades.get(s.pk)
            att = attendance.get(s.pk)
            rows.append({
                'student': s,
                'grade_value': grade.value if grade else '',
                'present': att.present if att else True,
            })
        ctx['rows'] = rows
        ctx['students_count'] = students.count()
        ctx['present_count'] = sum(1 for r in rows if r['present'])
        ctx['graded_count'] = sum(1 for r in rows if r['grade_value'])
        return ctx


class LessonUpdateView(RoleRequiredMixin, UpdateView):
    """Редактирование занятия и отметок."""
    roles = JOURNAL_EDIT
    model = Lesson
    form_class = LessonForm
    template_name = 'journal/lesson_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lesson = self.object
        students = lesson.group.students.order_by('last_name', 'first_name')
        grades = {g.student_id: g for g in lesson.grades.all()}
        attendance = {a.student_id: a for a in lesson.attendance.all()}
        initial = []
        for s in students:
            grade = grades.get(s.pk)
            att = attendance.get(s.pk)
            initial.append({
                'student': s.pk, 'student_name': s.short_name,
                'value': grade.value if grade and grade.value else '',
                'present': att.present if att else True,
            })
        ctx['students'] = students
        if self.request.POST:
            ctx['marks_formset'] = grade_formset_factory(students).__class__(
                self.request.POST, prefix='marks')
        else:
            ctx['marks_formset'] = grade_formset_factory(students).__class__(
                initial=initial, prefix='marks')
        return ctx

    def form_valid(self, form):
        lesson = form.save()
        students = lesson.group.students.order_by('last_name', 'first_name')
        formset = grade_formset_factory(students).__class__(
            self.request.POST, prefix='marks')
        if formset.is_valid():
            LessonCreateView._save_marks(self, lesson, formset)
        messages.success(self.request, 'Занятие обновлено.')
        return redirect('journal:lesson_detail', pk=lesson.pk)


# ---------------- Отчёты об успеваемости ----------------

class GroupReportView(DetailView):
    """Отчёт о текущей успеваемости группы (для администрации)."""
    model = Group
    template_name = 'journal/group_report.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['report'] = group_report(self.object)
        return ctx


class StudentProgressView(DetailView):
    """Отчёт по одному студенту (для родителей)."""
    model = Student
    template_name = 'journal/student_progress.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        student = self.object
        ctx['avg_grade'] = student_average_grade(student)
        ctx['attendance_percent'] = student_attendance_percent(student)
        ctx['is_low'] = student_is_low_performance(student)
        ctx['grades'] = (Grade.objects.filter(student=student)
                         .select_related('lesson', 'lesson__subject')
                         .order_by('-lesson__date'))
        ctx['attendance'] = (Attendance.objects.filter(student=student)
                             .select_related('lesson', 'lesson__subject')
                             .order_by('-lesson__date'))
        ctx['lessons_total'] = student.attendance.count()
        ctx['present_total'] = student.attendance.filter(present=True).count()
        return ctx


class LowPerformanceView(RoleRequiredMixin, TemplateView):
    """Уведомления преподавателей: студенты с низкой успеваемостью.

    Критерии (ТЗ): посещаемость < 60% ИЛИ средний балл < 3,5.
    """
    roles = LOW_PERF_VIEW
    template_name = 'journal/low_performance.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group_id = self.request.GET.get('group')
        groups_qs = Group.objects.all()
        if group_id:
            groups_qs = groups_qs.filter(pk=group_id)
            ctx['selected_group'] = int(group_id)

        students = low_performance_students(groups=groups_qs)
        rows = []
        for s in students:
            rows.append({
                'student': s,
                'avg_grade': student_average_grade(s),
                'attendance_percent': student_attendance_percent(s),
            })
        ctx['rows'] = rows
        ctx['groups'] = Group.objects.select_related('specialty').order_by('name')
        ctx['total'] = len(rows)
        return ctx
