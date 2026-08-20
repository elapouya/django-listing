#
# Created : 2026-08-20
#
# Tests for the "paginate by primary key" optimization (jgate#2041) :
# deep pages of a wide listing must not project all the discarded OFFSET rows.
#
from django.db import connection
from django.db.models import Count
from django.template import RequestContext
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from django_listing import Listing
from django_listing.paginators import Paginator

from .models import Author, Book, Review


class BookListing(Listing):
    model = Book
    per_page = 5


def make_listing(data, listing_class=BookListing, url="/", **params):
    request = RequestFactory().get(url)
    context = RequestContext(request)
    lsg = listing_class()
    lsg.init(data, context, **params)
    lsg.render_init_context(context)
    return lsg


def page_of(data, page=1, listing_class=BookListing, url=None, **params):
    lsg = make_listing(
        data, listing_class=listing_class, url=url or f"/?page={page}", **params
    )
    lsg.records.compute_current_page_records()
    return lsg


class PaginateByPkTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.authors = [Author.objects.create(name=f"author{i}") for i in range(3)]
        cls.books = [
            Book.objects.create(
                title=f"book{i:02d}",
                author=cls.authors[i % 3],
                # a lot of ties, so that ordering on category alone is ambiguous
                category=f"cat{i % 2}",
            )
            for i in range(30)
        ]
        for book in cls.books[:4]:
            for stars in (1, 3, 5):
                Review.objects.create(book=book, stars=stars)

    def plain_slice(self, qs, page, per_page=5, sort=None):
        """The rows a classic OFFSET/LIMIT slice would return"""
        lsg = make_listing(qs, sort=sort)
        order_by = lsg.records.get_order_by()
        bottom = (page - 1) * per_page
        return list(qs.order_by(*order_by)[bottom : bottom + per_page])


class PageContentTest(PaginateByPkTestCase):
    def test_deep_page_returns_the_same_rows_as_a_plain_slice(self):
        lsg = page_of(Book.objects.all(), page=4)
        self.assertEqual(
            [b.pk for b in lsg.current_page],
            [b.pk for b in Book.objects.order_by("pk")[15:20]],
        )

    def test_last_page_clamp_is_unchanged(self):
        lsg = page_of(Book.objects.all(), url="/?page=last")
        self.assertEqual(
            [b.pk for b in lsg.current_page],
            [b.pk for b in Book.objects.order_by("pk")[25:30]],
        )

    def test_ordering_is_preserved_on_the_page(self):
        lsg = page_of(Book.objects.all(), page=2, sort="-title")
        titles = [b.title for b in lsg.current_page]
        self.assertEqual(titles, sorted(titles, reverse=True))
        self.assertEqual(titles, ["book24", "book23", "book22", "book21", "book20"])

    def test_pages_do_not_overlap_when_sorting_on_a_column_full_of_ties(self):
        seen = []
        for page in range(1, 7):
            lsg = page_of(Book.objects.all(), page=page, sort="category")
            seen += [b.pk for b in lsg.current_page]
        self.assertEqual(len(seen), 30)
        self.assertEqual(len(set(seen)), 30)


class PkQueryTest(PaginateByPkTestCase):
    def captured_page_queries(self, *args, **kwargs):
        with CaptureQueriesContext(connection) as captured:
            lsg = page_of(*args, **kwargs)
            list(lsg.current_page)
        return lsg, [q["sql"] for q in captured.captured_queries]

    def test_page_rows_are_fetched_from_a_light_primary_key_query(self):
        lsg, queries = self.captured_page_queries(Book.objects.all(), page=4)
        selects = [q for q in queries if not q.startswith("SELECT COUNT")]
        self.assertEqual(len(selects), 2)
        self.assertEqual(
            selects[0],
            'SELECT "tests_book"."id" FROM "tests_book" '
            'ORDER BY "tests_book"."id" ASC LIMIT 5 OFFSET 15',
        )
        self.assertIn('"tests_book"."id" IN (', selects[1])

    def test_paginate_by_pk_can_be_disabled(self):
        lsg, queries = self.captured_page_queries(
            Book.objects.all(), page=4, paginate_by_pk=False
        )
        selects = [q for q in queries if not q.startswith("SELECT COUNT")]
        self.assertEqual(len(selects), 1)
        self.assertIn("LIMIT 5 OFFSET 15", selects[0])
        self.assertEqual(
            [b.pk for b in lsg.current_page],
            [b.pk for b in Book.objects.order_by("pk")[15:20]],
        )

    def test_select_related_columns_are_only_fetched_for_the_page(self):
        lsg, queries = self.captured_page_queries(
            Book.objects.select_related("author"), page=4
        )
        selects = [q for q in queries if not q.startswith("SELECT COUNT")]
        self.assertEqual(len(selects), 2)
        self.assertNotIn("tests_author", selects[0])
        self.assertIn("tests_author", selects[1])


