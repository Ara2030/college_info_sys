ИНСТРУКЦИЯ ПО РАЗВЁРТЫВАНИЮ ИС КОЛЛЕДЖА
=======================================

Что в архиве:
  college_info_sys/     - исходный код системы (Django-проект)
  database_dump.sql     - дамп базы данных (все данные: студенты, оценки, расписание и т.д.)
  README_УСТАНОВКА.txt  - этот файл

ТРЕБОВАНИЯ
----------
1. Python 3.12 или новее        (проверить: python --version)
2. PostgreSQL 15 или новее      (скачать: https://www.postgresql.org/download/windows/)
3. Git (необязательно)

УСТАНОВКА - ПОШАГОВО
--------------------
Шаг 1. Установите Python и PostgreSQL (при установке PostgreSQL запомните пароль
       пользователя postgres! Он понадобится).

Шаг 2. Распакуйте архив, например в C:\college_info_sys

Шаг 3. Создайте базу данных. Откройте командную строку (cmd) и выполните:

       "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE DATABASE college_sys ENCODING 'UTF8' TEMPLATE template0;"

       (введите пароль postgres, когда попросит)

Шаг 4. Восстановите данные из дампа:

       "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d college_sys -f database_dump.sql

Шаг 5. Создайте файл .env в папке проекта (скопируйте .env.example и переименуйте).
       Откройте его в блокноте и укажите:

       DJANGO_DEBUG=True
       DJANGO_SECRET_KEY=<любая длинная случайная строка>
       DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
       DB_NAME=college_sys
       DB_USER=postgres
       DB_PASSWORD=<ваш пароль postgres>
       DB_HOST=127.0.0.1
       DB_PORT=5432

Шаг 6. Запустите систему - двойной щелчок по start.bat
       (скрипт сам создаст окружение, поставит зависимости и запустит сервер)

Шаг 7. Откройте браузер:  http://127.0.0.1:8000/

ВХОД В СИСТЕМУ
--------------
  admin / admin123          - администратор
  director / director123    - директор
  methodist / methodist123  - методист
  teacher1 / teacher123     - преподаватель
  student1 / student123     - студент
  parent1 / parent123       - родитель

ВАЖНО: смените пароли в реальной эксплуатации!

ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ
-----------------------
- Ошибка подключения к БД → проверьте, что служба PostgreSQL запущена
  (Пуск → Службы → postgresql-x64-17 → Запустить) и пароль в .env верный.
- Нет прав на миграции → запустите от имени администратора.
- Подробная документация: файл README.md в папке проекта.
- Раздел "Возможные проблемы" в README.md содержит решения типовых ошибок.

АЛЬТЕРНАТИВА: если PostgreSQL установить нельзя
----------------------------------------------
Можно использовать SQLite (без установки СУБД). В файле config/settings.py
замените блок DATABASES на:

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

Затем выполните: python manage.py migrate (данные будут пустыми - заполнить
демо-данными можно скриптом: python fill_demo_data.py).
