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
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (CreateView, DeleteView, ListView, TemplateView,
                                  UpdateView)

from .access import RoleRequiredMixin, has_role
from .forms import UserCreateForm
from .middleware import get_client_ip
from .models import AuditLog, LoginAttempt, UserProfile
from .roles import (ROLE_DIRECTOR, ROLE_LABELS, ROLE_PARENT, ROLE_STUDENT,
                    ROLE_TEACHER, ACADEMIC_STAFF)

# Роли, которым доступно управление пользователями
USER_MGMT = [ROLE_DIRECTOR]


class AppLoginView(LoginView):
    """Вход в систему с защитой от перебора паролей (brute-force)."""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    # Демонстрационные учётные записи для быстрого входа (только при DEBUG)
    DEMO_ACCOUNTS = [
        {'label': 'Администратор', 'username': 'admin', 'password': 'admin123',
         'icon': '⚙️', 'hint': 'полный доступ'},
        {'label': 'Директор', 'username': 'director', 'password': 'director123',
         'icon': '👔', 'hint': 'руководство'},
        {'label': 'Методист', 'username': 'methodist', 'password': 'methodist123',
         'icon': '📋', 'hint': 'учебная часть'},
        {'label': 'Преподаватель', 'username': 'teacher1', 'password': 'teacher123',
         'icon': '👨‍🏫', 'hint': 'журнал'},
        {'label': 'Студент', 'username': 'student1', 'password': 'student123',
         'icon': '🎓', 'hint': 'личный кабинет'},
        {'label': 'Родитель', 'username': 'parent1', 'password': 'parent123',
         'icon': '👨‍👩‍👦', 'hint': 'успеваемость ребёнка'},
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Кнопки быстрого входа показываем только в режиме отладки (демонстрация)
        if settings.DEBUG:
            ctx['demo_accounts'] = self.DEMO_ACCOUNTS
        return ctx

    def post(self, request, *args, **kwargs):
        from datetime import timedelta
        from .models import AuditLog as AL

        # Быстрый вход: подстановка логина/пароля из демо-кнопки (только DEBUG)
        if settings.DEBUG and request.POST.get('demo_user'):
            for acc in self.DEMO_ACCOUNTS:
                if acc['username'] == request.POST.get('demo_user'):
                    request.POST = request.POST.copy()
                    request.POST['username'] = acc['username']
                    request.POST['password'] = acc['password']
                    break

        username = request.POST.get('username', '')
        ip = get_client_ip(request)
        window = timezone.now() - timedelta(minutes=settings.LOGIN_ATTEMPTS_WINDOW)
        fails = LoginAttempt.objects.filter(
            success=False, created_at__gte=window,
        ).filter(Q(username=username) | Q(ip_address=ip)).count()

        if fails >= settings.LOGIN_ATTEMPTS_LIMIT:
            AL.objects.create(
                username=username, action=AL.Action.LOCKOUT,
                description=f'Блокировка входа: {fails} неудачных попыток',
                ip_address=ip, path=request.path, method='POST',
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:300])
            return render(request, self.template_name, {
                'lockout': True,
                'lockout_minutes': settings.LOGIN_LOCKOUT_MINUTES,
                'attempts': fails,
            }, status=429)
        return super().post(request, *args, **kwargs)


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


# ---------------- Управление пользователями (администратор) ----------------

class UserListView(RoleRequiredMixin, ListView):
    """Список пользователей системы с ролями и привязками."""
    roles = USER_MGMT
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        return User.objects.prefetch_related('groups', 'profile').order_by('username')


class UserCreateView(RoleRequiredMixin, TemplateView):
    """Создание учётной записи: логин, пароль, роль, привязка к объекту."""
    roles = USER_MGMT
    template_name = 'accounts/user_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = UserCreateForm(self.request.POST or None)
        return ctx

    def post(self, request, *args, **kwargs):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                username=data['username'], password=data['password'],
                last_name=data.get('last_name', ''), first_name=data.get('first_name', ''),
                email=data.get('email', ''))
            role = data['role']
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)
            if role in ('director', 'deputy', 'methodist'):
                user.is_staff = True
                user.save(update_fields=['is_staff'])
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'student': data.get('student'),
                          'employee': data.get('employee'),
                          'parent_of': data.get('parent_of')})
            messages.success(request, f'Учётная запись «{user.username}» создана '
                                      f'(роль: {ROLE_LABELS.get(role, role)}).')
            return redirect('accounts:user_list')
        return render(request, self.template_name, {'form': form})


class UserDeleteView(RoleRequiredMixin, DeleteView):
    roles = USER_MGMT
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object == request.user:
            messages.error(request, 'Нельзя удалить собственную учётную запись.')
            return redirect('accounts:user_list')
        if self.object.is_superuser:
            messages.error(request, 'Нельзя удалить суперпользователя.')
            return redirect('accounts:user_list')
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Учётная запись удалена.')
        return super().form_valid(form)


# ---------------- Безопасность: журнал аудита и попытки входа ----------------

class SecurityLogView(RoleRequiredMixin, TemplateView):
    """Журнал безопасности: аудит действий и попытки входа."""
    roles = USER_MGMT
    template_name = 'accounts/security_log.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        action = self.request.GET.get('action')
        logs = AuditLog.objects.select_related('user').order_by('-created_at')
        if action:
            logs = logs.filter(action=action)
        ctx['logs'] = logs[:200]
        ctx['selected_action'] = action or ''
        ctx['actions'] = AuditLog.Action.choices
        ctx['attempts'] = LoginAttempt.objects.order_by('-created_at')[:50]
        ctx['failed_count'] = LoginAttempt.objects.filter(success=False).count()
        ctx['access_denied_count'] = AuditLog.objects.filter(
            action=AuditLog.Action.ACCESS_DENIED).count()
        ctx['lockout_count'] = AuditLog.objects.filter(
            action=AuditLog.Action.LOCKOUT).count()
        return ctx
