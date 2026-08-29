-- ============================================================================
-- ИНФОРМАЦИОННАЯ СИСТЕМА КОЛЛЕДЖА (СПО)
-- Модуль 2.1 «Контингент студентов»
-- Схема базы данных: PostgreSQL 15+
-- Дипломный проект
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. СПРАВОЧНИКИ
-- ----------------------------------------------------------------------------

-- Отделения колледжа
CREATE TABLE departments (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    short_name  VARCHAR(20)  NOT NULL DEFAULT '',
    head_name   VARCHAR(150) NOT NULL DEFAULT ''
);
COMMENT ON TABLE departments IS 'Отделения колледжа';

-- Специальности СПО (код, квалификация, ФГОС)
CREATE TABLE specialties (
    id              BIGSERIAL PRIMARY KEY,
    code            VARCHAR(10)  NOT NULL UNIQUE,
    name            VARCHAR(250) NOT NULL,
    qualification   VARCHAR(150) NOT NULL DEFAULT '',
    fgos            VARCHAR(50)  NOT NULL DEFAULT '',
    duration_years  SMALLINT     NOT NULL DEFAULT 3 CHECK (duration_years BETWEEN 2 AND 4)
);
COMMENT ON TABLE specialties IS 'Специальности СПО';

-- Типы приказов (зачисление, отчисление, перевод, академ. отпуск и т.д.)
CREATE TABLE order_types (
    id    BIGSERIAL PRIMARY KEY,
    code  VARCHAR(30)  NOT NULL UNIQUE,
    name  VARCHAR(150) NOT NULL
);
COMMENT ON TABLE order_types IS 'Типы приказов по контингенту';

