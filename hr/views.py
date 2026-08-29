# -*- coding: utf-8 -*-
"""
Представления модуля «Кадровый учёт» (2.5).

Личные карточки сотрудников (Т-2), штатное расписание, тарификация нагрузки,
выгрузка в «1С:Зарплата», приказы по личному составу.
"""
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView

from .forms import (EmployeeForm, HROrderForm, StaffPositionForm,
                    TarificationItemForm, TarificationPeriodForm)
from .models import (Employee, HROrder, SalaryExport, StaffPosition,
                     StaffingUnit, TarificationItem, TarificationPeriod)
from .services import (apply_hr_order, build_salary_export,
                       build_tarification_from_curriculum)


# ---------------- Дашборд кадров ----------------

class HrDashboardView(TemplateView):
    template_name = 'hr/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        employees = Employee.objects.all()
        ctx['total'] = employees.count()
        ctx['active'] = employees.filter(status=Employee.Status.ACTIVE).count()
        ctx['teachers'] = employees.filter(category=Employee.Category.TEACHER,
                                           status=Employee.Status.ACTIVE).count()
        ctx['management'] = employees.filter(category=Employee.Category.MANAGEMENT,
                                             status=Employee.Status.ACTIVE).count()
        ctx['support'] = employees.filter(category=Employee.Category.SUPPORT,
                                          status=Employee.Status.ACTIVE).count()
        ctx['positions'] = StaffPosition.objects.count()
        ctx['vacancies'] = sum(1 for p in StaffPosition.objects.all() if p.vacancy_rate > 0)
        ctx['tarification_count'] = TarificationPeriod.objects.count()
        ctx['orders_count'] = HROrder.objects.count()
        ctx['exports_count'] = SalaryExport.objects.count()
        return ctx


# ---------------- Сотрудники (Т-2) ----------------

