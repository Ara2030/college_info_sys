# -*- coding: utf-8 -*-
"""
Модуль 2.1 «Контингент студентов»
=================================
Сервис формирования XML-выгрузки сведений о контингенте обучающихся
в Реестр СПО (формат обмена 1.0).

Формат разработан в рамках дипломного проекта по аналогии с требованиями
ведомственных реестров (ФРДО, ГИС «Контингент»): XML-файл содержит заголовок
отправителя (реквизиты колледжа), сведения о студентах и приказах.

Схема формата: schema/registry_spo.xsd

Основные функции:
    build_registry_xml(...)     — построение XML-дерева (ElementTree)
    xml_to_string(...)          — сериализация в читаемый XML (pretty-print)
    validate_xml(...)           — проверка файла по XSD-схеме (lxml, опционально)
    checksum(...)               — SHA-256 файла (контроль целостности)
    create_registry_export(...) — формирование выгрузки и сохранение в БД
"""

from __future__ import annotations

import hashlib
import pathlib
import xml.etree.ElementTree as ET
from datetime import date
from typing import Iterable, Optional
from xml.dom import minidom

from django.core.files.base import ContentFile
from django.utils import timezone

from ..models import Order, RegistryExport

# ---------------------------------------------------------------------------
# Реквизиты образовательной организации (заполнить данными колледжа)
# ---------------------------------------------------------------------------
COLLEGE = {
    "name": "ГБПОУ «Колледж»",
    "ogrn": "1020000000000",
    "inn": "7700000000",
    "kpp": "770001001",
}

# Версия формата обмена (пишется в заголовок XML)
FORMAT_VERSION = "1.0"

# Путь к XSD-схеме по умолчанию (относительно корня проекта)
DEFAULT_XSD_PATH = pathlib.Path(__file__).resolve().parents[2] / "schema" / "registry_spo.xsd"


# ---------------------------------------------------------------------------
# Вспомогательные функции построения XML
# ---------------------------------------------------------------------------
def _text(parent: ET.Element, tag: str, value) -> ET.Element:
    """Добавляет дочерний элемент <tag> с текстовым значением (безопасно)."""
    el = ET.SubElement(parent, tag)
    if value is not None:
        el.text = str(value)
    return el


def _fio(student) -> dict:
    """ФИО студента: Фамилия / Имя / Отчество."""
    return {
        "Фамилия": getattr(student, "last_name", "") or "",
        "Имя": getattr(student, "first_name", "") or "",
        "Отчество": getattr(student, "middle_name", "") or "",
    }


def _address(student) -> str:
    """Полный адрес: составляется из полей address_*."""
    parts = []
    for field in ("address_index", "address_city",
                  "address_street", "address_house", "address_flat"):
        value = getattr(student, field, "") or ""
        if value:
            parts.append(str(value))
    return ", ".join(parts)


def _identity_doc(student) -> dict:
    """Паспорт (или иной документ, удостоверяющий личность)."""
    doc = getattr(student, "identity_document", None)
    if doc is None:
        docs = getattr(student, "documents", None)
        if docs is not None:
            doc = docs.filter(doc_type="passport").first()
    if doc is None:
        return {"Тип": "", "Серия": "", "Номер": "", "ДатаВыдачи": "", "КемВыдан": ""}
    issue_date = getattr(doc, "issue_date", None)
    return {
        "Тип": getattr(doc, "doc_type", "") or "",
        "Серия": getattr(doc, "series", "") or "",
        "Номер": getattr(doc, "number", "") or "",
        "ДатаВыдачи": issue_date.isoformat() if issue_date else "",
        "КемВыдан": getattr(doc, "issued_by", "") or "",
    }


