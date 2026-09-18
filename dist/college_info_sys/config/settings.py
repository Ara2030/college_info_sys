# -*- coding: utf-8 -*-
"""
Настройки ИС колледжа (СПО). Дипломный проект.

Безопасность: секреты вынесены в .env, включены защитные заголовки,
безопасные cookies, HSTS, политика CSP, логирование, подключение к БД
под отдельной ролью приложения с минимальными правами.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Загрузка параметров окружения из .env (без внешних зависимостей)
# ---------------------------------------------------------------------------
def _load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip())


_load_env(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


# ---------------------------------------------------------------------------
# Основные параметры
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = env_bool('DJANGO_DEBUG', False)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')

# Защита от подделки заголовка Host (при работе за прокси)
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'contingent',          # <-- модуль 2.1 «Контингент студентов»
    'journal',             # <-- модуль 2.2 «Электронный журнал»
    'attestation',         # <-- модуль 2.3 «Промежуточная аттестация»
    'schedule',            # <-- модуль 2.4 «Формирование расписания»
    'hr',                  # <-- модуль 2.5 «Кадровый учёт»
    'reporting',           # <-- модуль 2.6 «Отчётность и интеграция»
    'accounts',            # <-- модуль 2.7 «Авторизация и роли» (+ аудит, защита)
]

# --- Интеграции (модуль 2.6) ---
REGISTRY_API_ENABLED = False       # True — реальная отправка (нужен доступ к серверу)
REGISTRY_API_ENDPOINT = 'https://registry.spo.example.ru/api/v1/students'
SMEV_ENABLED = False               # True — реальное подключение (транспорт + сертификаты)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.SecurityHeadersMiddleware',   # CSP и дополнительные заголовки
    'accounts.middleware.AuditLogMiddleware',          # журнал действий (аудит)
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.roles_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------------------
# База данных: подключение под отдельной ролью приложения (минимальные права)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'college_sys'),
        'USER': os.environ.get('DB_USER', 'college_app'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        # Защита соединения и устойчивость
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 10,
            # Шифрование трафика к БД (при настроенном SSL на сервере):
            # 'sslmode': 'require',
        },
    }
}

# ---------------------------------------------------------------------------
# Пароли пользователей: усиленные требования
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
     'OPTIONS': {'max_similarity': 0.7}},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Безопасность сессий и cookies
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True          # cookie недоступна из JavaScript (защита от XSS)
SESSION_COOKIE_SAMESITE = 'Lax'         # защита от CSRF
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 8        # сессия 8 часов
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # сессия закрывается с браузером

# При работе по HTTPS (продакшен) — защищённые cookies и HSTS
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', not DEBUG)
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000        # 1 год
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True                    # запрет MIME-sniffing
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'                              # защита от clickjacking
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Маскирование персональных данных в интерфейсе
MASK_SENSITIVE_DATA = env_bool('MASK_SENSITIVE_DATA', True)

# ---------------------------------------------------------------------------
# Защита от перебора паролей (см. accounts.views.RateLimitedLoginView)
# ---------------------------------------------------------------------------
LOGIN_ATTEMPTS_LIMIT = 5          # неудачных попыток
LOGIN_ATTEMPTS_WINDOW = 15        # за последние N минут
LOGIN_LOCKOUT_MINUTES = 15        # блокировка на N минут

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# --- Авторизация (модуль 2.7) ---
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/accounts/profile/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Логирование: события безопасности и ошибки
# ---------------------------------------------------------------------------
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'security.log'),
            'maxBytes': 5 * 1024 * 1024,   # 5 МБ
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'app.log'),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'college.security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['app_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
