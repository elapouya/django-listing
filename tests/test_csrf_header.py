#
# Created : 2026-09-11
#
# Tests for the CSRF token handling of the AJAX requests (jgate#2116) :
# django-listing must follow the CSRF configuration of the host application
# and send the token in the header Django expects, never in the request body.
#
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.template import Template, RequestContext
from django.test import RequestFactory, SimpleTestCase, override_settings

STATIC_JS = Path(__file__).resolve().parent.parent / (
    "django_listing/static/django_listing/js"
)


def reload_listing_settings():
    # ready() computes the template context from the settings once at startup:
    # replay it so that an override_settings() is taken into account.
    apps.get_app_config("django_listing").ready()


def listing_context():
    return settings.django_listing_settings.context


def render_footer():
    request = RequestFactory().get("/")
    tpl = Template("{% load django_listing %}{% render_listing_footer %}")
    # The host applications enable the "request" context processor, the test
    # settings do not: pass the request explicitly, as the footer tag reads it.
    return tpl.render(RequestContext(request, {"request": request}))


class CsrfContextTest(SimpleTestCase):
    def tearDown(self):
        reload_listing_settings()

    def test_context_exposes_the_default_csrf_configuration(self):
        reload_listing_settings()
        ctx = listing_context()
        self.assertEqual(ctx["CSRF_COOKIE_NAME"], "csrftoken")
        self.assertEqual(ctx["CSRF_HEADER_NAME"], "X-CSRFTOKEN")
        self.assertIs(ctx["CSRF_COOKIE_READABLE"], True)

    def test_context_follows_a_renamed_csrf_cookie_and_header(self):
        with override_settings(
            CSRF_COOKIE_NAME="synerj_csrf", CSRF_HEADER_NAME="HTTP_X_SYNERJ_CSRF"
        ):
            reload_listing_settings()
            ctx = listing_context()
        self.assertEqual(ctx["CSRF_COOKIE_NAME"], "synerj_csrf")
        self.assertEqual(ctx["CSRF_HEADER_NAME"], "X-SYNERJ-CSRF")

    def test_cookie_is_not_readable_when_the_token_lives_in_the_session(self):
        with override_settings(CSRF_USE_SESSIONS=True):
            reload_listing_settings()
            readable = listing_context()["CSRF_COOKIE_READABLE"]
        self.assertIs(readable, False)

    def test_cookie_is_not_readable_when_httponly(self):
        with override_settings(CSRF_COOKIE_HTTPONLY=True):
            reload_listing_settings()
            readable = listing_context()["CSRF_COOKIE_READABLE"]
        self.assertIs(readable, False)


class FooterCsrfTest(SimpleTestCase):
    def test_footer_declares_the_csrf_cookie_and_header_for_the_javascript(self):
        html = render_footer()
        self.assertIn('const djlst_csrf_cookie_name = "csrftoken";', html)
        self.assertIn('const djlst_csrf_header_name = "X-CSRFTOKEN";', html)
        self.assertIn("const djlst_csrf_cookie_readable = true;", html)

    def test_footer_sends_the_token_in_a_header_not_in_the_request_body(self):
        html = render_footer()
        self.assertIn("$.ajaxPrefilter(", html)
        self.assertIn(
            "setRequestHeader(djlst_csrf_header_name, djlst_get_csrf_token())", html
        )
        self.assertNotIn("ajaxSetup", html)
        self.assertNotIn("csrfmiddlewaretoken", html)

    def test_footer_still_renders_the_page_csrf_token(self):
        html = render_footer()
        self.assertRegex(html, r'const csrf_token = "[A-Za-z0-9]{64}";')


class JavascriptCsrfContractTest(SimpleTestCase):
    """The footer prefilter calls a getter that the shipped scripts must define."""

    def test_source_defines_the_token_getter_reading_the_configured_cookie(self):
        js = (STATIC_JS / "django_listing.js").read_text()
        self.assertIn("function djlst_get_csrf_token()", js)
        self.assertIn("Cookies.get(djlst_csrf_cookie_name)", js)
        self.assertNotIn("update_csrf_token", js)
        self.assertNotIn("ajaxSetup", js)
        self.assertNotIn("csrftoken", js)

    def test_minified_script_is_regenerated_from_the_source(self):
        js = (STATIC_JS / "django_listing.min.js").read_text()
        self.assertIn("djlst_get_csrf_token", js)
        self.assertNotIn("update_csrf_token", js)