-- ----------------------------------------------------------------------------
-- 2. УЧЕБНЫЕ ГРУППЫ
-- ----------------------------------------------------------------------------
CREATE TABLE groups (
    id            BIGSERIAL PRIMARY KEY,
    name          VARCHAR(30)  NOT NULL UNIQUE,             -- ИС-22
    course        SMALLINT     NOT NULL DEFAULT 1 CHECK (course BETWEEN 1 AND 4),
    year          SMALLINT     NOT NULL,                    -- год набора
    form          VARCHAR(30)  NOT NULL DEFAULT 'очная'
                  CHECK (form IN ('очная','очно-заочная','заочная')),
    department_id BIGINT       NOT NULL REFERENCES departments(id),
    specialty_id  BIGINT       NOT NULL REFERENCES specialties(id),
    curator       VARCHAR(150) NOT NULL DEFAULT '',         -- ФИО куратора
    status        VARCHAR(20)  NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active','graduated','archived')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
COMMENT ON TABLE groups IS 'Учебные группы';
CREATE INDEX idx_groups_department ON groups(department_id);
CREATE INDEX idx_groups_specialty  ON groups(specialty_id);

-- ----------------------------------------------------------------------------
-- 3. СТУДЕНТЫ И ЛИЧНЫЕ ДАННЫЕ
-- ----------------------------------------------------------------------------
CREATE TABLE students (
    id                   BIGSERIAL PRIMARY KEY,
    last_name            VARCHAR(80)  NOT NULL,
    first_name           VARCHAR(80)  NOT NULL,
    middle_name          VARCHAR(80)  NOT NULL DEFAULT '',
    birth_date           DATE         NOT NULL,
    gender               CHAR(1)      NOT NULL CHECK (gender IN ('М','Ж')),
    snils                VARCHAR(14)  UNIQUE,               -- 000-000-000 00
    inn                  VARCHAR(12)  NOT NULL DEFAULT '',
    citizenship          VARCHAR(80)  NOT NULL DEFAULT 'Российская Федерация',
    birth_place          VARCHAR(150) NOT NULL DEFAULT '',
    registration_address TEXT         NOT NULL DEFAULT '',
    actual_address       TEXT         NOT NULL DEFAULT '',
    phone                VARCHAR(30)  NOT NULL DEFAULT '',
    email                VARCHAR(120) NOT NULL DEFAULT '',
    group_id             BIGINT       NOT NULL REFERENCES groups(id),
    specialty_id         BIGINT       NOT NULL REFERENCES specialties(id),
    form                 VARCHAR(30)  NOT NULL DEFAULT 'очная'
                         CHECK (form IN ('очная','очно-заочная','заочная')),
    status               VARCHAR(20)  NOT NULL DEFAULT 'studying'
                         CHECK (status IN ('studying','academic_leave','transferred',
                                           'expelled','graduated','restored')),
    enrolled_date        DATE         NOT NULL,
    book_number          VARCHAR(20)  NOT NULL DEFAULT '',   -- номер зачётной книжки
    notes                TEXT         NOT NULL DEFAULT '',
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);
COMMENT ON TABLE students IS 'Обучающиеся колледжа (личное дело)';
CREATE INDEX idx_students_group     ON students(group_id);
CREATE INDEX idx_students_specialty ON students(specialty_id);
CREATE INDEX idx_students_status    ON students(status);
CREATE INDEX idx_students_name      ON students(last_name, first_name, middle_name);

-- Документы студента (паспорт, свидетельство о рождении, СНИЛС и др.)
CREATE TABLE student_documents (
    id          BIGSERIAL PRIMARY KEY,
    student_id  BIGINT       NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    doc_type    VARCHAR(30)  NOT NULL
                CHECK (doc_type IN ('passport','birth_certificate','snils','inn',
                                    'med_policy','education_doc','military_id')),
    series      VARCHAR(20)  NOT NULL DEFAULT '',
    number      VARCHAR(30)  NOT NULL DEFAULT '',
    issue_date  DATE,
    issued_by   VARCHAR(250) NOT NULL DEFAULT '',
    valid_until DATE
);
COMMENT ON TABLE student_documents IS 'Документы обучающегося';
CREATE INDEX idx_documents_student ON student_documents(student_id);

-- Родители / опекуны
CREATE TABLE guardians (
    id          BIGSERIAL PRIMARY KEY,
    student_id  BIGINT       NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    full_name   VARCHAR(150) NOT NULL,
    relation    VARCHAR(30)  NOT NULL DEFAULT ''
                CHECK (relation IN ('мать','отец','опекун','иное')),
    phone       VARCHAR(30)  NOT NULL DEFAULT '',
    email       VARCHAR(120) NOT NULL DEFAULT ''
);
COMMENT ON TABLE guardians IS 'Родители и опекуны обучающихся';
CREATE INDEX idx_guardians_student ON guardians(student_id);

-- ----------------------------------------------------------------------------
-- 4. ПРИКАЗЫ И ДВИЖЕНИЕ КОНТИНГЕНТА
-- ----------------------------------------------------------------------------
CREATE TABLE orders (
    id           BIGSERIAL PRIMARY KEY,
    number       VARCHAR(30)  NOT NULL,
    date         DATE         NOT NULL DEFAULT CURRENT_DATE,
    type_id      BIGINT       NOT NULL REFERENCES order_types(id),
    title        VARCHAR(300) NOT NULL,
    basis        VARCHAR(300) NOT NULL DEFAULT '',      -- основание приказа
    status       VARCHAR(20)  NOT NULL DEFAULT 'draft'
                 CHECK (status IN ('draft','approved','published')),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
COMMENT ON TABLE orders IS 'Приказы по контингенту';
CREATE INDEX idx_orders_number_date ON orders(number, date);
CREATE INDEX idx_orders_type        ON orders(type_id);

-- Пункты приказа (один приказ — много студентов)
CREATE TABLE order_items (
    id             BIGSERIAL PRIMARY KEY,
    order_id       BIGINT       NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    student_id     BIGINT       NOT NULL REFERENCES students(id),
    action         VARCHAR(30)  NOT NULL
                   CHECK (action IN ('enroll','expel','transfer','academic_leave',
                                     'restore','graduate')),
    group_id       BIGINT       REFERENCES groups(id),      -- новая группа (при переводе/зачислении)
    course         SMALLINT     CHECK (course BETWEEN 1 AND 4),
    reason         VARCHAR(250) NOT NULL DEFAULT '',
    effective_date DATE         NOT NULL DEFAULT CURRENT_DATE,
    comment        VARCHAR(250) NOT NULL DEFAULT ''
);
COMMENT ON TABLE order_items IS 'Пункты приказа (действия по студентам)';
CREATE INDEX idx_items_order   ON order_items(order_id);
CREATE INDEX idx_items_student ON order_items(student_id);

-- История статусов студента (журнал движения контингента)
CREATE TABLE student_status_history (
    id             BIGSERIAL PRIMARY KEY,
    student_id     BIGINT       NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    status         VARCHAR(20)  NOT NULL,
    order_id       BIGINT       REFERENCES orders(id),
    effective_date DATE         NOT NULL,
    comment        VARCHAR(250) NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
COMMENT ON TABLE student_status_history IS 'История изменения статусов обучающихся';
CREATE INDEX idx_history_student  ON student_status_history(student_id);
CREATE INDEX idx_history_status   ON student_status_history(status);

-- Академические отпуска
CREATE TABLE academic_leaves (
    id          BIGSERIAL PRIMARY KEY,
    student_id  BIGINT       NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    order_id    BIGINT       REFERENCES orders(id),
    start_date  DATE         NOT NULL,
    end_date    DATE,
    reason      VARCHAR(250) NOT NULL DEFAULT '',
    status      VARCHAR(20)  NOT NULL DEFAULT 'active'
                CHECK (status IN ('active','closed'))
);
COMMENT ON TABLE academic_leaves IS 'Академические отпуска обучающихся';
CREATE INDEX idx_leaves_student ON academic_leaves(student_id);

-- ----------------------------------------------------------------------------
-- 5. ВЫГРУЗКА В РЕЕСТР СПО (XML)
-- ----------------------------------------------------------------------------
CREATE TABLE registry_exports (
    id            BIGSERIAL PRIMARY KEY,
    period        VARCHAR(7)   NOT NULL,               -- ГГГГ-ММ
    export_date   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    filename      VARCHAR(200) NOT NULL DEFAULT '',
    records_count INTEGER      NOT NULL DEFAULT 0,
    status        VARCHAR(20)  NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','success','error')),
    error_log     TEXT         NOT NULL DEFAULT '',
    created_by    VARCHAR(100) NOT NULL DEFAULT ''
);
COMMENT ON TABLE registry_exports IS 'Журнал выгрузок в Реестр СПО';
CREATE INDEX idx_exports_period ON registry_exports(period);

-- ----------------------------------------------------------------------------
-- 6. ПРЕДСТАВЛЕНИЯ
-- ----------------------------------------------------------------------------

-- Полная карточка студента
CREATE OR REPLACE VIEW v_students_full AS
SELECT s.id,
       CONCAT_WS(' ', s.last_name, s.first_name, NULLIF(s.middle_name, '')) AS full_name,
       s.birth_date,
       s.gender,
       s.snils,
       s.status,
       g.name  AS group_name,
       g.course,
       sp.code AS specialty_code,
       sp.name AS specialty_name,
       d.name  AS department_name
FROM students s
JOIN groups g      ON g.id = s.group_id
JOIN specialties sp ON sp.id = s.specialty_id
JOIN departments d  ON d.id = g.department_id;

-- Сводка контингента по отделениям / специальностям / курсам
CREATE OR REPLACE VIEW v_contingent_summary AS
SELECT d.name AS department,
       CONCAT_WS(' ', sp.code, sp.name) AS specialty,
       g.course,
       COUNT(*) FILTER (WHERE s.status = 'studying')      AS studying,
       COUNT(*) FILTER (WHERE s.status = 'academic_leave') AS on_leave,
       COUNT(*) FILTER (WHERE s.status = 'expelled')       AS expelled,
       COUNT(*) AS total
FROM students s
JOIN groups g       ON g.id = s.group_id
JOIN specialties sp ON sp.id = s.specialty_id
JOIN departments d  ON d.id = g.department_id
GROUP BY d.name, sp.code, sp.name, g.course;

-- ----------------------------------------------------------------------------
-- 7. НАЧАЛЬНОЕ НАПОЛНЕНИЕ СПРАВОЧНИКОВ (seed)
-- ----------------------------------------------------------------------------

INSERT INTO departments (name, short_name) VALUES
 ('Информационных технологий и связи',  'ИТ'),
 ('Электроэнергетики',                  'ЭЭ'),
 ('Экономики и управления',             'ЭУ'),
 ('Общеобразовательных дисциплин',      'ООД');

INSERT INTO specialties (code, name, qualification, fgos, duration_years) VALUES
 ('09.02.05', 'Прикладная информатика', 'Специалист по информационным ресурсам', 'ФГОС СПО 09.02.05', 3),
 ('09.02.07', 'Информационные системы и программирование', 'Программист', 'ФГОС СПО 09.02.07', 3),
 ('13.02.03', 'Электрические станции, сети и системы', 'Техник-электрик', 'ФГОС СПО 13.02.03', 3),
 ('13.02.11', 'Техническая эксплуатация и обслуживание электрического и электромеханического оборудования', 'Техник', 'ФГОС СПО 13.02.11', 3),
 ('09.02.01', 'Компьютерные системы и комплексы', 'Техник по компьютерным системам', 'ФГОС СПО 09.02.01', 3),
 ('38.02.01', 'Экономика и бухгалтерский учёт', 'Бухгалтер', 'ФГОС СПО 38.02.01', 2),
 ('38.02.04', 'Коммерция (по отраслям)', 'Менеджер по продажам', 'ФГОС СПО 38.02.04', 2),
 ('40.02.01', 'Право и организация социального обеспечения', 'Юрист', 'ФГОС СПО 40.02.01', 2);

INSERT INTO order_types (code, name) VALUES
 ('enrollment',      'О зачислении'),
 ('expulsion',       'Об отчислении'),
 ('transfer',        'О переводе'),
 ('academic_leave',  'О предоставлении академического отпуска'),
 ('restoration',     'О восстановлении'),
 ('graduation',      'О выпуске'),
 ('scholarship',     'О назначении стипендии');

COMMIT;
