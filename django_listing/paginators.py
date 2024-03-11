#
# Created : 2018-02-06
#
# @author: Eric Lapouyade
#

from django.core.paginator import Paginator as DjangoPaginator, Page as DjangoPage
from django.utils.translation import pgettext_lazy

from .context import RenderContext
from .theme_config import ThemeAttribute, ThemeTemplate

__all__ = [
    "NoIconButtonPaginator",
    "NoIconButtonPaginatorMixin",
    "NoTextButtonPaginator",
    "NoTextButtonPaginatorMixin",
    "Paginator",
]

PAGINATOR_PARAMS_KEYS = {
    "fast_page_next_tpl",
    "fast_page_prev_tpl",
    "fast_page_step",
    "goto_page_tpl",
    "has_editable_page_info",
    "has_first_last",
    "has_goto_page",
    "has_page_info",
    "has_prev_next",
    "has_row_info",
    "hide_disabled_buttons",
    "hide_single_page",
    "in_footer",
    "page_info_tpl",
    "page_row_tpl",
    "page_scale_ellipsis",
    "page_scale_size",
    "parts_order",
    "template_name",
    "theme_button_a_class",
    "theme_button_li_class",
    "theme_button_text_class",
    "theme_fast_next_icon",
    "theme_fast_page_has_icon",
    "theme_fast_page_has_text",
    "theme_fast_prev_icon",
    "theme_first_icon",
    "theme_first_last_has_icon",
    "theme_first_last_has_text",
    "theme_last_icon",
    "theme_next_icon",
    "theme_prev_icon",
    "theme_prev_next_has_icon",
    "theme_prev_next_has_text",
}


