-- Создание роли приложения с минимальными правами (защита БД)
-- Роль НЕ является суперпользователем: только CRUD-операции, без DDL.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'college_app') THEN
    CREATE ROLE college_app LOGIN PASSWORD 'Coll3ge_App#2026!x7K9';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE college_sys TO college_app;
GRANT USAGE ON SCHEMA public TO college_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO college_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO college_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO college_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO college_app;
-- Запрещаем создание объектов в схеме public (защита от изменения схемы)
REVOKE CREATE ON SCHEMA public FROM college_app;
-- Отключаем права PUBLIC по умолчанию
REVOKE ALL ON SCHEMA public FROM PUBLIC;
