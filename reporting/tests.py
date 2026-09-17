# -*- coding: utf-8 -*-
"""Тесты модуля «Отчётность и интеграция» (2.6)."""
import json

from django.test import TestCase

from contingent.models import Department, Group, Specialty, Student, StudentStatus
from .models import IntegrationLog, SmevRequest, StatReport
from .services import (build_stat_report, send_to_registry_api, smev_request,
                       stat_report_excel, stat_report_pdf)


class ReportingBaseTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        dep = Department.objects.create(name='ИТ', code='ИТ')
        spec = Specialty.objects.create(code='09.02.07', name='ИСП', department=dep)
        group = Group.objects.create(name='ИС-61', specialty=spec, department=dep,
                                     course=1, enroll_year=2025)
        Student.objects.create(
            last_name='Тестов', first_name='Иван', birth_date='2007-01-01',
            snils='777-888-999 11', group=group, specialty=spec,
            status=StudentStatus.STUDY, student_card_number='ИС-61-001',
            enroll_date='2025-09-01')


class StatReportTests(ReportingBaseTestCase):
    """Статистические отчёты (СПО-1, СПО-2, мониторинг)."""

    def test_spo1_report_created(self):
        report = build_stat_report(StatReport.Type.SPO1, 2026)
        self.assertEqual(report.period_year, 2026)
        self.assertEqual(report.status, StatReport.Status.READY)
        self.assertTrue(report.checksum)

    def test_spo1_contains_contingent_data(self):
        report = build_stat_report(StatReport.Type.SPO1, 2026)
        data = json.loads(report.data_json)
        section = data['Раздел 1. Сеть образовательной организации']
        self.assertEqual(section['Студентов'], 1)
        self.assertEqual(section['Групп'], 1)

    def test_spo1_contains_movement_section(self):
        report = build_stat_report(StatReport.Type.SPO1, 2026)
        data = json.loads(report.data_json)
        self.assertIn('Раздел 3. Движение контингента за год', data)

    def test_spo2_report_created(self):
        report = build_stat_report(StatReport.Type.SPO2, 2026)
        data = json.loads(report.data_json)
        self.assertIn('Аудиторный фонд', data)

    def test_monitoring_report_created(self):
        report = build_stat_report(StatReport.Type.MONITORING, 2026)
        data = json.loads(report.data_json)
        self.assertIn('Контингент', data)
        self.assertIn('Инфраструктура и кадры', data)

    def test_excel_export_is_valid_xlsx(self):
        report = build_stat_report(StatReport.Type.SPO1, 2026)
        buf, filename = stat_report_excel(report)
        self.assertTrue(buf.getvalue().startswith(b'PK'), 'xlsx начинается с PK')
        self.assertTrue(filename.endswith('.xlsx'))

    def test_pdf_export_is_valid_pdf(self):
        report = build_stat_report(StatReport.Type.SPO1, 2026)
        buf, filename = stat_report_pdf(report)
        self.assertTrue(buf.getvalue().startswith(b'%PDF-'))
        self.assertTrue(filename.endswith('.pdf'))

    def test_pdf_embeds_cyrillic_font(self):
        """Кириллица в PDF: должен быть встроен TrueType-шрифт (баг с квадратами)."""
        report = build_stat_report(StatReport.Type.SPO1, 2026)
        buf, _ = stat_report_pdf(report)
        data = buf.getvalue()
        self.assertIn(b'TrueType', data, 'должен быть встроен TTF-шрифт с кириллицей')


class RegistryApiTests(ReportingBaseTestCase):
    """REST API Реестра студентов СПО."""

    def test_send_to_registry_logs_request(self):
        log = send_to_registry_api(b'<?xml version="1.0"?><test/>')
        self.assertIsInstance(log, IntegrationLog)
        self.assertEqual(log.integration, IntegrationLog.Integration.REGISTRY_API)
        self.assertEqual(log.direction, 'out')
        self.assertIn(log.status, (IntegrationLog.Status.OK, IntegrationLog.Status.MOCK))

    def test_mock_mode_without_connection(self):
        log = send_to_registry_api(b'<test/>')
        self.assertEqual(log.status, IntegrationLog.Status.MOCK)
        self.assertEqual(log.status_code, 202)

    def test_payload_saved(self):
        log = send_to_registry_api(b'<xml>data</xml>')
        self.assertIn('xml', log.payload)


class SmevTests(ReportingBaseTestCase):
    """Интеграция с СМЭВ."""

    def test_smev_request_without_connection(self):
        req = smev_request('fns', '770000000000')
        self.assertEqual(req.status, SmevRequest.Status.NO_CONNECTION)
        self.assertIn('не настроено', req.response_text)

    def test_smev_request_saved(self):
        req = smev_request('pfr', '123-456-789 01', person_name='Иванов И.И.')
        self.assertEqual(req.registry, 'pfr')
        self.assertEqual(SmevRequest.objects.count(), 1)