def _training(student) -> dict:
    """Сведения об обучении: группа, курс, форма, специальность, статус."""
    group = getattr(student, "group", None)
    spec = getattr(group, "specialty", None) if group else None
    status_display = ""
    if hasattr(student, "get_status_display"):
        status_display = student.get_status_display()
    elif getattr(student, "status", None):
        status_display = student.status
    return {
        "Группа": getattr(group, "name", "") or "",
        "Курс": getattr(group, "course", 0) if group else 0,
        "ФормаОбучения": "Очная",
        "СпециальностьКод": getattr(spec, "code", "") if spec else "",
        "СпециальностьНаименование": getattr(spec, "name", "") if spec else "",
        "Статус": status_display,
        "ДатаЗачисления": (getattr(student, "enroll_date", None).isoformat()
                           if getattr(student, "enroll_date", None) else ""),
    }


def _date_text(value) -> str:
    """Дата для XML: пустая строка, если даты нет."""
    return value.isoformat() if value else ""


def _text_or_skip(parent: ET.Element, tag: str, value) -> None:
    """Добавляет дочерний элемент, только если значение непустое (для xs:date)."""
    if value:
        _text(parent, tag, value)


# ---------------------------------------------------------------------------
# Построение XML-дерева
# ---------------------------------------------------------------------------
def build_registry_xml(students, orders: Optional[Iterable[Order]] = None, *,
                       period_start: Optional[date] = None,
                       period_end: Optional[date] = None,
                       org: Optional[dict] = None) -> ET.Element:
    """Формирует корневой элемент <РеестрСПО> с заголовком, студентами и приказами."""
    org = org or COLLEGE
    root = ET.Element("РеестрСПО", {
        "версия": FORMAT_VERSION,
        "датаФормирования": date.today().isoformat(),
    })

    # --- Заголовок ---
    header = ET.SubElement(root, "Заголовок")
    _text(header, "ТипСообщения", "ВыгрузкаСведенийОКонтингенте")
    _text(header, "ВерсияФормата", FORMAT_VERSION)
    sender = ET.SubElement(header, "Отправитель")
    _text(sender, "Наименование", org.get("name", ""))
    _text(sender, "ОГРН", org.get("ogrn", ""))
    _text(sender, "ИНН", org.get("inn", ""))
    _text(sender, "КПП", org.get("kpp", ""))
    period = ET.SubElement(header, "Период")
    _text(period, "ДатаНачала", _date_text(period_start))
    _text(period, "ДатаОкончания", _date_text(period_end))

    # --- Студенты ---
    students_el = ET.SubElement(root, "Студенты")
    for student in students:
        s = ET.SubElement(students_el, "Студент")
        _text(s, "Идентификатор", student.pk)
        _text(s, "НомерЛичногоДела", getattr(student, "student_card_number", "") or "")
        fio = ET.SubElement(s, "ФИО")
        for tag, value in _fio(student).items():
            _text(fio, tag, value)
        _text(s, "СНИЛС", getattr(student, "snils", "") or "")
        birth = getattr(student, "birth_date", None)
        _text(s, "ДатаРождения", _date_text(birth))
        _text(s, "Пол", getattr(student, "gender", "") or "")
        _text(s, "Гражданство", getattr(student, "citizenship", "") or "Россия")
        doc = ET.SubElement(s, "ДокументУдостоверяющийЛичность")
        for tag, value in _identity_doc(student).items():
            if tag == "ДатаВыдачи":
                _text_or_skip(doc, tag, value)
            else:
                _text(doc, tag, value)
        _text(s, "Адрес", _address(student))
        # Документ об образовании
        edu = ET.SubElement(s, "ДокументОбОбразовании")
        _text(edu, "Серия", getattr(student, "education_doc_series", "") or "")
        _text(edu, "Номер", getattr(student, "education_doc_number", "") or "")
        edu_date = getattr(student, "education_doc_date", None)
        _text_or_skip(edu, "ДатаВыдачи", _date_text(edu_date))
        _text(edu, "Организация", getattr(student, "education_doc_org", "") or "")
        # Социальная карта
        social = ET.SubElement(s, "СоциальнаяКарта")
        _text(social, "Номер", getattr(student, "social_card_number", "") or "")
        sc_date = getattr(student, "social_card_issued", None)
        _text_or_skip(social, "ДатаВыдачи", _date_text(sc_date))
        contacts = ET.SubElement(s, "Контакты")
        _text(contacts, "Телефон", getattr(student, "phone", "") or "")
        _text(contacts, "Email", getattr(student, "email", "") or "")
        training = ET.SubElement(s, "Обучение")
        for tag, value in _training(student).items():
            if tag == "ДатаЗачисления":
                _text_or_skip(training, tag, value)
            else:
                _text(training, tag, value)

    # --- Приказы (блок выводится только если есть приказы) ---
    if orders:
        orders_el = ET.SubElement(root, "Приказы")
        for order in orders:
            o = ET.SubElement(orders_el, "Приказ")
        _text(o, "Номер", getattr(order, "number", "") or "")
        order_date = getattr(order, "date", None)
        _text(o, "Дата", _date_text(order_date))
        order_type = getattr(order, "order_type", "") or ""
        if hasattr(order, "get_order_type_display"):
            order_type = order.get_order_type_display()
        _text(o, "Вид", order_type)
        _text(o, "Тема", getattr(order, "title", "") or "")
        status_display = ""
        if hasattr(order, "get_status_display"):
            status_display = order.get_status_display()
        _text(o, "Статус", status_display)
        items = ET.SubElement(o, "Пункты")
        for item in getattr(order, "items", None).all() if getattr(order, "items", None) else []:
            p = ET.SubElement(items, "Пункт")
            action = getattr(item, "action", "") or ""
            if hasattr(item, "get_action_display"):
                action = item.get_action_display()
            _text(p, "Действие", action)
            _text(p, "Студент", str(item.student) if getattr(item, "student", None) else "")
            _text_or_skip(p, "ДатаВступленияВСилу", _date_text(order_date))
    return root


