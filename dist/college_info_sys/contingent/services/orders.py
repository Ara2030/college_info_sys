# -*- coding: utf-8 -*-
"""Сервис проведения приказов по контингенту.

Проводит приказ: обновляет статусы студентов согласно пунктам,
записывает журнал движения (StudentStatusHistory).
"""
from ..models import Order, StudentStatusHistory, StudentStatus

# Код действия в пункте приказа -> целевой статус студента
ACTION_TO_STATUS = {
    'enroll': StudentStatus.STUDY,           # зачисление
    'expel': StudentStatus.EXPELLED,         # отчисление
    'transfer': StudentStatus.STUDY,         # перевод (в т.ч. в другую группу)
    'academic_leave': StudentStatus.ACADEMIC_LEAVE,  # академ. отпуск
    'recover': StudentStatus.STUDY,          # восстановление
}


def render_order_text(order: Order) -> str:
    """
    Формирует текст приказа по шаблону типа приказа (OrderType.template_text)
    с подстановкой плейсхолдеров:
      {number}  — номер приказа, {date} — дата,
      {student} — список студентов (пункты), {basis} — основание.
    Если шаблон не задан — возвращает пустую строку.
    """
    template = (order.order_type.template_text
                if order.order_type and order.order_type.template_text else '')
    if not template:
        return ''

    items = order.items.select_related('student', 'group_to')
    students_lines = []
    for i, item in enumerate(items, 1):
        action = item.get_action_display()
        target = f' в группу {item.group_to.name}' if item.group_to else ''
        basis = f' ({item.basis})' if item.basis else ''
        students_lines.append(f'{i}. {item.student.full_name} — {action.lower()}{target}{basis}.')
    students_text = '\n'.join(students_lines) if students_lines else '—'

    replacements = {
        '{number}': order.number,
        '{date}': order.date.strftime('%d.%m.%Y'),
        '{student}': students_text,
        '{basis}': order.items.first().basis if order.items.exists() else '',
    }
    text = template
    for key, value in replacements.items():
        text = text.replace(key, str(value))
    return text


def post_order(order: Order) -> str:
    """Проводит приказ, возвращает строку-отчёт.

    Raises:
        ValueError: приказ уже проведён, пуст или содержит неизвестное действие.
    """
    if order.status == Order.Status.POSTED:
        raise ValueError('Приказ уже проведён.')

    items = order.items.select_related('student', 'group_to')
    if not items:
        raise ValueError('В приказе нет пунктов.')

    updated = 0
    for item in items:
        new_status = ACTION_TO_STATUS.get(item.action)
        if new_status is None:
            raise ValueError(f'Неизвестное действие «{item.action}» в пункте приказа.')

        # 1. Журнал движения контингента
        StudentStatusHistory.objects.create(
            student=item.student,
            order=order,
            status_from=item.student.status,
            status_to=new_status,
            date=order.date,
            comment=f'Приказ №{order.number} от {order.date:%d.%m.%Y}',
        )

        # 2. Обновляем карточку студента
        student = item.student
        student.status = new_status
        if item.action in ('enroll', 'recover', 'transfer') and item.group_to:
            student.group = item.group_to
        if item.action in ('enroll', 'recover') and not student.enroll_date:
            student.enroll_date = order.date
        update_fields = ['status', 'group', 'enroll_date']
        student.save(update_fields=update_fields)
        updated += 1

    # 3. Приказ — проведён
    order.status = Order.Status.POSTED
    order.save(update_fields=['status'])
    return f'Обработано пунктов: {updated}.'
