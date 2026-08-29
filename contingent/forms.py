"""Формы модуля «Контингент студентов» (2.1)."""
import re

from django import forms

from .models import (Student, Group, Order, OrderItem, AcademicLeave,
                     StudentDocument, ParentInfo)

SNILS_RE = re.compile(r'^\d{3}-\d{3}-\d{3} \d{2}$')


class BootstrapFormMixin:
    """Добавляет Bootstrap-классы всем полям формы."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.TextInput, forms.NumberInput, forms.EmailInput,
                                   forms.URLInput, forms.DateInput, forms.TimeInput,
                                   forms.Select, forms.Textarea, forms.ClearableFileInput)):
                widget.attrs.setdefault('class', 'form-control')
            if isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')


class StudentForm(BootstrapFormMixin, forms.ModelForm):
    """Карточка студента: личные данные + учёба + контакты + адрес."""

    class Meta:
        model = Student
        fields = ('last_name', 'first_name', 'middle_name', 'birth_date', 'gender',
                  'snils', 'citizenship', 'group', 'specialty', 'status',
                  'student_card_number', 'enroll_date',
                  'phone', 'email',
                  'address_index', 'address_city', 'address_street',
                  'address_house', 'address_flat', 'note')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'enroll_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_snils(self):
        snils = self.cleaned_data.get('snils', '').strip()
        if not snils:
            return ''
        if not SNILS_RE.fullmatch(snils):
            raise forms.ValidationError('Формат СНИЛС: 123-456-789 01')
        return snils

    def clean(self):
        cleaned = super().clean()
        group = cleaned.get('group')
        specialty = cleaned.get('specialty')
        if group and specialty and group.specialty_id != specialty.id:
            self.add_error('specialty', forms.ValidationError(
                f'Специальность группы «{group.name}» — {group.specialty.code}. '
                'Выберите её либо поменяйте группу.'
            ))
        return cleaned


class GroupForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name', 'specialty', 'department', 'course',
                  'enroll_year', 'curator', 'is_active')


class OrderForm(BootstrapFormMixin, forms.ModelForm):
    """Реквизиты приказа (пункты — отдельным формсетом)."""

    class Meta:
        model = Order
        fields = ('number', 'date', 'order_type', 'title', 'comment')
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}


class OrderItemForm(BootstrapFormMixin, forms.ModelForm):
    """Один пункт приказа: студент + действие."""

    class Meta:
        model = OrderItem
        fields = ('student', 'action', 'group_from', 'group_to', 'basis', 'comment')
        widgets = {
            'basis': forms.TextInput(attrs={'placeholder': 'Основание / причина'}),
            'comment': forms.TextInput(attrs={'placeholder': 'Примечание'}),
        }


OrderItemFormSet = forms.inlineformset_factory(
    Order, OrderItem, form=OrderItemForm, extra=3, can_delete=True,
)


class AcademicLeaveForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AcademicLeave
        fields = ('student', 'order', 'date_from', 'date_to', 'reason', 'is_active')
        widgets = {
            'date_from': forms.DateInput(attrs={'type': 'date'}),
            'date_to': forms.DateInput(attrs={'type': 'date'}),
        }


class StudentDocumentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = StudentDocument
        fields = ('doc_type', 'series', 'number', 'issue_date', 'issued_by',
                  'issue_code', 'is_main')
        widgets = {'issue_date': forms.DateInput(attrs={'type': 'date'})}


class ParentInfoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ParentInfo
        fields = ('last_name', 'first_name', 'middle_name', 'phone')