def xml_to_string(root: ET.Element) -> str:
    """Сериализует дерево в читаемый XML с декларацией (UTF-8)."""
    rough = ET.tostring(root, encoding="unicode")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ")


# ---------------------------------------------------------------------------
# Валидация и контрольная сумма
# ---------------------------------------------------------------------------
def validate_xml(xml_str: str, xsd_path: Optional[str] = None) -> list:
    """
    Проверяет XML по XSD-схеме (lxml). Возвращает список ошибок;
    пустой список означает, что файл корректен.
    """
    errors = []
    try:
        from lxml import etree
    except ImportError:
        return ["lxml не установлен — проверка по XSD пропущена (pip install lxml)"]
    try:
        schema_doc = etree.parse(str(xsd_path or DEFAULT_XSD_PATH))
        schema = etree.XMLSchema(schema_doc)
        doc = etree.fromstring(xml_str.encode("utf-8"))
        if not schema.validate(doc):
            for err in schema.error_log:
                errors.append(f"строка {err.line}: {err.message}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"ошибка проверки XML: {exc}")
    return errors


def checksum(data: bytes) -> str:
    """SHA-256 файла — контроль целостности при передаче в реестр."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Формирование выгрузки и сохранение в БД
# ---------------------------------------------------------------------------
def create_registry_export(*, students, orders: Optional[Iterable[Order]] = None,
                           period_start: date, period_end: date,
                           group=None, student_status: str = "",
                           comment: str = "", org: Optional[dict] = None) -> RegistryExport:
    """
    Формирует XML-выгрузку, валидирует её и сохраняет запись в RegistryExport.
    Возвращает сохранённую выгрузку.
    """
    root = build_registry_xml(students, orders,
                              period_start=period_start,
                              period_end=period_end, org=org)
    xml_str = xml_to_string(root)
    xml_bytes = xml_str.encode("utf-8")
    errors = validate_xml(xml_str)

    export = RegistryExport(
        period_start=period_start,
        period_end=period_end,
        group=group,
        student_status=student_status,
        student_count=len(students),
        order_count=len(orders or []),
        checksum=checksum(xml_bytes),
        validation_errors="\n".join(errors),
        comment=comment,
        status=RegistryExport.Status.ERROR if errors else RegistryExport.Status.READY,
    )
    file_name = f"registry_spo_{timezone.now():%Y%m%d_%H%M%S}.xml"
    export.file_name = file_name
    export.xml_file.save(file_name, ContentFile(xml_bytes), save=False)
    export.save()
    return export
