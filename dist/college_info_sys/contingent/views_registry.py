# -*- coding: utf-8 -*-
"""
Экраны выгрузки в Реестр СПО (модуль 2.1 «Контингент студентов»).

Маршруты (добавить в contingent/urls.py):
    path('exports/', views_registry.export_registry_list, name='export_list'),
    path('exports/<int:pk>/', views_registry.export_registry_detail, name='export_detail'),
    path('exports/<int:pk>/download/', views_registry.export_registry_download, name='export_download'),
"""
from django import forms
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from contingent.models import Group, RegistryExport, Student, StudentStatus
from contingent.services.registry_export import create_registry_export

# Варианты статусов студентов (значения — как в модели Student.status)
STUDENT_STATUS_CHOICES = [
    ("", "Все статусы"),
    (StudentStatus.STUDY, "Обучается"),
    (StudentStatus.ACADEMIC_LEAVE, "Академ. отпуск"),
    (StudentStatus.EXPELLED, "Отчислен"),
    (StudentStatus.GRADUATED, "Окончил обучение"),
]


class RegistryExportForm(forms.Form):
    """Форма параметров формирования выгрузки."""

    period_start = forms.DateField(
        label="Период с",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    period_end = forms.DateField(
        label="Период по",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.order_by("name"),
        required=False,
        label="Группа (необязательно)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        choices=STUDENT_STATUS_CHOICES,
        required=False,
        label="Статус студентов",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    comment = forms.CharField(
        label="Комментарий",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
    )

    def clean(self):
        data = super().clean()
        if data.get("period_start") and data.get("period_end") \
                and data["period_start"] > data["period_end"]:
            self.add_error("period_end", "Дата окончания раньше даты начала периода")
        return data


def export_registry_list(request):
    """Список сформированных выгрузок + форма создания новой."""
    exports = RegistryExport.objects.select_related("group").order_by("-created_at")
    form = RegistryExportForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        students = Student.objects.select_related("group__specialty").all()
        if form.cleaned_data["group"]:
            students = students.filter(group=form.cleaned_data["group"])
        if form.cleaned_data["status"]:
            students = students.filter(status=form.cleaned_data["status"])

        export = create_registry_export(
            students=students,
            period_start=form.cleaned_data["period_start"],
            period_end=form.cleaned_data["period_end"],
            group=form.cleaned_data["group"],
            student_status=form.cleaned_data["status"],
            comment=form.cleaned_data["comment"],
        )
        messages.success(
            request,
            f"Выгрузка сформирована: {export.file_name} "
            f"({export.student_count} студентов, {export.order_count} приказов)",
        )
        return redirect("contingent:export_detail", pk=export.pk)

    return render(request, "contingent/export_list.html", {
        "exports": exports,
        "form": form,
    })


def export_registry_detail(request, pk):
    """Детали выгрузки: метаданные, контрольная сумма, содержимое XML."""
    export = get_object_or_404(RegistryExport, pk=pk)
    xml_content = ""
    try:
        with export.xml_file.open("rb") as f:
            xml_content = f.read().decode("utf-8")
    except (ValueError, OSError):
        xml_content = ""
    return render(request, "contingent/export_detail.html", {
        "export": export,
        "xml_content": xml_content,
    })


def export_registry_download(request, pk):
    """Скачивание XML-файла выгрузки."""
    export = get_object_or_404(RegistryExport, pk=pk)
    if not export.xml_file:
        raise Http404("Файл выгрузки отсутствует")
    return FileResponse(
        export.xml_file.open("rb"),
        as_attachment=True,
        filename=export.file_name,
    )
