#
# Created : 2026-09-25
#
# Tests for the rollback of the writes made before an error (jgate#2161) : the
# view turns the exception into a 500 response itself, so ATOMIC_REQUESTS would
# commit the half-done work if the view did not mark the transaction for rollback.
#
from django.db import transaction
from django.test import RequestFactory, TestCase

from django_listing.exceptions import ListingException
from django_listing.views import ListingView

from .models import Author


class FailingAjaxView(ListingView):
    def manage_listing_ajax_request(self, request, *args, **kwargs):
        Author.objects.create(name="half saved")
        raise ValueError("price computation failed")


class FailingPostView(ListingView):
    def manage_listing_post(self, request, *args, **kwargs):
        Author.objects.create(name="half saved")
        raise ListingException("listing failed")


def post(view_class, ajax=True):
    headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"} if ajax else {}
    request = RequestFactory().post("/", {}, **headers)
    return view_class.as_view()(request)


class RollbackOnErrorTest(TestCase):
    def call_atomic(self, view_class, ajax=True):
        # Same as ATOMIC_REQUESTS : the view runs inside an atomic block
        with transaction.atomic():
            response = post(view_class, ajax)
        return response

    def test_ajax_exception_rolls_back(self):
        with self.assertLogs("django_listing", "ERROR"):
            response = self.call_atomic(FailingAjaxView)
        self.assertEqual(response.status_code, 500)
        self.assertFalse(Author.objects.exists())

    def test_listing_exception_rolls_back(self):
        response = self.call_atomic(FailingPostView, ajax=False)
        self.assertEqual(response.status_code, 500)
        self.assertFalse(Author.objects.exists())

    def test_writes_before_the_view_are_rolled_back_too(self):
        with transaction.atomic():
            Author.objects.create(name="written by the request before the view")
            with self.assertLogs("django_listing", "ERROR"):
                post(FailingAjaxView)
        self.assertFalse(Author.objects.exists())


class NoAtomicBlockTest(TestCase):
    # Outside any atomic block (autocommit, no ATOMIC_REQUESTS) there is nothing
    # to roll back : the view must still answer its 500, not raise.
    def test_ajax_exception_without_atomic_block(self):
        connection = transaction.get_connection()
        in_atomic_block = connection.in_atomic_block
        # TestCase wraps each test in an atomic block : hide it to simulate autocommit
        connection.in_atomic_block = False
        try:
            with self.assertLogs("django_listing", "ERROR"):
                response = post(FailingAjaxView)
        finally:
            connection.in_atomic_block = in_atomic_block
        self.assertEqual(response.status_code, 500)
