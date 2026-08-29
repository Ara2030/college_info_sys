# -*- coding: utf-8 -*-
"""Админ-панель модуля «Промежуточная аттестация» (2.3)."""
from django.contrib import admin

from .models import Exam, ExamResult, AcademicDebt, ScholarshipPeriod


class ExamResultInline(admin.TabularInline):
    model = ExamResult
    extra = 0


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('date', 'time', 'group', 'subject', 'exam_type', 'room', 'teacher')
    list_filter = ('exam_type', 'subject', 'group')
    search_fields = ('subject__name', 'group__name', 'teacher')
    inlines = (ExamResultInline,)


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('exam', 'student', 'grade', 'present')
    list_filter = ('grade', 'exam__exam_type')
    search_fields = ('student__last_name', 'student__first_name')
    autocomplete_fields = ('student',)


@admin.register(AcademicDebt)
class AcademicDebtAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'status', 'created_at', 'deadline', 'cleared_at')
    list_filter = ('status', 'subject')
    search_fields = ('student__last_name', 'student__first_name', 'subject__name')
    autocomplete_fields = ('student',)


@admin.register(ScholarshipPeriod)
class ScholarshipPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'period_start', 'period_end', 'status', 'students_count')
    list_filter = ('status',)
    filter_horizontal = ('students',)
