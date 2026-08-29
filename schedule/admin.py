# -*- coding: utf-8 -*-
"""Админ-панель модуля «Формирование расписания» (2.4)."""
from django.contrib import admin

from .models import Room, Teacher, Curriculum, TeacherUnavailable, ScheduleEntry


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'building', 'capacity', 'room_type', 'is_available')
    list_filter = ('room_type', 'is_available')
    search_fields = ('name',)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'position', 'department', 'is_active')
    list_filter = ('is_active', 'department')
    search_fields = ('last_name', 'first_name', 'middle_name')


@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ('group', 'subject', 'teacher', 'hours_per_week', 'semester', 'exam_type')
    list_filter = ('semester', 'exam_type', 'group')
    search_fields = ('group__name', 'subject__name', 'teacher__last_name')
    autocomplete_fields = ('group',)


@admin.register(TeacherUnavailable)
class TeacherUnavailableAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'day_of_week', 'lesson_number', 'semester', 'comment')
    list_filter = ('day_of_week', 'semester')
    autocomplete_fields = ('teacher',)


@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ('day_of_week', 'lesson_number', 'group', 'subject',
                    'teacher', 'room', 'semester', 'is_published')
    list_filter = ('day_of_week', 'semester', 'is_published', 'week_type')
    search_fields = ('group__name', 'subject__name', 'teacher__last_name', 'room__name')
    autocomplete_fields = ('group',)
