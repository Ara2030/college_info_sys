# -*- coding: utf-8 -*-
"""Заполнение базы тестовыми данными (демо-данные для дипломного проекта)."""
import os
import random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from contingent.models import (Department, Specialty, Group, Student,
                               StudentStatus, OrderType)

random.seed(42)

# --- Отделения (4) ---
departments = [
    ('Информационные технологии', 'ИТ', 'Иванов И.И.'),
    ('Электроэнергетика', 'ЭЭ', 'Петров П.П.'),
    ('Экономика и управление', 'ЭУ', 'Сидорова С.С.'),
    ('Общеобразовательное отделение', 'ОО', 'Кузнецов К.К.'),
]
for name, code, head in departments:
    Department.objects.get_or_create(code=code, defaults={'name': name, 'head': head})

# --- Специальности (8) ---
specs = [
    ('09.02.05', 'Прикладная информатика (по отраслям)', 'Программист', 'ИТ', 46),
    ('09.02.07', 'Информационные системы и программирование', 'Разработчик веб и мультимедийных приложений', 'ИТ', 46),
    ('13.02.03', 'Электрические станции, сети и системы', 'Техник-электрик', 'ЭЭ', 46),
    ('13.02.11', 'Техническая эксплуатация и обслуживание электрического и электромеханического оборудования', 'Техник', 'ЭЭ', 46),
    ('38.02.01', 'Экономика и бухгалтерский учёт', 'Бухгалтер', 'ЭУ', 34),
    ('38.02.04', 'Коммерция (по отраслям)', 'Менеджер по продажам', 'ЭУ', 34),
    ('40.02.01', 'Право и организация социального обеспечения', 'Юрист', 'ЭУ', 34),
    ('44.02.02', 'Преподавание в начальных классах', 'Учитель начальных классов', 'ОО', 46),
]
spec_objects = {}
for code, name, qual, dep_code, months in specs:
    dep = Department.objects.get(code=dep_code)
    obj, _ = Specialty.objects.get_or_create(
        code=code, defaults={'name': name, 'qualification': qual, 'department': dep, 'duration_months': months})
    spec_objects[code] = obj

# --- Группы (примерно 12) ---
groups_data = [
    ('ИС-11', '09.02.05', 'ИТ', 1, 2025),
    ('ИС-21', '09.02.05', 'ИТ', 2, 2024),
    ('ИС-31', '09.02.05', 'ИТ', 3, 2023),
    ('ИСП-11', '09.02.07', 'ИТ', 1, 2025),
    ('ИСП-21', '09.02.07', 'ИТ', 2, 2024),
    ('Э-11', '13.02.03', 'ЭЭ', 1, 2025),
    ('Э-21', '13.02.03', 'ЭЭ', 2, 2024),
    ('Э-31', '13.02.03', 'ЭЭ', 3, 2023),
    ('ЭМ-11', '13.02.11', 'ЭЭ', 1, 2025),
    ('Б-21', '38.02.01', 'ЭУ', 2, 2024),
    ('К-11', '38.02.04', 'ЭУ', 1, 2025),
    ('П-31', '40.02.01', 'ЭУ', 3, 2023),
]
group_objects = {}
for name, spec_code, dep_code, course, year in groups_data:
    spec = spec_objects[spec_code]
    dep = Department.objects.get(code=dep_code)
    obj, _ = Group.objects.get_or_create(
        name=name, defaults={'specialty': spec, 'department': dep, 'course': course, 'enroll_year': year})
    group_objects[name] = obj

# --- Студенты (по 6 на группу = 72) ---
last_names = ['Иванов', 'Петров', 'Сидоров', 'Кузнецов', 'Смирнов', 'Волков',
              'Козлов', 'Морозов', 'Соколов', 'Павлов', 'Орлов', 'Фёдоров']
first_names = ['Алексей', 'Дмитрий', 'Сергей', 'Андрей', 'Максим', 'Иван',
               'Елена', 'Ольга', 'Мария', 'Анна', 'Наталья', 'Татьяна']
middle_names = ['Иванович', 'Петрович', 'Сергеевич', 'Андреевич', 'Александрович', 'Викторович']

