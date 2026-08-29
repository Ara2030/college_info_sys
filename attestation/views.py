# -*- coding: utf-8 -*-
"""
Представления модуля «Промежуточная аттестация» (2.3).

Расписание экзаменов и зачётов (с ограничениями), экзаменационные ведомости,
внесение результатов, приказы об академических задолженностях,
формирование списков на стипендию.
"""
from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView

from contingent.models import Group
from journal.models import Subject

from .forms import ExamForm, exam_result_formset_factory, ScheduleBuildForm, ScholarshipForm
from .models import (AcademicDebt, Exam, ExamResult, ScholarshipPeriod)
from .services import (build_schedule, build_scholarship_list, create_exam_results,
                       generate_debt_order, sync_debts_from_exam)


# ---------------- Расписание ----------------

class ExamListView(ListView):
    """Расписание экзаменов и зачётов (фильтр по группе)."""
    model = Exam
    template_name = 'attestation/exam_list.html'
    context_object_name = 'exams'
    paginate_by = 30

    def get_queryset(self):
        qs = (Exam.objects.select_related('subject', 'group')
              .order_by('date', 'time', 'group__name'))
        group_id = self.request.GET.get('group')
        if group_id:
            qs = qs.filter(group_id=group_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['groups'] = Group.objects.order_by('name')
        ctx['selected_group'] = self.request.GET.get('group', '')
        ctx['exam_count'] = Exam.objects.filter(exam_type='exam').count()
        ctx['credit_count'] = Exam.objects.filter(exam_type='credit').count()
        return ctx


class ExamCreateView(CreateView):
    model = Exam
    form_class = ExamForm
    template_name = 'attestation/exam_form.html'
    success_url = reverse_lazy('attestation:exam_list')

    def get_initial(self):
        initial = super().get_initial()
        for key in ('group', 'subject', 'date', 'exam_type'):
            if self.request.GET.get(key):
                initial[key] = self.request.GET.get(key)
        return initial

    def form_valid(self, form):
        exam = form.save()
        create_exam_results(exam)   # ведомость: строки по студентам группы
        messages.success(self.request, f'{exam} — ведомость сформирована.')
        return redirect('attestation:exam_detail', pk=exam.pk)


class ExamUpdateView(UpdateView):
    model = Exam
    form_class = ExamForm
    template_name = 'attestation/exam_form.html'
    success_url = reverse_lazy('attestation:exam_list')


class ExamDetailView(DetailView):
    """Ведомость: результаты студентов + внесение оценок."""
    model = Exam
    template_name = 'attestation/exam_detail.html'
    context_object_name = 'exam'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        exam = self.object
        students = exam.group.students.order_by('last_name', 'first_name')
        results = {r.student_id: r for r in exam.results.all()}
        initial = []
        for s in students:
            r = results.get(s.pk)
            if r:
                initial.append({'student': s.pk, 'student_name': s.short_name,
                                'grade': r.grade, 'present': r.present})
            else:
                initial.append({'student': s.pk, 'student_name': s.short_name,
                                'grade': '', 'present': True})
        if self.request.POST:
            ctx['results_formset'] = exam_result_formset_factory(students).__class__(
                self.request.POST, prefix='results')
        else:
            ctx['results_formset'] = exam_result_formset_factory(students).__class__(
                initial=initial, prefix='results')
        ctx['student_count'] = students.count()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        students = self.object.group.students.order_by('last_name', 'first_name')
        formset = exam_result_formset_factory(students).__class__(
            request.POST, prefix='results')
        if formset.is_valid():
            for form in formset.forms:
                data = form.cleaned_data
                student = data.get('student')
                if not student:
                    continue
                ExamResult.objects.update_or_create(
                    exam=self.object, student=student,
                    defaults={'grade': data.get('grade', '') or '',
                              'present': data.get('present', True)},
                )
            created = sync_debts_from_exam(self.object)
            msg = 'Результаты сохранены.'
            if created:
                msg += f' Создано задолженностей: {len(created)}.'
            messages.success(request, msg)
        else:
            messages.error(request, 'Ошибка в форме результатов.')
        return redirect('attestation:exam_detail', pk=self.object.pk)


class ExamPrintView(DetailView):
    """Печатная форма экзаменационной ведомости."""
    model = Exam
    template_name = 'attestation/exam_print.html'
    context_object_name = 'exam'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['results'] = self.object.results.select_related('student').order_by(
            'student__last_name', 'student__first_name')
        return ctx


class ScheduleBuildView(TemplateView):
    """Автоматическое построение расписания с учётом ограничений."""
    template_name = 'attestation/schedule_build.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ScheduleBuildForm(self.request.POST or None)
        return ctx

    def post(self, request, *args, **kwargs):
        form = ScheduleBuildForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            exams = build_schedule(
                group=data['group'],
                subjects=data['subjects'],
                exam_type=data['exam_type'],
                start_date=data['start_date'],
                room=data['room'],
                teacher=data['teacher'],
            )
            messages.success(
                request,
                f'Построено расписание: {len(exams)} {data["exam_type"]}ов. '
                'Интервал между экзаменами — не менее 3 дней, не более одного в день.')
            return redirect('attestation:exam_list')
        return render(request, self.template_name, {'form': form})


# ---------------- Академические задолженности ----------------

class DebtListView(ListView):
    """Журнал академических задолженностей."""
    model = AcademicDebt
    template_name = 'attestation/debt_list.html'
    context_object_name = 'debts'
    paginate_by = 30

    def get_queryset(self):
        qs = (AcademicDebt.objects.select_related('student', 'subject', 'exam')
              .order_by('-created_at', 'student__last_name'))
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_count'] = AcademicDebt.objects.filter(
            status=AcademicDebt.Status.ACTIVE).count()
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class DebtGenerateOrderView(View):
    """Автоматическое формирование приказа об академических задолженностях."""

    def post(self, request):
        try:
            order = generate_debt_order(author=request.user if request.user.is_authenticated else None)
            messages.success(request,
                             f'Приказ №{order.number} от {order.date:%d.%m.%Y} сформирован '
                             f'({order.students_count} пунктов).')
            return redirect('contingent:order_detail', pk=order.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('attestation:debt_list')


class DebtClearView(View):
    """Отметить задолженность как ликвидированную."""

    def post(self, request, pk):
        debt = get_object_or_404(AcademicDebt, pk=pk)
        debt.status = AcademicDebt.Status.CLEARED
        debt.cleared_at = date.today()
        debt.save(update_fields=['status', 'cleared_at'])
        messages.success(request, f'Задолженность {debt} ликвидирована.')
        return redirect('attestation:debt_list')


# ---------------- Стипендия ----------------

class ScholarshipListView(ListView):
    """Стипендиальные периоды."""
    model = ScholarshipPeriod
    template_name = 'attestation/scholarship_list.html'
    context_object_name = 'periods'


class ScholarshipCreateView(TemplateView):
    """Формирование списка студентов, имеющих право на стипендию."""
    template_name = 'attestation/scholarship_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ScholarshipForm(self.request.POST or None)
        return ctx

    def post(self, request, *args, **kwargs):
        form = ScholarshipForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            period = build_scholarship_list(
                period_start=data['period_start'],
                period_end=data['period_end'],
            )
            messages.success(
                request,
                f'Список на стипендию сформирован: {period.students_count} студентов.')
            return redirect('attestation:scholarship_detail', pk=period.pk)
        return render(request, self.template_name, {'form': form})


class ScholarshipDetailView(DetailView):
    """Список студентов, имеющих право на стипендию."""
    model = ScholarshipPeriod
    template_name = 'attestation/scholarship_detail.html'
    context_object_name = 'period'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['students'] = self.object.students.select_related('group', 'specialty').order_by(
            'group__name', 'last_name', 'first_name')
        return ctx
