# -*- coding: utf-8 -*-
"""Формы модуля «Авторизация и роли»."""
from django import forms
from django.contrib.auth.models import User

from contingent.models import Student
from hr.models import Employee
from .models import UserProfile
from .roles import ROLE_LABELS


class UserCreateForm(forms.Form):
    """Создание учётной записи администратором: логин, пароль, роль, привязка."""

    username = forms.CharField(
        label='Логин', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(
        label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(
        label='Фамилия', max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(
        label='Имя', max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(
        label='E-mail', required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        label='Роль', choices=[(k, v) for k, v in ROLE_LABELS.items()],
        widget=forms.Select(attrs={'class': 'form-select'}))
    student = forms.ModelChoiceField(
        label='Связать со студентом (для роли «Студент»)', required=False,
        queryset=Student.objects.order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'form-select'}))
    employee = forms.ModelChoiceField(
        label='Связать с сотрудником (для роли «Преподаватель»)', required=False,
        queryset=Employee.objects.order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'form-select'}))
    parent_of = forms.ModelChoiceField(
        label='Ребёнок (для роли «Родитель»)', required=False,
        queryset=Student.objects.order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'form-select'}))

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Пользователь с таким логином уже существует.')
        return username

    def clean_student(self):
        student = self.cleaned_data.get('student')
        if student and UserProfile.objects.filter(student=student).exists():
            raise forms.ValidationError(
                'Для этого студента уже создана учётная запись. '
                'Выберите другого студента.')
        return student

    def clean_employee(self):
        employee = self.cleaned_data.get('employee')
        if employee and UserProfile.objects.filter(employee=employee).exists():
            raise forms.ValidationError(
                'Для этого сотрудника уже создана учётная запись. '
                'Выберите другого сотрудника.')
        return employee

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        # Проверка соответствия привязки роли
        if role == 'student' and not cleaned.get('student'):
            self.add_error('student', 'Для роли «Студент» выберите студента.')
        if role == 'parent' and not cleaned.get('parent_of'):
            self.add_error('parent_of', 'Для роли «Родитель» выберите ребёнка.')
        return cleaned