created = 0
snils_seen = set()
for gname, group in group_objects.items():
    for i in range(6):
        ln = random.choice(last_names)
        fn = random.choice(first_names)
        mn = random.choice(middle_names)
        snils = f'{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)} {random.randint(10, 99)}'
        guard = 0
        while snils in snils_seen and guard < 50:
            snils = f'{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)} {random.randint(10, 99)}'
            guard += 1
        snils_seen.add(snils)
        birth = date(random.randint(2006, 2009), random.randint(1, 12), random.randint(1, 28))
        enroll = date(group.enroll_year, 9, 1)
        card = f'{gname}-{i+1:03d}'
        obj, was_created = Student.objects.get_or_create(
            snils=snils,
            defaults={
                'last_name': ln, 'first_name': fn, 'middle_name': mn,
                'birth_date': birth, 'gender': 'М' if fn[-1] not in ('а', 'я') else 'Ж',
                'group': group, 'specialty': group.specialty,
                'status': StudentStatus.STUDY,
                'student_card_number': card, 'enroll_date': enroll,
                'phone': f'+7 (9{random.randint(10,99)}) {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}',
                'email': f'student{card}@college.ru',
                'address_index': '123456', 'address_city': 'Москва',
                'address_street': 'Ул. Образцовая', 'address_house': str(random.randint(1, 40)),
                'address_flat': str(random.randint(1, 200)),
            })
        if was_created:
            created += 1

# --- Типы приказов ---
order_types = [
    ('enroll', 'Зачисление', 'Приказ о зачислении'),
    ('expel', 'Отчисление', 'Приказ об отчислении'),
    ('transfer', 'Перевод', 'Приказ о переводе'),
    ('academic_leave', 'Академический отпуск', 'Приказ о предоставлении академического отпуска'),
    ('recover', 'Восстановление', 'Приказ о восстановлении'),
]
for code, name, doc_name in order_types:
    OrderType.objects.get_or_create(code=code, defaults={'name': name, 'document_name': doc_name})

# ==========================================================================
# Модуль 2.2 «Электронный журнал»: дисциплины, занятия, оценки, посещаемость
# ==========================================================================
from journal.models import Subject, Lesson, Grade, Attendance  # noqa: E402

# Дисциплины для IT-групп
subject_names = [
    'Информатика', 'Математика', 'Базы данных', 'Программирование',
    'Операционные системы', 'Компьютерные сети', 'Физика', 'Иностранный язык',
]
subject_objs = []
for name in subject_names:
    subj, _ = Subject.objects.get_or_create(
        name=name, defaults={'code': name[:2].upper(), 'teacher': f'Преподаватель {name}'})
    subject_objs.append(subj)

# Занятия + отметки: для каждой группы проводим по 4 занятия (2 дисциплины × 2)
lessons_created = 0
grades_created = 0
att_created = 0
for group in Group.objects.all():
    group_subjects = subject_objs[:2]  # для простоты берём первые 2 дисциплины
    for subject in group_subjects:
        for week in (1, 2):
            lesson_date = date(group.enroll_year + group.course - 1, 9, 1 + (week - 1) * 7)
            lesson, was_created = Lesson.objects.get_or_create(
                subject=subject, group=group, date=lesson_date, lesson_number=week,
                defaults={'topic': f'{subject.name} — занятие {week}', 'teacher': subject.teacher})
            if was_created:
                lessons_created += 1
            # Отметки для каждого студента группы
            for student in group.students.all():
                present = random.random() > 0.15  # ~85% посещаемость, у некоторых хуже
                if present and random.random() < 0.1:
                    present = False  # искусственно добавляем пропускающих
                Grade.objects.get_or_create(
                    lesson=lesson, student=student,
                    defaults={'value': random.choice(['5', '4', '4', '3', '3', '2'])})
                Attendance.objects.get_or_create(
                    lesson=lesson, student=student, defaults={'present': present})
                grades_created += 1
                att_created += 1

print(f'Готово: отделений={Department.objects.count()}, '
      f'специальностей={Specialty.objects.count()}, '
      f'групп={Group.objects.count()}, '
      f'студентов={Student.objects.count()} (создано новых: {created}), '
      f'типов приказов={OrderType.objects.count()}, '
      f'дисциплин={Subject.objects.count()}, '
      f'занятий={Lesson.objects.count()} (создано: {lessons_created}), '
      f'оценок={Grade.objects.count()} (создано: {grades_created}), '
      f'записей посещаемости={Attendance.objects.count()} (создано: {att_created})')
