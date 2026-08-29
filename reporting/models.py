# -*- coding: utf-8 -*-
"""
Модуль «Отчётность и интеграция» (2.6).

Модели:
  StatReport       — статистический отчёт (СПО-1, СПО-2, мониторинг Минпросвещения)
  IntegrationLog   — журнал интеграций (REST API Реестра СПО, СМЭВ)
  SmevRequest      — запрос сведений из государственных реестров через СМЭВ
"""
from django.db import models


class StatReport(models.Model):
    """Автоматически сформированный статистический отчёт."""
    class Type(models.TextChoices):
        SPO1 = 'spo1', 'СПО-1 (сведения о сети и численности)'
        SPO2 = 'spo2', 'СПО-2 (сведения о материально-технической базе)'
        MONITORING = 'monitoring', 'Мониторинг Минпросвещения'

    class Status(models.TextChoices):
        READY = 'ready', 'Сформирован'
        SENT = 'sent', 'Отправлен'
        ERROR = 'error', 'Ошибка'

    report_type = models.CharField('Тип отчёта', max_length=15, choices=Type.choices)
    period_year = models.PositiveSmallIntegerField('Отчётный год')
    period_date = models.DateField('Дата среза', null=True, blank=True)
    status = models.CharField('Статус', max_length=10, choices=Status.choices,
                              default=Status.READY)
    data_json = models.TextField('Данные отчёта (JSON)')
    file_name = models.CharField('Имя файла', max_length=255, blank=True)
    checksum = models.CharField('Контрольная сумма SHA-256', max_length=64, blank=True)
    created_at = models.DateTimeField('Сформирован', auto_now_add=True)
    comment = models.TextField('Комментарий', blank=True)

    class Meta:
        verbose_name = 'Статистический отчёт'
        verbose_name_plural = 'Статистические отчёты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_report_type_display()} — {self.period_year}'


class IntegrationLog(models.Model):
    """Журнал интеграций: REST API Реестра СПО, СМЭВ."""
    class Integration(models.TextChoices):
        REGISTRY_API = 'registry_api', 'REST API Реестра студентов СПО'
        SMEV = 'smev', 'СМЭВ (государственные реестры)'

    class Status(models.TextChoices):
        OK = 'ok', 'Успешно'
        MOCK = 'mock', 'Заглушка (без реального подключения)'
        NO_CONNECTION = 'no_connection', 'Нет подключения'
        ERROR = 'error', 'Ошибка'

    integration = models.CharField('Интеграция', max_length=20,
                                   choices=Integration.choices)
    direction = models.CharField('Направление', max_length=10,
                                 choices=[('out', 'Отправка'), ('in', 'Получение')])
    endpoint = models.CharField('Конечная точка', max_length=500, blank=True)
    payload = models.TextField('Запрос / данные', blank=True)
    response = models.TextField('Ответ', blank=True)
    status = models.CharField('Статус', max_length=15, choices=Status.choices,
                              default=Status.OK)
    status_code = models.PositiveSmallIntegerField('Код ответа', null=True, blank=True)
    created_at = models.DateTimeField('Время', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись интеграции'
        verbose_name_plural = 'Журнал интеграций'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_integration_display()} — {self.created_at:%d.%m.%Y %H:%M}'


class SmevRequest(models.Model):
    """Запрос в СМЭВ для получения сведений из государственных реестров."""
    class Registry(models.TextChoices):
        FNS = 'fns', 'ФНС (ИНН)'
        PFR = 'pfr', 'СФР (СНИЛС)'
        ZAGS = 'zags', 'ЗАГС (акты гражданского состояния)'
        MVD = 'mvd', 'МВД (паспорт)'

    class Status(models.TextChoices):
        CONNECTED = 'connected', 'Сведения получены'
        NO_CONNECTION = 'no_connection', 'Подключение не настроено'
        ERROR = 'error', 'Ошибка'

    registry = models.CharField('Реестр', max_length=10, choices=Registry.choices)
    identifier = models.CharField('Идентификатор (СНИЛС/ИНН/паспорт)', max_length=50)
    person_name = models.CharField('ФИО', max_length=200, blank=True)
    status = models.CharField('Статус', max_length=15, choices=Status.choices,
                              default=Status.NO_CONNECTION)
    response_text = models.TextField('Сведения из реестра', blank=True)
    request_date = models.DateTimeField('Дата запроса', auto_now_add=True)

    class Meta:
        verbose_name = 'Запрос СМЭВ'
        verbose_name_plural = 'Запросы СМЭВ'
        ordering = ['-request_date']

    def __str__(self):
        return f'{self.get_registry_display()} — {self.identifier}'
