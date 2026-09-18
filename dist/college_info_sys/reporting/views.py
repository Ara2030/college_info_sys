# -*- coding: utf-8 -*-
"""
Представления модуля «Отчётность и интеграция» (2.6).

Статистические отчёты (СПО-1, СПО-2, мониторинг), выгрузка в Реестр СПО
через REST API (XML), интеграция с СМЭВ, экспорт в Excel/PDF.
"""
import json

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView

from attestation.models import ScholarshipPeriod
from contingent.models import RegistryExport

from .forms import SmevRequestForm, StatReportForm
from .models import IntegrationLog, SmevRequest, StatReport
from .services import (build_stat_report, send_to_registry_api, smev_request,
                       stat_report_excel, stat_report_pdf)

from accounts.access import RoleRequiredMixin
from accounts.roles import INTEGRATION_MGMT, REPORTING_EDIT


# ---------------- Дашборд отчётности ----------------

class ReportingDashboardView(RoleRequiredMixin, TemplateView):
    roles = REPORTING_EDIT
    template_name = 'reporting/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reports'] = StatReport.objects.count()
        ctx['spo1'] = StatReport.objects.filter(report_type=StatReport.Type.SPO1).count()
        ctx['spo2'] = StatReport.objects.filter(report_type=StatReport.Type.SPO2).count()
        ctx['monitoring'] = StatReport.objects.filter(
            report_type=StatReport.Type.MONITORING).count()
        ctx['exports'] = RegistryExport.objects.count()
        ctx['logs'] = IntegrationLog.objects.count()
        ctx['smev'] = SmevRequest.objects.count()
        ctx['recent_reports'] = StatReport.objects.order_by('-created_at')[:5]
        return ctx


# ---------------- Статистические отчёты ----------------

class StatReportListView(RoleRequiredMixin, ListView):
    roles = REPORTING_EDIT
    model = StatReport
    template_name = 'reporting/stat_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        report_type = self.request.GET.get('type')
        if report_type:
            qs = qs.filter(report_type=report_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['selected_type'] = self.request.GET.get('type', '')
        return ctx


class StatReportCreateView(RoleRequiredMixin, TemplateView):
    roles = REPORTING_EDIT
    template_name = 'reporting/stat_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = StatReportForm(self.request.POST or None)
        return ctx

    def post(self, request, *args, **kwargs):
        form = StatReportForm(request.POST)
        if form.is_valid():
            report = build_stat_report(
                form.cleaned_data['report_type'],
                period_year=form.cleaned_data['period_year'])
            messages.success(request, f'Отчёт сформирован: {report}.')
            return redirect('reporting:stat_detail', pk=report.pk)
        return render(request, self.template_name, {'form': form})


class StatReportDetailView(RoleRequiredMixin, DetailView):
    roles = REPORTING_EDIT
    model = StatReport
    template_name = 'reporting/stat_detail.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['data'] = json.loads(self.object.data_json)
        return ctx


class StatReportExcelView(RoleRequiredMixin, View):
    """Экспорт отчёта в Excel."""
    roles = REPORTING_EDIT

    def get(self, request, pk):
        report = get_object_or_404(StatReport, pk=pk)
        buf, filename = stat_report_excel(report)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class StatReportPdfView(RoleRequiredMixin, View):
    """Экспорт отчёта в PDF."""
    roles = REPORTING_EDIT

    def get(self, request, pk):
        report = get_object_or_404(StatReport, pk=pk)
        buf, filename = stat_report_pdf(report)
        response = HttpResponse(buf.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


# ---------------- REST API Реестра студентов СПО ----------------

class RegistryApiView(RoleRequiredMixin, TemplateView):
    """Выгрузка в Реестр СПО через REST API (XML) + журнал."""
    roles = INTEGRATION_MGMT
    template_name = 'reporting/registry_api.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['exports'] = RegistryExport.objects.order_by('-created_at')[:10]
        ctx['logs'] = IntegrationLog.objects.filter(
            integration=IntegrationLog.Integration.REGISTRY_API).order_by('-created_at')[:10]
        return ctx

    def post(self, request, *args, **kwargs):
        export_id = request.POST.get('export_id')
        if not export_id:
            messages.error(request, 'Выберите выгрузку для отправки.')
            return redirect('reporting:registry_api')
        export = get_object_or_404(RegistryExport, pk=export_id)
        xml_bytes = export.xml_file.read()
        log = send_to_registry_api(xml_bytes)
        if log.status == IntegrationLog.Status.OK:
            messages.success(request, f'Отправлено в Реестр СПО: {log.status_code}.')
        elif log.status == IntegrationLog.Status.MOCK:
            messages.warning(request, 'Отправка в протокольном режиме (заглушка): '
                                      'реальный сервер не подключён.')
        else:
            messages.error(request, f'Ошибка отправки: {log.response[:200]}')
        return redirect('reporting:registry_api')


# ---------------- СМЭВ ----------------

class SmevView(RoleRequiredMixin, TemplateView):
    """Интеграция с СМЭВ: запросы сведений из госреестров."""
    roles = INTEGRATION_MGMT
    template_name = 'reporting/smev.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = SmevRequestForm(self.request.POST or None)
        ctx['requests'] = SmevRequest.objects.order_by('-request_date')[:15]
        return ctx

    def post(self, request, *args, **kwargs):
        form = SmevRequestForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            req = smev_request(data['registry'], data['identifier'],
                               person_name=data['person_name'])
            if req.status == SmevRequest.Status.NO_CONNECTION:
                messages.warning(request, 'Подключение к СМЭВ не настроено — запрос зафиксирован.')
            else:
                messages.success(request, 'Сведения получены из реестра.')
            return redirect('reporting:smev')
        return render(request, self.template_name, {'form': form})


# ---------------- Журнал интеграций ----------------

class IntegrationLogListView(RoleRequiredMixin, ListView):
    roles = INTEGRATION_MGMT
    model = IntegrationLog
    template_name = 'reporting/logs.html'
    context_object_name = 'logs'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        integration = self.request.GET.get('integration')
        if integration:
            qs = qs.filter(integration=integration)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['selected_integration'] = self.request.GET.get('integration', '')
        return ctx
