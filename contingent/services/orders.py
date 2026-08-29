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
