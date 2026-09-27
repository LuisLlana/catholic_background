# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Settings. Everything that changes between installations comes from environment
variables (see .env.example); nothing secret is stored in the code.
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    return env(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name):
    return [item.strip() for item in env(name, "").split(",") if item.strip()]


SECRET_KEY = env("SECRET_KEY", "insecure-development-key-change-me")

# Base path of the application: it is the address the applications take the image
# from (/background?ts=...), and every other page hangs from it (/background/admin/...).
# Empty to serve everything from the root of the host.
BASE_PATH = env("BASE_PATH", "background").strip("/")
PREFIX = f"/{BASE_PATH}/" if BASE_PATH else "/"
DEBUG = env_bool("DEBUG")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS") or (["*"] if DEBUG else [])
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
    "accounts",
    "artworks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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

# Database: SQLite by default; PostgreSQL or MariaDB by changing DATABASE_URL, e.g.
#   postgres://user:password@host/catholic   mysql://user:password@host/catholic
DATA_DIR = Path(env("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", f"sqlite:///{DATA_DIR / 'db.sqlite3'}"), conn_max_age=600
    )
}
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    # Recommended for MariaDB/MySQL: strict mode and full Unicode
    DATABASES["default"].setdefault("OPTIONS", {}).update({
        "charset": "utf8mb4",
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
    })
    # A conditional unique constraint of allauth's e-mail table (not used: login is only with Google/Microsoft)
    SILENCED_SYSTEM_CHECKS = ["models.W036"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------- login
# No passwords: only Google and Microsoft accounts.
AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "home"
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_ONLY = True
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_AUTO_SIGNUP = True
# The same person entering with Google and with Microsoft (same e-mail) is one user
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_ADAPTER = "accounts.adapters.SocialAccountAdapter"

SOCIALACCOUNT_PROVIDERS = {}
if env("GOOGLE_CLIENT_ID"):
    SOCIALACCOUNT_PROVIDERS["google"] = {
        "APPS": [{"client_id": env("GOOGLE_CLIENT_ID"), "secret": env("GOOGLE_CLIENT_SECRET", "")}],
        "SCOPE": ["profile", "email"],
    }
if env("MICROSOFT_CLIENT_ID"):
    SOCIALACCOUNT_PROVIDERS["microsoft"] = {
        "APPS": [{
            "client_id": env("MICROSOFT_CLIENT_ID"),
            "secret": env("MICROSOFT_CLIENT_SECRET", ""),
            # "common": personal and organization accounts
            "settings": {"tenant": env("MICROSOFT_TENANT", "common")},
        }],
    }

# Users with these e-mails become administrators when they log in
ADMIN_EMAILS = [e.lower() for e in env_list("ADMIN_EMAILS")]
# Users from these domains become editors automatically; others wait for approval
AUTO_APPROVE_DOMAINS = [d.lower() for d in env_list("AUTO_APPROVE_DOMAINS")]

# ---------------------------------------------------------------- language and time
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "Europe/Madrid")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------- files
STATIC_URL = f"{PREFIX}static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = f"{PREFIX}media/"
MEDIA_ROOT = DATA_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 40 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Cookies only for this application, not for the rest of the host
SESSION_COOKIE_PATH = PREFIX
CSRF_COOKIE_PATH = PREFIX

# ---------------------------------------------------------------- behind nginx (HTTPS)
if env_bool("BEHIND_PROXY", not DEBUG):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
# Take the client IP from X-Forwarded-For (only if nginx sets it)
TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", not DEBUG)

# ---------------------------------------------------------------- the service
CATHOLIC_BACKGROUND = {
    # Liturgical calendar (Spain: Epiphany on 6 January, Ascension and Corpus on Sunday)
    "EPIPHANY_ON_SUNDAY": env_bool("EPIPHANY_ON_SUNDAY", False),
    "ASCENSION_ON_SUNDAY": env_bool("ASCENSION_ON_SUNDAY", True),
    "CORPUS_ON_SUNDAY": env_bool("CORPUS_ON_SUNDAY", True),
    # Images
    "MIN_IMAGE_SIDE": int(env("MIN_IMAGE_SIDE", "1000")),
    "MAX_IMAGE_MB": int(env("MAX_IMAGE_MB", "25")),
    # Privacy: days that access logs with IP addresses are kept
    "ACCESS_LOG_DAYS": int(env("ACCESS_LOG_DAYS", "30")),
    # Shown on the privacy page
    "PRIVACY_CONTROLLER": env("PRIVACY_CONTROLLER", "Luis Llana"),
    "PRIVACY_CONTACT": env("PRIVACY_CONTACT", "luis.llana.diaz@gmail.com"),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "WARNING")},
}
