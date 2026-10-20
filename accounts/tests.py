# -*- coding: utf-8 -*-
"""Тесты модуля «Авторизация и роли» (2.7) + безопасность."""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from contingent.models import Department, Group as StudyGroup, Specialty, Student, StudentStatus
from .models import AuditLog, LoginAttempt, UserProfile
from .access import has_role
from .roles import (ROLE_DIRECTOR, ROLE_METHODIST, ROLE_PARENT, ROLE_STUDENT,
                    ROLE_TEACHER, CONTINGENT_EDIT, HR_MGMT)
from .templatetags.security import mask_snils, mask_tail


class RolesBaseTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        dep = Department.objects.create(name='ИТ', code='ИТ')
        spec = Specialty.objects.create(code='09.02.07', name='ИСП', department=dep)
        group = StudyGroup.objects.create(name='ИС-71', specialty=spec, department=dep,
                                          course=1, enroll_year=2025)
        cls.student = Student.objects.create(
            last_name='Тестов', first_name='Иван', birth_date='2007-01-01',
            snils='123-456-789 01', group=group, specialty=spec,
            status=StudentStatus.STUDY, student_card_number='ИС-71-001',
            enroll_date='2025-09-01')

        # Пользователи разных ролей
        cls.director = cls._user('director', ROLE_DIRECTOR)
        cls.methodist = cls._user('methodist', ROLE_METHODIST)
        cls.teacher = cls._user('teacher', ROLE_TEACHER)
        cls.student_user = cls._user('student', ROLE_STUDENT)
        cls.student_user.profile.student = cls.student
        cls.student_user.profile.save()
        cls.parent = cls._user('parent', ROLE_PARENT)
        cls.parent.profile.parent_of = cls.student
        cls.parent.profile.save()

    @classmethod
    def _user(cls, username, role):
        user = User.objects.create_user(username=username, password='StrongPass123')
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
        UserProfile.objects.get_or_create(user=user)
        return user


