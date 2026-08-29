# -*- coding: utf-8 -*-
"""
Представления модуля «Формирование расписания» (2.4).

Портал расписания (студенты/преподаватели), автопостроение по учебному плану,
автоматическая проверка конфликтов, оперативная корректировка (замены).
"""
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView, UpdateView

from contingent.models import Group

from .forms import ScheduleBuildForm, ScheduleEntryForm, ScheduleReplaceForm
from .models import (DAY_CHOICES, SLOT_TIMES, Curriculum, Room, ScheduleEntry,
                     Teacher, TeacherUnavailable, WEEK_TYPE_CHOICES)
from .services import auto_build, check_all_conflicts

from accounts.access import RoleRequiredMixin
from accounts.roles import SCHEDULE_EDIT


def _grid(entries, week_type=None):
    """Сетка расписания: {day: {slot: entry}}."""
    grid = {day: {slot: None for slot in SLOT_TIMES} for day, _ in DAY_CHOICES}
    for e in entries:
        if week_type and e.week_type != week_type:
            continue
        grid[e.day_of_week][e.lesson_number] = e
    return grid


class SchedulePortalView(ListView):
    """Портал: список групп с опубликованным расписанием."""
    model = Group
    template_name = 'schedule/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        return (Group.objects.select_related('specialty', 'department')
                .annotate(entries_count=Count('schedule_entries'))
                .order_by('name'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['teachers'] = Teacher.objects.filter(is_active=True).order_by('last_name')
        ctx['rooms'] = Room.objects.filter(is_available=True).order_by('name')
        ctx['conflicts'] = len(check_all_conflicts())
        return ctx


class GroupScheduleView(DetailView):
    """Расписание группы (сетка дней × пар) — публикация для студентов."""
    model = Group
    template_name = 'schedule/group_schedule.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        semester = self.request.GET.get('semester', 1)
        try:
            semester = int(semester)
        except (TypeError, ValueError):
            semester = 1
        entries = (ScheduleEntry.objects.filter(group=self.object, semester=semester)
                   .select_related('subject', 'teacher', 'room')
                   .order_by('day_of_week', 'lesson_number'))
        ctx['grid'] = _grid(entries)
        ctx['entries'] = entries
        ctx['days'] = DAY_CHOICES
        ctx['slots'] = sorted(SLOT_TIMES.items())
        ctx['semester'] = semester
        ctx['week_types'] = WEEK_TYPE_CHOICES
        return ctx


class TeacherScheduleView(DetailView):
    """Расписание преподавателя."""
    model = Teacher
    template_name = 'schedule/teacher_schedule.html'
    context_object_name = 'teacher'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        semester = self.request.GET.get('semester', 1)
        try:
            semester = int(semester)
        except (TypeError, ValueError):
            semester = 1
        entries = (ScheduleEntry.objects.filter(teacher=self.object, semester=semester)
                   .select_related('subject', 'group', 'room')
                   .order_by('day_of_week', 'lesson_number'))
        ctx['grid'] = _grid(entries)
        ctx['days'] = DAY_CHOICES
        ctx['slots'] = sorted(SLOT_TIMES.items())
        ctx['semester'] = semester
        ctx['unavailable'] = TeacherUnavailable.objects.filter(
            teacher=self.object, semester=semester)
        return ctx


class EntryCreateView(RoleRequiredMixin, CreateView):
    """Создание занятия (с проверкой конфликтов)."""
    roles = SCHEDULE_EDIT
    model = ScheduleEntry
    form_class = ScheduleEntryForm
    template_name = 'schedule/entry_form.html'
    success_url = reverse_lazy('schedule:conflicts')

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get('group'):
            initial['group'] = self.request.GET['group']
        if self.request.GET.get('semester'):
            initial['semester'] = self.request.GET['semester']
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request,
                         f'Занятие добавлено: {self.object}. Конфликты проверены автоматически.')
        return redirect(self.get_success_url())


class EntryReplaceView(RoleRequiredMixin, View):
    """Оперативная корректировка: замена преподавателя / аудитории."""
    roles = SCHEDULE_EDIT

    def get(self, request, pk):
        entry = get_object_or_404(ScheduleEntry, pk=pk)
        form = ScheduleReplaceForm(entry=entry)
        return render(request, 'schedule/entry_replace.html',
                      {'entry': entry, 'form': form})

    def post(self, request, pk):
        entry = get_object_or_404(ScheduleEntry, pk=pk)
        form = ScheduleReplaceForm(request.POST, entry=entry)
        if form.is_valid():
            data = form.cleaned_data
            old_teacher, old_room = entry.teacher, entry.room
            entry.teacher = data['teacher']
            entry.room = data['room']
            entry.comment = data.get('comment', '') or entry.comment
            entry.save()
            changes = []
            if old_teacher != entry.teacher:
                changes.append(f'преподаватель: {old_teacher.short_name} → {entry.teacher.short_name}')
            if old_room != entry.room:
                changes.append(f'аудитория: {old_room} → {entry.room}')
            messages.success(request, 'Замена выполнена: ' + '; '.join(changes) +
                             (f' ({entry.comment})' if entry.comment else ''))
            return redirect('schedule:conflicts')
        return render(request, 'schedule/entry_replace.html',
                      {'entry': entry, 'form': form})


class ScheduleBuildView(RoleRequiredMixin, TemplateView):
    """Автопостроение расписания из учебного плана."""
    roles = SCHEDULE_EDIT
    template_name = 'schedule/build.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ScheduleBuildForm(self.request.POST or None)
        ctx['curriculum'] = (Curriculum.objects.select_related('group', 'subject', 'teacher')
                             .order_by('group__name', 'subject__name'))
        return ctx

    def post(self, request, *args, **kwargs):
        form = ScheduleBuildForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            created = auto_build(group=data['group'], semester=data['semester'],
                                 week_type=data['week_type'])
            messages.success(
                request,
                f'Расписание построено: {len(created)} занятий для группы '
                f'{data["group"]} (семестр {data["semester"]}).')
            return redirect(f'/schedule/groups/{data["group"].pk}/?semester={data["semester"]}')
        return render(request, self.template_name, {'form': form})


class ConflictsView(TemplateView):
    """Автоматическая проверка конфликтов всего расписания."""
    template_name = 'schedule/conflicts.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['conflicts'] = check_all_conflicts()
        ctx['total_entries'] = ScheduleEntry.objects.count()
        return ctx


class EntryPublishView(RoleRequiredMixin, View):
    """Публикация / снятие с публикации занятия."""
    roles = SCHEDULE_EDIT

    def post(self, request, pk):
        entry = get_object_or_404(ScheduleEntry, pk=pk)
        entry.is_published = not entry.is_published
        entry.save(update_fields=['is_published'])
        messages.success(
            request,
            f'Занятие {entry} {"опубликовано" if entry.is_published else "снято с публикации"}.')
        return redirect(request.META.get('HTTP_REFERER') or 'schedule:conflicts')
