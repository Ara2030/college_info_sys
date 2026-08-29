# -*- coding: utf-8 -*-
"""Админ-панель модуля «Кадровый учёт» (2.5)."""
from django.contrib import admin

from .models import (Employee, HROrder, SalaryExport, StaffPosition,
                     StaffingUnit, TarificationItem, TarificationPeriod)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'position', 'category', 'status', 'hire_date', 'dismissal_date')
    list_filter = ('status', 'category')
    search_fields = ('last_name', 'first_name', 'middle_name', 'snils', 'inn', 'position')


@admin.register(StaffPosition)
class StaffPositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'rate_count', 'salary', 'filled_rate')
    search_fields = ('title',)


@admin.register(StaffingUnit)
class StaffingUnitAdmin(admin.ModelAdmin):
    list_display = ('position', 'employee', 'rate', 'date_from')
    list_filter = ('position',)
    autocomplete_fields = ('employee',)


@admin.register(TarificationPeriod)
class TarificationPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'year_start', 'status', 'total_hours')
    list_filter = ('status',)


@admin.register(TarificationItem)
class TarificationItemAdmin(admin.ModelAdmin):
    list_display = ('period', 'employee', 'subject', 'hours_per_week', 'total_hours', 'groups')
    list_filter = ('period',)
    search_fields = ('employee__last_name', 'subject__name')
    autocomplete_fields = ('employee',)


@admin.register(HROrder)
class HROrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'date', 'order_type', 'employee', 'position')
    list_filter = ('order_type',)
    search_fields = ('number', 'employee__last_name')
    autocomplete_fields = ('employee',)


@admin.register(SalaryExport)
class SalaryExportAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'created_at', 'tarification', 'employee_count',
                    'total_hours', 'status')
    list_filter = ('status',)
