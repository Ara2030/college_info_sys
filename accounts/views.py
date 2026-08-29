# -*- coding: utf-8 -*-
"""
Представления модуля «Авторизация и роли».

  LoginView  — вход в систему (Django LoginView + шаблон)
  LogoutView — выход
  ProfileView — личный кабинет пользователя по его роли:
      студент — успеваемость и расписание группы;
      родитель — успеваемость ребёнка;
      сотрудник/преподаватель — расписание преподавателя, карточка.
"""
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from .access import has_role
from .models import UserProfile
from .roles import (ROLE_PARENT, ROLE_STUDENT, ROLE_TEACHER,
                    ACADEMIC_STAFF)


class AppLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class AppLogoutView(LogoutView):
    next_page = '/accounts/login/'


class ProfileView(LoginRequiredMixin, TemplateView):
    """Личный кабинет: содержимое зависит от роли пользователя."""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        profile, _ = UserProfile.objects.get_or_create(user=user)
        ctx['profile'] = profile
        ctx['is_admin'] = user.is_superuser
        ctx['roles'] = profile.role_names or (['Администратор'] if user.is_superuser else [])

        # --- Студент ---
        if profile.student_id:
            ctx['mode'] = 'student'
            ctx['student'] = profile.student
            from journal.services import (student_average_grade,
                                          student_attendance_percent,
                                          student_is_low_performance)
            from journal.models import Grade
            ctx['avg_grade'] = student_average_grade(profile.student)
            ctx['attendance_percent'] = student_attendance_percent(profile.student)
            ctx['is_low'] = student_is_low_performance(profile.student)
            ctx['recent_grades'] = (Grade.objects.filter(student=profile.student)
                                    .select_related('lesson', 'lesson__subject')
                                    .order_by('-lesson__date')[:10])
            return ctx

        # --- Родитель ---
        if profile.parent_of_id:
            ctx['mode'] = 'parent'
            ctx['child'] = profile.parent_of
            from journal.services import (student_average_grade,
                                          student_attendance_percent,
                                          student_is_low_performance)
            from journal.models import Grade
            ctx['avg_grade'] = student_average_grade(profile.parent_of)
            ctx['attendance_percent'] = student_attendance_percent(profile.parent_of)
            ctx['is_low'] = student_is_low_performance(profile.parent_of)
            ctx['recent_grades'] = (Grade.objects.filter(student=profile.parent_of)
                                    .select_related('lesson', 'lesson__subject')
                                    .order_by('-lesson__date')[:10])
            return ctx

        # --- Сотрудник / преподаватель ---
        if profile.employee_id:
            ctx['mode'] = 'employee'
            ctx['employee'] = profile.employee
            from schedule.models import ScheduleEntry
            teacher = profile.employee.teacher
            ctx['has_teacher'] = teacher is not None
            if teacher:
                ctx['entries_count'] = ScheduleEntry.objects.filter(
                    teacher=teacher).count()
            return ctx

        # --- Административный персонал (без привязки) ---
        ctx['mode'] = 'staff'
        if has_role(user, ACADEMIC_STAFF) or user.is_superuser:
            ctx['is_academic_staff'] = True
        return ctx