class FallbackTest(PaginateByPkTestCase):
    """Pièges : cases where paginating on the pk is wrong and must be skipped"""

    def assert_single_select(self, queries):
        selects = [q for q in queries if not q.startswith("SELECT COUNT")]
        self.assertEqual(len(selects), 1, "\n".join(selects))

    def test_sequence_data_is_still_paginated(self):
        data = [dict(id=i, title=f"row{i:02d}") for i in range(30)]
        lsg = page_of(data, page=4, listing_class=Listing, per_page=5)
        self.assertEqual(
            [item.obj["title"] for item in lsg.current_page],
            ["row15", "row16", "row17", "row18", "row19"],
        )

    def test_values_annotate_queryset_falls_back_on_a_plain_slice(self):
        # group_by feature turns data into a .values().annotate() queryset :
        # there is no pk anymore in the rows
        qs = Book.objects.values("category").annotate(count=Count("id"))
        with CaptureQueriesContext(connection) as captured:
            lsg = page_of(qs, page=1, sort="category")
            rows = list(lsg.current_page)
        self.assert_single_select([q["sql"] for q in captured.captured_queries])
        self.assertEqual(
            sorted(rows, key=lambda r: r["category"]),
            [{"category": "cat0", "count": 15}, {"category": "cat1", "count": 15}],
        )

    def test_multivalued_join_page_returns_the_same_rows_as_a_plain_slice(self):
        # a filter on a reverse relation duplicates rows : slicing on the pk
        # would not return the same number of rows
        qs = Book.objects.filter(reviews__stars__gte=1)
        expected = self.plain_slice(qs, page=1)
        lsg = page_of(qs, page=1)
        self.assertEqual(len(list(lsg.current_page)), len(expected))
        self.assertEqual([b.pk for b in lsg.current_page], [b.pk for b in expected])

    def test_combined_queryset_falls_back_on_a_plain_slice(self):
        qs = Book.objects.filter(category="cat0").union(
            Book.objects.filter(category="cat1")
        )
        lsg = page_of(qs, page=2)
        self.assertEqual(len(list(lsg.current_page)), 5)


class DuplicatedRowsBeltTest(PaginateByPkTestCase):
    """The pk slicing must give up as soon as it gets duplicated primary keys,
    even when the query did not look like it would duplicate rows"""

    def test_duplicated_page_pks_fall_back_on_a_plain_slice(self):
        class BlindPaginator(Paginator):
            def has_multivalued_join(self, qs):
                return False

        qs = Book.objects.filter(reviews__stars__gte=1)
        expected = self.plain_slice(qs, page=1)
        lsg = page_of(qs, page=1, paginator_class=BlindPaginator)
        self.assertEqual([b.pk for b in lsg.current_page], [b.pk for b in expected])


class AggregateAnnotationTest(PaginateByPkTestCase):
    def test_aggregate_annotation_is_still_paginated_on_the_pk(self):
        # an aggregate annotation groups by pk : rows are not duplicated,
        # so the pk slicing is safe and must be used
        qs = Book.objects.annotate(nb_reviews=Count("reviews"))
        with CaptureQueriesContext(connection) as captured:
            lsg = page_of(qs, page=1)
            rows = list(lsg.current_page)
        selects = [
            q["sql"]
            for q in captured.captured_queries
            if not q["sql"].startswith("SELECT COUNT")
        ]
        self.assertEqual(len(selects), 2, "\n".join(selects))
        self.assertEqual([b.pk for b in rows], [b.pk for b in self.books[:5]])
        self.assertEqual([b.nb_reviews for b in rows], [3, 3, 3, 3, 0])


class PkTiebreakTest(PaginateByPkTestCase):
    def order_by_of(self, data, **params):
        lsg = make_listing(data, **params)
        return list(lsg.records.order_queryset(data).query.order_by)

    def test_a_pk_tiebreak_is_appended_to_the_ordering(self):
        self.assertEqual(
            self.order_by_of(Book.objects.all(), sort="category"), ["category", "pk"]
        )

    def test_the_pk_tiebreak_is_not_appended_twice(self):
        self.assertEqual(self.order_by_of(Book.objects.all()), ["pk"])
        self.assertEqual(self.order_by_of(Book.objects.all(), sort="-id"), ["-id"])

    def test_values_annotate_queryset_gets_no_pk_tiebreak(self):
        qs = Book.objects.values("category").annotate(count=Count("id"))
        self.assertEqual(self.order_by_of(qs, sort="category"), ["category"])
