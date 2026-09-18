# -*- coding: utf-8 -*-
"""
Роли и права доступа ИС колледжа.

Роли реализованы группами Django (django.contrib.auth.Group).
Список ролей и их допустимые разделы заданы здесь и используются
миксином RoleRequiredMixin / декоратором role_required.

Роли:
  director         — директор (полный доступ)
  deputy           — заместитель директора
  head_department  — заведующий отделением
  methodist        — методист (учебная часть)
  teacher          — преподаватель
  student          — студент (личный кабинет)
  parent           — родитель (успеваемость ребёнка)
"""

# Имена групп-ролей (совпадают с кодами)
ROLE_DIRECTOR = 'director'
ROLE_DEPUTY = 'deputy'
ROLE_HEAD = 'head_department'
ROLE_METHODIST = 'methodist'
ROLE_TEACHER = 'teacher'
ROLE_STUDENT = 'student'
ROLE_PARENT = 'parent'

ALL_ROLES = [
    ROLE_DIRECTOR, ROLE_DEPUTY, ROLE_HEAD, ROLE_METHODIST,
    ROLE_TEACHER, ROLE_STUDENT, ROLE_PARENT,
]

ROLE_LABELS = {
    ROLE_DIRECTOR: 'Директор',
    ROLE_DEPUTY: 'Заместитель директора',
    ROLE_HEAD: 'Заведующий отделением',
    ROLE_METHODIST: 'Методист',
    ROLE_TEACHER: 'Преподаватель',
    ROLE_STUDENT: 'Студент',
    ROLE_PARENT: 'Родитель',
}

# --- Наборы ролей для разделов ---

# Административно-управленческий персонал (учебная часть)
ACADEMIC_STAFF = [ROLE_DIRECTOR, ROLE_DEPUTY, ROLE_HEAD, ROLE_METHODIST]
# Ведение контингента, групп, приказов
CONTINGENT_EDIT = ACADEMIC_STAFF
# Журнал: проведение занятий, отметки
JOURNAL_EDIT = [ROLE_TEACHER] + ACADEMIC_STAFF
# Уведомления о низкой успеваемости
LOW_PERF_VIEW = [ROLE_TEACHER] + ACADEMIC_STAFF
# Аттестация: расписание и результаты
ATTESTATION_EDIT = [ROLE_TEACHER, ROLE_METHODIST, ROLE_HEAD, ROLE_DEPUTY, ROLE_DIRECTOR]
# Задолженности и стипендия
ATTESTATION_MGMT = [ROLE_METHODIST, ROLE_HEAD, ROLE_DEPUTY, ROLE_DIRECTOR]
# Расписание: редактирование (автопостроение, занятия, замены, публикация)
SCHEDULE_EDIT = ACADEMIC_STAFF
# Кадры: полный доступ
HR_MGMT = [ROLE_DIRECTOR, ROLE_DEPUTY]
# Кадры: просмотр
HR_VIEW = [ROLE_DIRECTOR, ROLE_DEPUTY, ROLE_HEAD, ROLE_METHODIST]
# Отчётность: формирование и экспорт
REPORTING_EDIT = [ROLE_METHODIST, ROLE_HEAD, ROLE_DEPUTY, ROLE_DIRECTOR]
# Интеграции (REST API, СМЭВ)
INTEGRATION_MGMT = [ROLE_DEPUTY, ROLE_DIRECTOR]