class EmployeeListView(ListView):
    model = Employee
    template_name = 'hr/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        q = self.request.GET.get('q', '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(last_name__icontains=q) | Q(first_name__icontains=q) |
                           Q(position__icontains=q) | Q(snils__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class EmployeeCreateView(CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')


class EmployeeDetailView(DetailView):
    """Личная карточка сотрудника (форма Т-2)."""
    model = Employee
    template_name = 'hr/employee_detail.html'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        emp = self.object
        ctx['staffing'] = emp.staffing_units.select_related('position')
        ctx['tarification'] = (TarificationItem.objects.filter(employee=emp)
                               .select_related('subject', 'period').order_by('period__year_start'))
        ctx['orders'] = emp.hr_orders.order_by('-date')
        return ctx


class EmployeeUpdateView(UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')


class EmployeeCardView(DetailView):
    """Печатная форма карточки Т-2."""
    model = Employee
    template_name = 'hr/employee_card.html'
    context_object_name = 'employee'


# ---------------- Штатное расписание ----------------

class StaffingView(TemplateView):
    """Штатное расписание: должности, занятые ставки, вакансии."""
    template_name = 'hr/staffing.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['positions'] = StaffPosition.objects.prefetch_related('units__employee').order_by('title')
        ctx['total_positions'] = StaffPosition.objects.count()
        ctx['vacancies'] = sum(1 for p in StaffPosition.objects.all() if p.vacancy_rate > 0)
        ctx['filled'] = StaffingUnit.objects.exclude(employee=None).count()
        return ctx


class StaffPositionCreateView(CreateView):
    model = StaffPosition
    form_class = StaffPositionForm
    template_name = 'hr/position_form.html'
    success_url = reverse_lazy('hr:staffing')


# ---------------- Тарификация ----------------

class TarificationListView(ListView):
    model = TarificationPeriod
    template_name = 'hr/tarification_list.html'
    context_object_name = 'periods'


class TarificationCreateView(CreateView):
    model = TarificationPeriod
    form_class = TarificationPeriodForm
    template_name = 'hr/tarification_form.html'
    success_url = reverse_lazy('hr:tarification_list')

    def form_valid(self, form):
        period = form.save()
        if form.cleaned_data.get('import_from_plan'):
            count = build_tarification_from_curriculum(period)
            messages.success(self.request,
                             f'Тарификация «{period.name}» создана. '
                             f'Строк из учебного плана: {count}.')
        else:
            messages.success(self.request, f'Тарификация «{period.name}» создана.')
        return redirect('hr:tarification_detail', pk=period.pk)


class TarificationDetailView(DetailView):
    model = TarificationPeriod
    template_name = 'hr/tarification_detail.html'
    context_object_name = 'period'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        period = self.object
        ctx['items'] = (period.items.select_related('employee', 'subject')
                        .order_by('employee__last_name', 'subject__name'))
        ctx['by_employee'] = {}
        for item in ctx['items']:
            key = item.employee_id
            if key not in ctx['by_employee']:
                ctx['by_employee'][key] = {'employee': item.employee, 'hours': 0, 'items': []}
            ctx['by_employee'][key]['hours'] += item.total_hours
            ctx['by_employee'][key]['items'].append(item)
        return ctx


class TarificationItemCreateView(CreateView):
    model = TarificationItem
    form_class = TarificationItemForm
    template_name = 'hr/tarification_item_form.html'

    def get_initial(self):
        return {'period': self.kwargs['period_pk']}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['period'] = get_object_or_404(TarificationPeriod, pk=self.kwargs['period_pk'])
        return ctx

    def form_valid(self, form):
        form.instance.period = get_object_or_404(
            TarificationPeriod, pk=self.kwargs['period_pk'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('hr:tarification_detail', kwargs={'pk': self.kwargs['period_pk']})


# ---------------- Выгрузка в 1С:Зарплата ----------------

class SalaryExportListView(ListView):
    model = SalaryExport
    template_name = 'hr/salary_list.html'
    context_object_name = 'exports'


class SalaryExportCreateView(TemplateView):
    """Формирование выгрузки в 1С:Зарплата по периоду тарификации."""
    template_name = 'hr/salary_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['periods'] = TarificationPeriod.objects.prefetch_related('items').order_by('-year_start')
        return ctx

    def post(self, request, *args, **kwargs):
        period_id = request.POST.get('period')
        if not period_id:
            messages.error(request, 'Выберите период тарификации.')
            return redirect('hr:salary_create')
        period = get_object_or_404(TarificationPeriod, pk=period_id)
        export = build_salary_export(period)
        messages.success(
            request,
            f'Выгрузка сформирована: {export.file_name} — {export.employee_count} '
            f'сотрудников, {export.total_hours} часов.')
        return redirect('hr:salary_list')


class SalaryExportDownloadView(View):
    def get(self, request, pk):
        export = get_object_or_404(SalaryExport, pk=pk)
        if not export.json_file:
            raise Http404('Файл отсутствует')
        return FileResponse(export.json_file.open('rb'), as_attachment=True,
                            filename=export.file_name)


# ---------------- Приказы по личному составу ----------------

class HROrderListView(ListView):
    model = HROrder
    template_name = 'hr/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('employee')
        order_type = self.request.GET.get('type')
        if order_type:
            qs = qs.filter(order_type=order_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['selected_type'] = self.request.GET.get('type', '')
        return ctx


class HROrderCreateView(CreateView):
    model = HROrder
    form_class = HROrderForm
    template_name = 'hr/order_form.html'

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get('employee'):
            initial['employee'] = self.request.GET['employee']
        return initial

    def form_valid(self, form):
        self.object = form.save()
        apply_hr_order(self.object)
        messages.success(
            self.request,
            f'Приказ №{self.object.number} сохранён и применён к карточке сотрудника.')
        return redirect('hr:order_detail', pk=self.object.pk)


class HROrderDetailView(DetailView):
    model = HROrder
    template_name = 'hr/order_detail.html'
    context_object_name = 'order'


class HROrderPrintView(DetailView):
    model = HROrder
    template_name = 'hr/order_print.html'
    context_object_name = 'order'