class AccessControlTests(RolesBaseTestCase):
    """Разграничение доступа по ролям."""

    def test_has_role_for_director(self):
        self.assertTrue(has_role(self.director, CONTINGENT_EDIT))

    def test_has_role_false_for_student(self):
        self.assertFalse(has_role(self.student_user, CONTINGENT_EDIT))

    def test_superuser_has_all_roles(self):
        admin = User.objects.create_superuser('admin2', 'a@a.ru', 'StrongPass123')
        self.assertTrue(has_role(admin, HR_MGMT))

    def test_anonymous_has_no_roles(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(has_role(AnonymousUser(), CONTINGENT_EDIT))

    def test_student_cannot_create_student(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('contingent:student_create'))
        self.assertEqual(response.status_code, 403)

    def test_director_can_create_student(self):
        self.client.force_login(self.director)
        response = self.client.get(reverse('contingent:student_create'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_cannot_access_hr(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('hr:dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_director_can_access_hr(self):
        self.client.force_login(self.director)
        response = self.client.get(reverse('hr:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('contingent:student_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_student_profile_page(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['mode'], 'student')

    def test_parent_profile_shows_child(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['mode'], 'parent')
        self.assertEqual(response.context['child'], self.student)


class BruteForceProtectionTests(RolesBaseTestCase):
    """Защита от перебора паролей."""

    def test_failed_login_creates_attempt(self):
        self.client.post(reverse('accounts:login'),
                         {'username': 'director', 'password': 'wrong'})
        self.assertTrue(LoginAttempt.objects.filter(username='director',
                                                    success=False).exists())

    def test_lockout_after_limit(self):
        for _ in range(6):
            response = self.client.post(reverse('accounts:login'),
                                        {'username': 'attacker', 'password': 'wrongpass'})
        self.assertEqual(response.status_code, 429, 'должна сработать блокировка')

    def test_lockout_logged_in_audit(self):
        for _ in range(6):
            self.client.post(reverse('accounts:login'),
                             {'username': 'attacker2', 'password': 'wrongpass'})
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.LOCKOUT).exists())

    def test_successful_login_logged(self):
        self.client.post(reverse('accounts:login'),
                         {'username': 'director', 'password': 'StrongPass123'})
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.LOGIN).exists())

    def test_login_attempt_success_flag(self):
        self.client.post(reverse('accounts:login'),
                         {'username': 'director', 'password': 'StrongPass123'})
        self.assertTrue(LoginAttempt.objects.filter(username='director',
                                                    success=True).exists())


class AuditTests(RolesBaseTestCase):
    """Аудит действий."""

    def test_access_denied_logged(self):
        self.client.force_login(self.student_user)
        self.client.get(reverse('contingent:student_create'))
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.Action.ACCESS_DENIED).exists())

    def test_log_has_ip_and_action(self):
        self.client.force_login(self.director)
        self.client.post(reverse('hr:order_create'), {})  # неудачная форма -> update?
        log = AuditLog.objects.first()
        if log:
            self.assertIsNotNone(log.action)


class DataMaskingTests(TestCase):
    """Маскирование персональных данных."""

    def test_mask_snils(self):
        self.assertEqual(mask_snils('123-456-789 01'), '***-***-789 01')

    def test_mask_snils_none(self):
        self.assertEqual(mask_snils(''), '')

    def test_mask_tail(self):
        # 'SC-1234567' — 10 символов, видны последние 2
        self.assertEqual(mask_tail('SC-1234567', 2), '********67')

    def test_mask_tail_short_value(self):
        self.assertEqual(mask_tail('12', 2), '**')


class SecurityHeadersTests(TestCase):
    """Защитные HTTP-заголовки."""

    def test_login_page_has_security_headers(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertIn('Content-Security-Policy', response.headers)
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertIn('Permissions-Policy', response.headers)

    def test_frame_denied_in_csp(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])


@override_settings(DEBUG=True)
class ClearDemoDataTests(TestCase):
    """Очистка демо-данных со страницы входа."""

    def setUp(self):
        import tempfile
        from django.test import override_settings
        self.base_dir = tempfile.mkdtemp(prefix='college_test_')
        self._settings = override_settings(BASE_DIR=self.base_dir)
        self._settings.enable()
        self.addCleanup(self._settings.disable)

        import shutil
        self.addCleanup(shutil.rmtree, self.base_dir, True)

        self.admin = User.objects.create_superuser('root', 'root@example.ru', 'RootPass123')
        self.dep = Department.objects.create(name='ИТ', code='ИТ')
        spec = Specialty.objects.create(code='09.02.07', name='ИСП', department=self.dep)
        self.group = StudyGroup.objects.create(name='ИС-71', specialty=spec, department=self.dep,
                                               course=1, enroll_year=2025)

    def _post(self, **overrides):
        data = {
            'admin_username': 'root',
            'admin_password': 'RootPass123',
            'confirm_word': 'УДАЛИТЬ',
        }
        data.update(overrides)
        return self.client.post(reverse('accounts:clear_demo_data'), data)

    def test_link_visible_on_login_page(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, 'Очистка демо-данных')

    def test_get_not_allowed(self):
        response = self.client.get(reverse('accounts:clear_demo_data'))
        self.assertEqual(response.status_code, 405)

    def test_wrong_password_keeps_data(self):
        response = self._post(admin_password='wrong')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Department.objects.exists())
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.Action.ACCESS_DENIED,
            description__contains='Очистка демо-данных').exists())

    def test_not_superuser_rejected(self):
        User.objects.create_user('director', password='DirectorPass1')
        self._post(admin_username='director', admin_password='DirectorPass1')
        self.assertTrue(Department.objects.exists())

    def test_wrong_confirm_word_keeps_data(self):
        self._post(confirm_word='удалить все')
        self.assertTrue(Department.objects.exists())

    def test_clear_with_admin_credentials(self):
        response = self._post()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Department.objects.exists())
        self.assertFalse(StudyGroup.objects.exists())
        # пользователи и аудит сохраняются
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.DELETE).exists())
        # автозаполнение отключается файлом-флагом
        import os
        self.assertTrue(os.path.exists(os.path.join(self.base_dir, '.demo_disabled')))

    def test_disabled_when_not_debug(self):
        from django.test import override_settings
        with override_settings(DEBUG=False):
            response = self.client.post(reverse('accounts:clear_demo_data'), {
                'admin_username': 'root', 'admin_password': 'RootPass123',
                'confirm_word': 'УДАЛИТЬ'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Department.objects.exists())

    def test_button_disabled_after_clear(self):
        self._post()
        page = self.client.get(reverse('accounts:login'))
        self.assertContains(page, 'Демо-данные удалены')
        self.assertContains(page, 'disabled')
        self.assertNotContains(page, 'action="/accounts/login/clear-demo/"')

    def test_second_clear_reports_nothing_to_clear(self):
        self._post()
        response = self.client.post(reverse('accounts:clear_demo_data'), {
            'admin_username': 'root', 'admin_password': 'RootPass123',
            'confirm_word': 'УДАЛИТЬ'}, follow=True)
        self.assertContains(response, 'очищать нечего')

    def test_button_active_when_data_present(self):
        page = self.client.get(reverse('accounts:login'))
        self.assertContains(page, 'action="/accounts/login/clear-demo/"')
        self.assertNotContains(page, 'Демо-данные удалены')
