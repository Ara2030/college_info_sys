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

print(f'Готово: отделений={Department.objects.count()}, '
      f'специальностей={Specialty.objects.count()}, '
      f'групп={Group.objects.count()}, '
      f'студентов={Student.objects.count()} (создано новых: {created}), '
      f'типов приказов={OrderType.objects.count()}')
