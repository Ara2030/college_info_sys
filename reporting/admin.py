# -*- coding: utf-8 -*-
"""Админ-панель модуля «Отчётность и интеграция» (2.6)."""
from django.contrib import admin

from .models import IntegrationLog, SmevRequest, StatReport


@admin.register(StatReport)
class StatReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'period_year', 'period_date', 'status', 'created_at')
    list_filter = ('report_type', 'status', 'period_year')
    search_fields = ('file_name',)


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'integration', 'direction', 'endpoint', 'status_code', 'status')
    list_filter = ('integration', 'status')
    search_fields = ('endpoint', 'payload')


@admin.register(SmevRequest)
class SmevRequestAdmin(admin.ModelAdmin):
    list_display = ('request_date', 'registry', 'identifier', 'person_name', 'status')
    list_filter = ('registry', 'status')
    search_fields = ('identifier', 'person_name')