class Paginator(DjangoPaginator):
    template_name = ThemeTemplate("paginator.html")
    has_page_info = True
    has_editable_page_info = False
    page_info_tpl = pgettext_lazy("paginator", "Page {page_number} of {nb_pages}")
    has_row_info = False
    row_info_tpl = pgettext_lazy("paginator", "{row_first}-{row_last} of {nb_rows}")
    has_prev_next = True
    prev_text = pgettext_lazy("paginator", "Previous")
    next_text = pgettext_lazy("paginator", "Next")
    has_first_last = False
    first_text = pgettext_lazy("paginator", "First")
    last_text = pgettext_lazy("paginator", "Last")
    fast_page_step = 0
    fast_page_prev_tpl = "-{step}"
    fast_page_next_tpl = "+{step}"
    page_scale_size = 0
    page_scale_ellipsis = 0
    hide_disabled_buttons = False
    hide_single_page = False
    parts_order = "first,fastprev,prev,pageinfo,rowinfo,scale," "next,fastnext,last"
    has_goto_page = False
    goto_page_tpl = pgettext_lazy("paginator", "Go to page {goto_form}")
    in_footer = False

    theme_first_last_has_icon = ThemeAttribute("paginator_theme_first_last_has_icon")
    theme_first_last_has_text = ThemeAttribute("paginator_theme_first_last_has_text")
    theme_first_icon = ThemeAttribute("paginator_theme_first_icon")
    theme_last_icon = ThemeAttribute("paginator_theme_last_icon")
    theme_fast_page_has_icon = ThemeAttribute("paginator_theme_fast_page_has_icon")
    theme_fast_page_has_text = ThemeAttribute("paginator_theme_fast_page_has_text")
    theme_fast_prev_icon = ThemeAttribute("paginator_theme_fast_prev_icon")
    theme_fast_next_icon = ThemeAttribute("paginator_theme_fast_next_icon")
    theme_prev_next_has_icon = ThemeAttribute("paginator_theme_prev_next_has_icon")
    theme_prev_next_has_text = ThemeAttribute("paginator_theme_prev_next_has_text")
    theme_prev_icon = ThemeAttribute("paginator_theme_prev_icon")
    theme_next_icon = ThemeAttribute("paginator_theme_next_icon")
    theme_button_a_class = ThemeAttribute("paginator_theme_button_a_class")
    theme_button_li_class = ThemeAttribute("paginator_theme_button_li_class")
    theme_button_text_class = ThemeAttribute("paginator_theme_button_text_class")

    def __init__(
        self, listing, object_list, per_page, orphans=0, allow_empty_first_page=True
    ):
        super().__init__(object_list, per_page, orphans, allow_empty_first_page)
        self.listing = listing
        for k in PAGINATOR_PARAMS_KEYS:
            listing_key = "paginator_" + k
            if hasattr(listing, listing_key):
                setattr(self, k, getattr(listing, listing_key))
        if isinstance(self.parts_order, str):
            self.parts_order = self.parts_order.replace(" ", "")
            self.parts_order = list(
                map(lambda s: s.split(","), self.parts_order.split(";"))
            )

    def validate_number(self, number):
        if number == "last":
            number = self.num_pages
        return super().validate_number(number)

    def page(self, number):
        """Return a Page object for the given 1-based page number."""
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if bottom > self.count - self.per_page:
            bottom = max(0, self.count - self.per_page)
            top = self.count
        page = Page(self.object_list[bottom:top], number, self, bottom, top)
        return page

    def get_context(self):
        get_url = self.listing.get_url
        page = self.listing.current_page
        fast_page_prev = max(1, page.number - self.fast_page_step)
        fast_page_next = min(self.num_pages, page.number + self.fast_page_step)
        beginning_ellipsis_pages = []
        beginning_ellipsis_display = True
        ending_ellipsis_pages = []
        ending_ellipsis_display = True
        if self.page_scale_size:
            scale_range_min = max(1, page.number - int(self.page_scale_size / 2))
            scale_range_max = min(
                scale_range_min + self.page_scale_size - 1, self.num_pages
            )

            if self.page_scale_ellipsis:
                beginning_ellipsis_pages = [
                    (p, get_url(page=p), p == page.number)
                    for p in range(
                        1, min(self.page_scale_ellipsis + 1, scale_range_min)
                    )
                ]
                if scale_range_min < self.page_scale_ellipsis + 2:
                    beginning_ellipsis_display = False
                if scale_range_max == self.num_pages:
                    scale_range_min = max(1, self.num_pages - self.page_scale_size)
                else:
                    ending_ellipsis_range_min = max(
                        scale_range_max + 1,
                        self.num_pages - self.page_scale_ellipsis + 1,
                    )
                    if ending_ellipsis_range_min == scale_range_max + 1:
                        beginning_ellipsis_display = False
                    ending_ellipsis_range_max = self.num_pages
                    ending_ellipsis_pages = [
                        (p, get_url(page=p), p == page.number)
                        for p in range(
                            ending_ellipsis_range_min, ending_ellipsis_range_max + 1
                        )
                    ]

            scale_pages = [
                (p, get_url(page=p), p == page.number)
                for p in range(scale_range_min, scale_range_max + 1)
            ]
        else:
            scale_pages = []

        if self.has_editable_page_info or self.has_goto_page:
            goto_form = '<form class="goto-page">'
            goto_form += self.listing.get_hiddens_html(without="page")
            goto_form += (
                '<input type="text" '
                'value="{val}" '
                'name="page{suffix}">'.format(
                    val=page.number, suffix=self.listing.suffix
                )
            )
            goto_form += "</form>"
        else:
            goto_form = ""

        if self.has_editable_page_info:
            page_number = goto_form
        else:
            page_number = page.number

        nb_page_rows = page.end_index() - page.start_index() + 1

        return RenderContext(
            first_page_url=get_url(page=1),
            last_page_url=get_url(page=self.num_pages),
            prev_page_url=get_url(
                page=page.previous_page_number() if page.number > 1 else 1
            ),
            next_page_url=get_url(
                page=page.next_page_number()
                if page.number < self.num_pages
                else self.num_pages
            ),
            fast_page_prev_url=get_url(page=fast_page_prev),
            fast_page_next_url=get_url(page=fast_page_next),
            fast_page_prev_text=self.fast_page_prev_tpl.format(
                step=self.fast_page_step
            ),
            fast_page_next_text=self.fast_page_next_tpl.format(
                step=self.fast_page_step
            ),
            scale_pages=scale_pages,
            beginning_ellipsis_pages=beginning_ellipsis_pages,
            beginning_ellipsis_display=beginning_ellipsis_display,
            ending_ellipsis_pages=ending_ellipsis_pages,
            ending_ellipsis_display=ending_ellipsis_display,
            nb_page_rows=nb_page_rows,
            page_info=self.page_info_tpl.format(
                page_number=page_number, nb_pages=self.num_pages
            ),
            row_info=self.row_info_tpl.format(
                row_first=page.start_index(),
                row_last=page.end_index(),
                nb_rows=self.count,
                nb_page_rows=nb_page_rows,
            ),
            goto_page=self.goto_page_tpl.format(goto_form=goto_form),
            show_paginator_single_page=(
                self.num_pages > 1 or not self.hide_single_page
            ),
            current_page=page,
            paginator=self,
        )


class Page(DjangoPage):
    def __init__(self, object_list, number, paginator, bottom=None, top=None):
        super().__init__(object_list, number, paginator)
        self._bottom = bottom
        self._top = top

    def start_index(self):
        """
        Return the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        # Special case, return zero if no items.
        if self.paginator.count == 0:
            return 0
        # Special case for J-Gate because last page need special calculation
        if self._bottom is not None:
            return self._bottom + 1
        return (self.paginator.per_page * (self.number - 1)) + 1

    def end_index(self):
        """
        Return the 1-based index of the last object on this page,
        relative to total objects found (hits).
        """
        # Special case for J-Gate because last page need special calculation
        if self._top is not None:
            return self._top
        # Special case for the last page because there can be orphans.
        if self.number == self.paginator.num_pages:
            return self.paginator.count
        return self.number * self.paginator.per_page


class NoTextButtonPaginatorMixin:
    theme_first_last_has_text = False
    theme_fast_page_has_text = False
    theme_prev_next_has_text = False


class NoTextButtonPaginator(NoTextButtonPaginatorMixin, Paginator):
    pass


class NoIconButtonPaginatorMixin:
    theme_first_last_has_icon = False
    theme_fast_page_has_icon = False
    theme_prev_next_has_icon = False


class NoIconButtonPaginator(NoIconButtonPaginatorMixin, Paginator):
    pass
