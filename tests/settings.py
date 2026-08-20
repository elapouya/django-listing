#
# Minimal Django settings to run django-listing unit tests
#
SECRET_KEY = "django-listing-tests"
DEBUG = False
USE_TZ = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "dal",
    "dal_select2",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "django_listing",
    "tests",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

STATIC_URL = "/static/"
MIDDLEWARE = []
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
