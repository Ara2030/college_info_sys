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

# ==========================================================================
# Модуль 2.5 «Кадровый учёт»: сотрудники, штатное, тарификация, 1С, приказы
# ==========================================================================
from hr.models import (Employee, HROrder, SalaryExport, StaffPosition,  # noqa: E402
                       StaffingUnit, TarificationItem, TarificationPeriod)
from hr.services import (apply_hr_order, build_salary_export,  # noqa: E402
                         build_tarification_from_curriculum)

# Сотрудники: создаём по преподавателям (связь с расписанием) + АУП + персонал
employees_created = 0
for t in Teacher.objects.all():
    emp, was = Employee.objects.get_or_create(
        last_name=t.last_name, first_name=t.first_name, middle_name=t.middle_name,
        defaults={
            'category': 'teacher', 'position': t.position or 'Преподаватель',
            'department': 'Учебная часть', 'status': 'active',
            'hire_date': date(2018, 9, 1),
            'snils': f'{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(100,999)} {random.randint(10,99)}',
            'inn': f'{random.randint(1000000000, 9999999999)}',
            'education': 'Высшее', 'phone': f'+7 (9{random.randint(10,99)}) {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}',
            'email': f'{t.last_name.lower()}@college.ru',
            'teacher': t,
        })
    if was:
        employees_created += 1

# АУП и вспомогательный персонал
management = [
    ('Соколов', 'Андрей', 'Павлович', 'Директор', 'Администрация'),
    ('Орлова', 'Наталья', 'Викторовна', 'Заместитель директора по УР', 'Администрация'),
    ('Белов', 'Максим', 'Игоревич', 'Заведующий отделением', 'Отделение ИТ'),
    ('Громова', 'Татьяна', 'Александровна', 'Бухгалтер', 'Бухгалтерия'),
    ('Крылов', 'Сергей', 'Олегович', 'Специалист по кадрам', 'Отдел кадров'),
    ('Дроздов', 'Николай', 'Сергеевич', 'Системный администратор', 'IT-отдел'),
]
for ln, fn, mn, pos, dep in management:
    emp, was = Employee.objects.get_or_create(
        last_name=ln, first_name=fn, middle_name=mn,
        defaults={'category': 'management' if dep in ('Администрация', 'Отделение ИТ') else 'support',
                  'position': pos, 'department': dep, 'status': 'active',
                  'hire_date': date(2015, 9, 1), 'education': 'Высшее'})
    if was:
        employees_created += 1

# Штатное расписание: должности + единицы
staff_created = 0
staff_positions = [
    ('Директор', 'Администрация', 1, 90000),
    ('Заместитель директора по УР', 'Администрация', 1, 70000),
    ('Заведующий отделением', 'Отделения', 4, 55000),
    ('Преподаватель', 'Учебная часть', 20, 42000),
    ('Методист', 'Учебная часть', 2, 40000),
    ('Бухгалтер', 'Бухгалтерия', 3, 45000),
    ('Специалист по кадрам', 'Отдел кадров', 2, 42000),
    ('Системный администратор', 'IT-отдел', 2, 48000),
    ('Лаборант', 'Лаборатории', 4, 32000),
    ('Уборщик служебных помещений', 'Хозяйственный отдел', 5, 25000),
]
for title, dep, rate, salary in staff_positions:
    pos, was = StaffPosition.objects.get_or_create(
        title=title, defaults={'department': dep, 'rate_count': rate, 'salary': salary})
    if was:
        staff_created += 1
    # Назначаем сотрудников на ставки
    if title == 'Преподаватель':
        for emp in Employee.objects.filter(category='teacher', status='active')[:6]:
            StaffingUnit.objects.get_or_create(position=pos, employee=emp,
                                               defaults={'rate': 1, 'date_from': date(2018, 9, 1)})
    elif title == 'Директор':
        emp = Employee.objects.filter(position='Директор').first()
        if emp:
            StaffingUnit.objects.get_or_create(position=pos, employee=emp,
                                               defaults={'rate': 1, 'date_from': date(2015, 9, 1)})
    elif title == 'Бухгалтер':
        emp = Employee.objects.filter(position='Бухгалтер').first()
        if emp:
            StaffingUnit.objects.get_or_create(position=pos, employee=emp,
                                               defaults={'rate': 1, 'date_from': date(2015, 9, 1)})

# Тарификация: период + импорт из учебного плана
tar_period, tp_was = TarificationPeriod.objects.get_or_create(
    name='Тарификация 2025/2026', year_start=2025,
    defaults={'status': 'draft'})
tar_created = build_tarification_from_curriculum(tar_period) if tp_was else 0

# Выгрузка в 1С:Зарплата
export_created = 0
if not SalaryExport.objects.filter(tarification=tar_period).exists():
    export = build_salary_export(tar_period)
    export_created = 1

# Приказы по личному составу
order_created = 0
if not HROrder.objects.exists():
    emp = Employee.objects.filter(position='Преподаватель', status='active').first()
    if emp:
        order = HROrder.objects.create(
            number=f'ПР-{random.randint(100,999)}', date=date(2025, 9, 1),
            order_type='hire', employee=emp, position='Преподаватель',
            basis='Трудовой договор от 01.09.2025 № 12',
            text='Принять на работу по основному месту работы с учебной нагрузкой.')
        apply_hr_order(order)
        order_created += 1

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
      f'опубликовано={published}, '
      f'сотрудников={Employee.objects.count()} (создано: {employees_created}), '
      f'должностей={StaffPosition.objects.count()} (создано: {staff_created}), '
      f'единиц={StaffingUnit.objects.count()}, '
      f'тарификация: {tar_period.name} — {tar_period.items.count()} строк (создано: {tar_created}), '
      f'выгрузок 1С={SalaryExport.objects.count()} (создано: {export_created}), '
      f'приказов={HROrder.objects.count()} (создано: {order_created})')
