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

# ==========================================================================
# Модуль 2.3 «Промежуточная аттестация»: расписание, ведомости, стипендия
# ==========================================================================
from attestation.models import Exam, ExamResult, AcademicDebt, ScholarshipPeriod  # noqa: E402
from attestation.services import build_schedule, sync_debts_from_exam, \
    build_scholarship_list  # noqa: E402

# Автопостроение расписания экзаменов (с учётом ограничений)
exams_created = 0
for group in Group.objects.all():
    exam_subjects = subject_objs[2:5]  # 3 дисциплины на экзамен
    start = date(group.enroll_year + group.course, 6, 1)  # июньская сессия
    try:
        exams = build_schedule(group=group, subjects=exam_subjects,
                               exam_type='exam', start_date=start)
        exams_created += len(exams)
    except Exception:
        pass

# Зачёты (2 дисциплины, не более одного в день)
credits_created = 0
for group in Group.objects.all():
    credit_subjects = subject_objs[5:7]
    start = date(group.enroll_year + group.course, 5, 20)
    try:
        credits = build_schedule(group=group, subjects=credit_subjects,
                                 exam_type='credit', start_date=start)
        credits_created += len(credits)
    except Exception:
        pass

# Ведомости: результаты + автоматические задолженности
results_created = 0
debts_created = 0
for exam in Exam.objects.all():
    for student in exam.group.students.all():
        # 12% — неуд, 18% — «3», остальное 4–5 (или зачтено для зачётов)
        if exam.is_exam:
            grade = random.choices(
                ['5', '4', '3', '2'],
                weights=[25, 35, 22, 18], k=1)[0] if exam.subject.name != 'Математика' else \
                random.choices(['5', '4', '3', '2'], weights=[30, 30, 25, 15], k=1)[0]
        else:
            grade = random.choices(['pass', 'fail'], weights=[88, 12], k=1)[0]
        present = random.random() > 0.05
        res, was_created = ExamResult.objects.update_or_create(
            exam=exam, student=student,
            defaults={'grade': grade if present else '', 'present': present})
        if was_created:
            results_created += 1
    # Задолженности по неудовлетворительным результатам
    debts_created += len(sync_debts_from_exam(exam))

# Стипендиальный список за «июньскую сессию»
period = build_scholarship_list(
    period_start=date(date.today().year, 5, 20),
    period_end=date(date.today().year, 6, 30),
)
# ==========================================================================
# Модуль 2.4 «Формирование расписания»: аудитории, преподаватели, план
# ==========================================================================
from schedule.models import Room, Teacher, Curriculum, ScheduleEntry, TeacherUnavailable  # noqa: E402
from schedule.services import auto_build  # noqa: E402

# Аудитории (48 по ТЗ: 32 кабинета, 10 лабораторий, 6 компьютерных классов)
rooms_created = 0
for i in range(1, 33):
    r, was = Room.objects.get_or_create(name=f'А-{i:02d}', defaults={
        'building': 'Учебный корпус', 'capacity': random.choice([24, 30, 32]),
        'room_type': 'lecture'})
    if was:
        rooms_created += 1
for i in range(1, 11):
    r, was = Room.objects.get_or_create(name=f'Л-{i:02d}', defaults={
        'building': 'Учебный корпус', 'capacity': 16, 'room_type': 'lab'})
    if was:
        rooms_created += 1
for i in range(1, 7):
    r, was = Room.objects.get_or_create(name=f'К-{i:02d}', defaults={
        'building': 'Учебный корпус', 'capacity': 15, 'room_type': 'computer'})
    if was:
        rooms_created += 1

# Преподаватели (8)
teacher_names = [
    ('Иванов', 'Иван', 'Иванович', 'Преподаватель'),
    ('Петрова', 'Мария', 'Сергеевна', 'Старший преподаватель'),
    ('Сидоров', 'Пётр', 'Петрович', 'Преподаватель'),
    ('Кузнецова', 'Анна', 'Андреевна', 'Преподаватель'),
    ('Смирнов', 'Алексей', 'Викторович', 'Преподаватель'),
    ('Волкова', 'Елена', 'Дмитриевна', 'Старший преподаватель'),
    ('Козлов', 'Дмитрий', 'Александрович', 'Преподаватель'),
    ('Морозова', 'Ольга', 'Игоревна', 'Преподаватель'),
]
teacher_objs = []
for ln, fn, mn, pos in teacher_names:
    t, was = Teacher.objects.get_or_create(
        last_name=ln, first_name=fn, middle_name=mn,
        defaults={'position': pos, 'department': 'Учебная часть'})
    teacher_objs.append(t)

# Учебный план: каждой группе по 3-4 дисциплины из существующих (с преподавателем)
plan_created = 0
subject_pool = Subject.objects.all()
for group in Group.objects.all():
    for idx, subj in enumerate(subject_pool[:4]):
        teacher = teacher_objs[idx % len(teacher_objs)]
        cur, was = Curriculum.objects.get_or_create(
            group=group, subject=subj, semester=1,
            defaults={'teacher': teacher, 'hours_per_week': 2,
                      'exam_type': random.choice(['exam', 'credit'])})
        if was:
            plan_created += 1

# Ограничения времени работы: каждый преподаватель недоступен 1 слот в неделю
unav_created = 0
for i, teacher in enumerate(teacher_objs):
    u, was = TeacherUnavailable.objects.get_or_create(
        teacher=teacher, day_of_week=(i % 6) + 1, lesson_number=(i % 5) + 1,
        semester=1, defaults={'comment': 'Методический день'})
    if was:
        unav_created += 1

# Автопостроение расписания на 1 семестр
entries_created = 0
for group in Group.objects.all():
    entries_created += len(auto_build(group=group, semester=1))

# Публикуем всё расписание
published = ScheduleEntry.objects.update(is_published=True)

print(f'Готово: отделений={Department.objects.count()}, '
      f'специальностей={Specialty.objects.count()}, '
      f'групп={Group.objects.count()}, '
      f'студентов={Student.objects.count()} (создано новых: {created}), '
      f'типов приказов={OrderType.objects.count()}, '
      f'дисциплин={Subject.objects.count()}, '
      f'занятий={Lesson.objects.count()} (создано: {lessons_created}), '
      f'оценок={Grade.objects.count()} (создано: {grades_created}), '
      f'записей посещаемости={Attendance.objects.count()} (создано: {att_created}), '
      f'экзаменов={Exam.objects.filter(exam_type="exam").count()} (создано: {exams_created}), '
      f'зачётов={Exam.objects.filter(exam_type="credit").count()} (создано: {credits_created}), '
      f'результатов={ExamResult.objects.count()} (создано: {results_created}), '
      f'задолженностей={AcademicDebt.objects.count()} (создано: {debts_created}), '
      f'стипендия: {period.name} — {period.students_count} студентов, '
      f'аудиторий={Room.objects.count()} (создано: {rooms_created}), '
      f'преподавателей={Teacher.objects.count()}, '
      f'пунктов плана={Curriculum.objects.count()} (создано: {plan_created}), '
      f'ограничений={TeacherUnavailable.objects.count()} (создано: {unav_created}), '
      f'занятий в расписании={ScheduleEntry.objects.count()} (создано: {entries_created}), '
      f'опубликовано={published}')
