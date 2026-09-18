# -*- coding: utf-8 -*-
"""
Сервисы модуля «Формирование расписания» (2.4).

  check_entry_conflicts(entry, exclude=None) — проверка конфликтов занятия
  check_all_conflicts()                      — проверка всего расписания
  auto_build(group, semester, days, slots)   — автопостроение из учебного плана
"""
from .models import (Room, ScheduleEntry, Teacher, TeacherUnavailable,
                     DAY_CHOICES, SLOT_TIMES)


def check_entry_conflicts(entry, exclude=None):
    """
    Автоматическая проверка конфликтов для занятия.

    Возвращает список ошибок:
      - группа уже занята в этом слоте;
      - аудитория занята в этом слоте (одновременное занятие в двух группах);
      - преподаватель занят в этом слоте (в двух группах);
      - преподаватель недоступен в этот слот (TeacherUnavailable).
    """
    errors = []
    same_slot = ScheduleEntry.objects.filter(
        day_of_week=entry.day_of_week,
        lesson_number=entry.lesson_number,
        week_type=entry.week_type,
        semester=entry.semester,
    )
    if exclude is not None:
        same_slot = same_slot.exclude(pk=exclude.pk)

    if same_slot.filter(group=entry.group).exists():
        errors.append('У группы уже есть занятие в это время (конфликт группы).')

    if same_slot.filter(room=entry.room).exists():
        errors.append('Аудитория уже занята в это время — одновременное занятие '
                      'аудитории в двух группах.')

    if same_slot.filter(teacher=entry.teacher).exists():
        errors.append('Преподаватель уже занят в это время — одновременное занятие '
                      'преподавателя в двух группах.')

    if TeacherUnavailable.objects.filter(
        teacher=entry.teacher,
        day_of_week=entry.day_of_week,
        lesson_number=entry.lesson_number,
        semester=entry.semester,
    ).exists():
        errors.append('Преподаватель недоступен в это время (ограничение работы).')

    return errors


def check_all_conflicts():
    """
    Проверка всех занятий расписания на конфликты.
    Возвращает список (entry, errors) для занятий с ошибками.
    """
    result = []
    for entry in ScheduleEntry.objects.select_related(
            'group', 'subject', 'teacher', 'room'):
        errors = check_entry_conflicts(entry, exclude=entry)
        if errors:
            result.append((entry, errors))
    return result


def entry_is_valid(entry, exclude=None):
    """True, если занятие не создаёт конфликтов."""
    return not check_entry_conflicts(entry, exclude=exclude)


def _find_free_slot(group, teacher, semester, week_type='every'):
    """Ищет (day, lesson_number) свободный для группы и преподавателя."""
    for day, _ in DAY_CHOICES:
        for slot in range(1, len(SLOT_TIMES) + 1):
            if ScheduleEntry.objects.filter(
                group=group, day_of_week=day, lesson_number=slot,
                week_type=week_type, semester=semester,
            ).exists():
                continue
            if ScheduleEntry.objects.filter(
                teacher=teacher, day_of_week=day, lesson_number=slot,
                week_type=week_type, semester=semester,
            ).exists():
                continue
            if TeacherUnavailable.objects.filter(
                teacher=teacher, day_of_week=day, lesson_number=slot,
                semester=semester,
            ).exists():
                continue
            return day, slot
    return None


def _find_free_room(day, slot, semester, week_type='every'):
    for room in Room.objects.filter(is_available=True):
        if not ScheduleEntry.objects.filter(
            room=room, day_of_week=day, lesson_number=slot,
            week_type=week_type, semester=semester,
        ).exists():
            return room
    return None


def auto_build(*, group, semester=1, week_type='every', comment=''):
    """
    Автоматическое составление расписания группы на семестр
    по учебному плану (Curriculum): для каждой дисциплины распределяются
    часы в неделю по свободным слотам без конфликтов.
    Возвращает список созданных ScheduleEntry.
    """
    from .models import Curriculum
    created = []
    for item in Curriculum.objects.filter(group=group, semester=semester):
        for _ in range(item.hours_per_week):
            free = _find_free_slot(group, item.teacher, semester, week_type)
            if free is None:
                continue
            day, slot = free
            room = _find_free_room(day, slot, semester, week_type)
            if room is None:
                continue
            entry = ScheduleEntry.objects.create(
                group=group, subject=item.subject, teacher=item.teacher,
                room=room, day_of_week=day, lesson_number=slot,
                week_type=week_type, semester=semester,
                comment=comment or f'По учебному плану: {item.hours_per_week} ч/нед',
            )
            created.append(entry)
    return created
