import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


env_file = BASE_DIR / ".env"
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#") and "=" in entry:
            name, value = entry.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-only-insecure-key-change-before-deployment")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "clinic.apps.ClinicConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "petcare.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "petcare.wsgi.application"

database_engine = os.environ.get("DB_ENGINE", "sqlite").strip().lower()
if database_engine in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", ""),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", ""),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {
                "sslmode": os.environ.get("DB_SSLMODE", "prefer" if DEBUG else "require"),
                "connect_timeout": 5,
            },
        }
    }
    missing_database_settings = [name for name in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST") if not os.environ.get(name)]
    if not DEBUG and missing_database_settings:
        raise RuntimeError(f"PostgreSQL production configuration is missing: {', '.join(missing_database_settings)}")
elif database_engine == "sqlite" and DEBUG:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    raise RuntimeError("Production must use PostgreSQL. Set DB_ENGINE=postgresql and configure DB_* environment variables.")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", not DEBUG)
CSRF_COOKIE_HTTPONLY = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31_536_000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)

if not DEBUG and SECRET_KEY == "local-only-insecure-key-change-before-deployment":
    raise RuntimeError("Set DJANGO_SECRET_KEY to a strong secret in production.")
if not DEBUG and (not ALLOWED_HOSTS or set(ALLOWED_HOSTS) <= {"127.0.0.1", "localhost"}):
    raise RuntimeError("Set DJANGO_ALLOWED_HOSTS to the public hostname in production.")
