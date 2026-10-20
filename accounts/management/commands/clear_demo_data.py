# -*- coding: utf-8 -*-
"""Удаление демонстрационных данных перед вводом реальных.

Очищаются все учебные модули: контингент, журнал, аттестация, расписание,
кадры, отчётность. Пользователи, аудит и попытки входа сохраняются.

Использование:
    python manage.py clear_demo_data          # с подтверждением
    python manage.py clear_demo_data --yes    # без вопросов
"""
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.core.management.base import BaseCommand

# Приложения с демонстрационными (учебными) данными
DOMAIN_APPS = ('contingent', 'journal', 'attestation', 'schedule', 'hr', 'reporting')

# Файл-флаг: автозаполнение демо-данными при запуске больше не выполняется
DEMO_LOCK_FILE = '.demo_disabled'


def get_domain_models():
    """Модели всех учебных модулей (без прокси и автосозданных)."""
    models = []
    for label in DOMAIN_APPS:
        for model in django_apps.get_app_config(label).get_models():
            if model._meta.proxy or model._meta.auto_created:
                continue
            models.append(model)
    return models


def clear_domain_data():
    """Удаляет данные учебных модулей.

    Порядок удаления не задаётся вручную: делаем несколько проходов, пока
    модели с защищёнными связями (PROTECT) не освободятся. Возвращает словарь
    {модель: сколько записей удалено}.
    """
    models = get_domain_models()
    before = {m: m.objects.count() for m in models}

    pending = list(models)
    for _ in range(len(models) + 3):
        if not pending:
            break
        still_blocked = []
        for model in pending:
            try:
                model.objects.all().delete()
            except Exception:
                # Скорее всего защищённая связь — попробуем в следующем проходе
                still_blocked.append(model)
        if len(still_blocked) == len(pending):
            break
        pending = still_blocked

    after = {m: m.objects.count() for m in models}
    return {m: before[m] - after[m] for m in models if before[m] - after[m] > 0}


def disable_demo_autofill():
    """Создаёт файл-флаг, чтобы start.ps1 не заполнял демо-данные заново."""
    Path(settings.BASE_DIR, DEMO_LOCK_FILE).write_text(
        'Демо-данные очищены. Удалите этот файл, чтобы снова включить автозаполнение.\n',
        encoding='utf-8')
    return Path(settings.BASE_DIR, DEMO_LOCK_FILE)


def demo_autofill_disabled():
    return Path(settings.BASE_DIR, DEMO_LOCK_FILE).exists()


def demo_data_present():
    """Быстрая проверка, есть ли в базе учебные данные (демо или реальные).

    Считаем по нескольким ключевым моделям — EXISTS дешевле полного count.
    """
    from contingent.models import Department, Student
    from hr.models import Employee
    from journal.models import Lesson
    from schedule.models import ScheduleEntry

    for model in (Student, Department, Lesson, Employee, ScheduleEntry):
        if model.objects.exists():
            return True
    return False


class Command(BaseCommand):
    help = ('Удаляет демонстрационные данные всех учебных модулей '
            '(пользователи и журнал аудита сохраняются)')

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true',
                            help='не спрашивать подтверждение')
        parser.add_argument('--keep-autofill', action='store_true',
                            help='не отключать автозаполнение демо-данными при запуске')

    def handle(self, *args, **options):
        models = get_domain_models()
        total = sum(m.objects.count() for m in models)
        if total == 0:
            self.stdout.write(self.style.WARNING('Учебные данные уже отсутствуют.'))
        else:
            self.stdout.write(f'Будет удалено записей: {total} '
                              f'(моделей: {len(models)})')
            if not options['yes']:
                answer = input('Удалить демонстрационные данные? [y/N]: ').strip().lower()
                if answer not in ('y', 'yes', 'д', 'да'):
                    self.stdout.write('Отменено.')
                    return

        deleted = clear_domain_data()
        for model, count in sorted(deleted.items(), key=lambda kv: kv[1], reverse=True):
            self.stdout.write(f'  {model._meta.label:35} -{count}')

        if not options['keep_autofill']:
            path = disable_demo_autofill()
            self.stdout.write(f'Автозаполнение демо-данными отключено ({path.name}).')

        self.stdout.write(self.style.SUCCESS(
            f'Готово: удалено {sum(deleted.values())} записей. '
            f'Пользователи и аудит сохранены.'))
