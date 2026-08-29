# -*- coding: utf-8 -*-
"""Админ-панель модуля «Электронный журнал» (2.2)."""
from django.contrib import admin

from .models import Subject, Lesson, Grade, Attendance


class GradeInline(admin.TabularInline):
    model = Grade
    extra = 0


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'teacher')
    search_fields = ('name', 'code', 'teacher')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('date', 'lesson_number', 'subject', 'group', 'topic', 'teacher')
    list_filter = ('subject', 'group')
    search_fields = ('topic', 'subject__name', 'group__name')
    inlines = (GradeInline, AttendanceInline)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'student', 'value')
    list_filter = ('value', 'lesson__subject')
    search_fields = ('student__last_name', 'student__first_name')
    autocomplete_fields = ('student',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'student', 'present')
    list_filter = ('present', 'lesson__subject')
    search_fields = ('student__last_name', 'student__first_name')
    autocomplete_fields = ('student',)
