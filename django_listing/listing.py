#
# Created : 2018-02-09
#
# @author: Eric Lapouyade
#

import collections
import logging
import pprint
from urllib.parse import urlsplit, urlunsplit

import tablib
from django import forms
from django.conf import settings
from django.db.models import Model
from django.db.models.query import QuerySet
from django.http import QueryDict
from django.middleware.csrf import get_token as get_csrf_token
from django.template import loader
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy

from django_listing import (
    EXPORT_FORMATS,
    EXPORT_FORMATS_KEEP_ORIGINAL_TYPE,
    EXPORT_FORMATS_USE_COL_NAME,
)

from .columns import COLUMNS_PARAMS_KEYS, ModelColumns, SelectionColumn, SequenceColumns
from .context import RenderContext
from .exceptions import *
from .filters import FILTERS_PARAMS_KEYS, Filters
from .html_attributes import HTMLAttributes
from .listing_form import LISTING_FORM_PARAMS_KEYS, ListingBaseForm
from .paginators import PAGINATOR_PARAMS_KEYS, Paginator
from .record import RecordManager
from .theme_config import ThemeAttribute, ThemeTemplate
from .toolbar import TOOLBAR_PARAMS_KEYS, Toolbar
from .utils import init_dicts_from_class

pp = pprint.PrettyPrinter(indent=4)

__all__ = ["ListingVariations", "Listing", "DivListing", "logger"]

logger = logging.getLogger("django_listing")

LISTING_ROWS_PER_PAGE = 20
LISTING_ROWS_PER_PAGE_MAX = 500
LISTING_SUFFIX_REQUEST_DATA_FIELD = "_listing_suffix_data"
LISTING_SUFFIX_PATTERN = "-{}"
LISTING_SELECTION_INPUT_NAME_KEY = "selected_rows"
LISTING_SELECTION_CHECKBOX_NAME = "selection_checkbox"
LISTING_SELECTION_HOVER_CSS_CLASS = "hover"
LISTING_SELECTOR_CSS_CLASS = "row-selector"

# only these parameters are allowed in the query string.
LISTING_QUERY_STRING_KEYS = {
    "editing",
    "editing_columns",
    "editing_row_pk",
    "export",
    "page",
    "per_page",
    "select_columns",
    "selecting",
    "sort",
    "theme",
    "variation",
}
LISTING_QUERY_STRING_INT_KEYS = {"page", "per_page", "variation", "editing_row_pk"}
LISTING_NOT_PERSISTENT_QUERY_STRING_KEYS = set()

# Only these attributes can be modified outside the class (in django templates,
# views, listings instances ...)
LISTING_PARAMS_KEYS = {
    "accept_ajax",
    "action_button_cancel_label",
    "action_button_edit_label",
    "action_button_update_label",
    "action_button_upload_label",
    "action_footer_template_name",
    "action_header_template_name",
    "ajax_part",
    "ajax_request",
    "allow_empty_first_page",
    "anchor_hash",
    "attrs",
    "columns_headers",
    "data",
    "datetimepicker_date_format",
    "datetimepicker_datetime_format",
    "datetimepicker_time_format",
    "div_row_template_name",
    "div_rows",
    "div_template_name",
    "edit_on_demand",
    "editable",
    "editable_columns",
    "editing",
    "editing_columns",
    "editing_hidden_columns",
    "editing_row_pk",
    "empty_listing_template_name",
    "empty_table_msg",
    "exclude_columns",
    "export",
    "filters",
    "footer_snippet",
    "footer_template_name",
    "form",
    "global_context",
    "has_footer",
    "has_footer_action_buttons",
    "has_header",
    "has_paginator",
    "has_upload",
    "id",
    "is_small_device_localized",
    "link_object_columns",
    "listing_template_name",
    "name",
    "onready_snippet",
    "orphans",
    "page",
    "paginator_class",
    "per_page",
    "per_page_max",
    "primary_key",
    "record_label",
    "record_label_plural",
    "row_attrs",
    "row_form_base_class",
    "row_inner_div_tpl",
    "save_to_database",
    "select_columns",
    "selectable",
    "selecting",
    "selection_initial",
    "selection_key",
    "selection_menu_id",
    "selection_mode",
    "selection_multiple",
    "selection_overlay_template_name",
    "selection_position",
    "small_device_header_style",
    "small_device_max_width",
    "sort",
    "sortable",
    "suffix",
    "theme",
    "theme_action_button_cancel_icon",
    "theme_action_button_class",
    "theme_action_button_edit_icon",
    "theme_action_button_update_icon",
    "theme_action_button_upload_icon",
    "theme_button_active_class",
    "theme_button_disabled_class",
    "theme_div_row_container_class",
    "theme_localized_small_device_styles_width",
    "theme_sort_asc_class",
    "theme_sort_asc_icon",
    "theme_sort_desc_class",
    "theme_sort_desc_icon",
    "theme_sort_none_icon",
    "theme_sortable_class",
    "theme_sorted_class",
    "theme_spinner_icon",
    "toolbar",
    "toolbar_placement",
    "unsortable",
    "use_datetimepicker",
    "variation",
    "variations",
}

LISTING_VARIATIONS_KEYS = LISTING_PARAMS_KEYS | {"get_url"}
LISTING_FORMSET_PREFIX = "listing"


class ListingBase:
    def __init__(self, *args, **kwargs):
        self.stored_params = {}
        self.stored_columns_params = {}
        self.stored_toolbar_items_params = {}
        self.stored_filters_params = {}
        self.stored_form_params = {}

    def transfert_params_from(self, listing):
        self.stored_params = listing.stored_params
        self.stored_columns_params = listing.stored_columns_params
        self.stored_toolbar_items_params = listing.stored_toolbar_items_params
        self.stored_filters_params = listing.stored_filters_params
        self.stored_form_params = listing.stored_form_params

    def set_attr(self, attr, value):
        setattr(self, attr, value)

    def store_kwargs(self, **kwargs):
        self.stored_params.update(kwargs)

    def store_html_attr(self, listing_attr, html_attr, value):
        html_params = self.stored_params.get(listing_attr)
        if html_params is None:
            self.stored_params[listing_attr] = HTMLAttributes({html_attr: value})
        else:
            html_params.add(html_attr, value)

    def store_column_kwargs(self, name, **kwargs):
        self.stored_columns_params.setdefault(name, {}).update(kwargs)

    def store_column_html_attr(self, name, col_attr, html_attr, value):
        col_params = self.stored_columns_params.get(name)
        if col_params is None:
            param = {col_attr: HTMLAttributes({html_attr: value})}
            self.store_column_kwargs(name, **param)
        else:
            html_params = col_params.setdefault(html_attr, HTMLAttributes())
            html_params.add(html_attr, value)

    def store_toolbar_item_html_attr(self, name, tbi_attr, html_attr, value):
        tbi_params = self.stored_toolbar_items_params.get(name)
        if tbi_params is None:
            param = {tbi_attr: HTMLAttributes({html_attr: value})}
            self.store_toolbar_item_kwargs(name, **param)
        else:
            html_params = tbi_params.setdefault(html_attr, HTMLAttributes())
            html_params.add(html_attr, value)

    def get_column_kwargs(self, name):
        return self.stored_columns_params.get(name)

    def store_toolbar_item_kwargs(self, name, **kwargs):
        self.stored_toolbar_items_params.setdefault(name, {}).update(kwargs)

    def get_toolbar_item_kwargs(self, name):
        return self.stored_toolbar_items_params.get(name)

    def store_filter_kwargs(self, name, **kwargs):
        self.stored_filters_params.setdefault(name, {}).update(kwargs)

    def store_filter_html_attr(self, name, filter_attr, html_attr, value):
        filter_params = self.stored_filters_params.get(name)
        if filter_params is None:
            param = {filter_attr: HTMLAttributes({html_attr: value})}
            self.store_filter_kwargs(name, **param)
        else:
            html_params = filter_params.setdefault(html_attr, HTMLAttributes())
            html_params.add(html_attr, value)

    def get_filter_kwargs(self, name):
        return self.stored_filters_params.get(name)

    def store_form_kwargs(self, name, **kwargs):
        self.stored_form_params.setdefault(name, {}).update(kwargs)

    def store_form_html_attr(self, name, form_attr, html_attr, value):
        form_params = self.stored_form_params.get(name)
        if form_params is None:
            param = {form_attr: HTMLAttributes({html_attr: value})}
            self.store_form_kwargs(name, **param)
        else:
            html_params = form_params.setdefault(html_attr, HTMLAttributes())
            html_params.add(html_attr, value)

    def get_form_kwargs(self, name):
        return self.stored_form_params.get(name)


class ListingVariations(ListingBase):
    variations_classes = ()
    variation_default = 0
    data = None
    listing = None
    id = None
    model = None
    suffix = None

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        if data is not None:
            self.init(data, **kwargs)
        self.init_kwargs = kwargs

    def get_model(self):
        if self.model:
            return self.model
        if self.listing and self.listing.columns:
            return self.listing.columns.get_model()
        return None

    def set_kwargs(self, **kwargs):
        if self.listing:
            self.listing.set_kwargs(**kwargs)
        else:
            # postpone to when listing will be created
            self.store_kwargs(**kwargs)

    def set_attr(self, attr, value):
        if self.listing:
            self.listing.set_attr(attr, value)
        else:
            # postpone to when listing will be created
            self.store_kwargs(**{attr: value})

    def is_initialized(self):
        if self.listing:
            return self.listing.is_initialized()
        else:
            return False

    def init(self, data, **kwargs):
        self.data = data
        if self.listing:
            self.listing.init(data, **kwargs)
        else:
            # postpone to when listing will be created
            self.store_kwargs(**kwargs)

    def create_listing(self, context):
        if not self.listing:
            request = context.request
            if self.suffix is None:
                self.suffix = Listing.get_suffix(request, self)
            variation = request.GET.get("variation" + self.suffix)
            if variation and variation.isdigit():
                variation = int(variation)
                if variation >= len(self.variations_classes) or variation < 0:
                    variation = self.variation_default
            else:
                variation = self.variation_default

            cls = self.variations_classes[variation]
            listing = cls(**self.init_kwargs)
            listing.variation = variation
            listing.variations = self
            listing.suffix = self.suffix
            listing.parsed_url = urlsplit(request.get_full_path())
            if self.id:
                listing.id = self.id
            # Copy variations class attributes to listing instance
            for k, v in self.__class__.__dict__.items():
                if not k.startswith("_") and not getattr(listing, k, None):
                    setattr(listing, k, v)
            listing.transfert_params_from(self)
            listing.set_kwargs()
            listing.init(self.data)
            self.listing = listing

    def render_init(self, context):
        self.create_listing(context)
        self.listing.set_kwargs()
        self.listing.render_init(context)

    def render(self, context):
        self.create_listing(context)
        self.listing.set_kwargs()
        return self.listing.render(context)

    def get_url(self, context, **kwargs):
        self.create_listing(context)
        return self.listing.get_url(context, **kwargs)

    def have_to_refresh(self):
        if self.listing:
            return self.listing.have_to_refresh()
        return False

    def __getattr__(self, item):
        if item in LISTING_VARIATIONS_KEYS and self.listing:
            return getattr(self.listing, item)
        return super().__getattribute__(item)


class Listing(ListingBase):
    accept_ajax = False
    action = None
    action_button_cancel_label = pgettext_lazy("action button", "Cancel")
    action_button_edit_label = pgettext_lazy("action button", "Edit")
    action_button_update_label = pgettext_lazy("action button", "Update")
    action_button_upload_label = pgettext_lazy("action button", "Upload")
    action_col = None
    action_footer_template_name = ThemeTemplate("action_footer.html")
    action_header_template_name = ThemeTemplate("action_header.html")
    ajax_part = None
    allow_empty_first_page = True
    anchor_hash = None
    attrs = {"class": "table table-hover table-bordered table-striped table-sm"}
    can_edit = False
    can_select = False
    columns = None
    columns_headers = None
    data = None
    datetimepicker_date_format = "Y-m-d"
    datetimepicker_datetime_format = "Y-m-d H:i"
    datetimepicker_time_format = "H:i"
    div_template_name = ThemeTemplate("div_row.html")
    row_attrs = {}
    edit_on_demand = False
    editable = False
    editable_columns = set()
    editing = None
    editing_columns = None
    editing_row_pk = None
    editing_hidden_columns = None
    empty_table_msg = gettext_lazy("Nothing to display")
    empty_listing_template_name = ThemeTemplate("empty_listing.html")
    exclude_columns = None
    export = None
    filters = None
    footer_snippet = None
    footer_template_name = None
    form = None
    has_footer = False
    has_footer_action_buttons = True
    has_form = False
    has_header = True
    has_hidden_selection = False
    has_paginator = True
    has_toolbar = False
    has_upload = False
    id = None
    is_small_device_localized = False
    link_object_columns = None
    row_form_base_class = ListingBaseForm
    listing_form_base_class = ListingBaseForm
    listing_template_name = ThemeTemplate("listing.html")
    model = None
    name = "listing"
    onready_snippet = None
    orphans = 0
    page = 1
    pagination = True
    paginator = None
    paginator_class = Paginator
    per_page = LISTING_ROWS_PER_PAGE
    per_page_max = LISTING_ROWS_PER_PAGE_MAX
    posted_columns = None
    primary_key = "id"
    records_class = RecordManager
    record_label = None
    record_label_plural = None
    row_form_errors = None
    row_inner_div_tpl = None
    save_to_database = False
    select_columns = None
    selectable = False
    selected_columns = None
    selected_hidden_columns = None
    selecting = None
    selection_initial = None
    selection_key = "id"
    selection_menu_id = None
    selection_mode = "default"  # default, overlay, hover
    selection_multiple = False
    selection_overlay_template_name = ThemeTemplate("selection_overlay.html")
    selection_position = "hidden"  # left, right or hidden
    small_device_max_width = "767.98px"
    small_device_header_style = "font-weight: bold"
    sort = None
    sortable = True
    suffix = None
    toolbar = None
    toolbar_placement = "both"
    unsortable = True
    use_datetimepicker = False
    variation = None
    variations = None

    params_keys = set()  # keep it here in the class not in __init__()

    theme_class = ThemeAttribute("theme_class")
    theme_listing_class = ThemeAttribute("theme_listing_class")
    theme_action_button_class = ThemeAttribute("theme_action_button_class")
    theme_action_button_cancel_icon = ThemeAttribute("theme_action_button_cancel_icon")
    theme_action_button_edit_icon = ThemeAttribute("theme_action_button_edit_icon")
    theme_action_button_update_icon = ThemeAttribute("theme_action_button_update_icon")
    theme_action_button_upload_icon = ThemeAttribute("theme_action_button_upload_icon")
    theme_container_class = ThemeAttribute("theme_container_class")
    theme_sort_asc_icon = ThemeAttribute("theme_sort_asc_icon")
    theme_sort_desc_icon = ThemeAttribute("theme_sort_desc_icon")
    theme_sort_none_icon = ThemeAttribute("theme_sort_none_icon")
    theme_spinner_icon = ThemeAttribute("theme_spinner_icon")
    theme_sortable_class = ThemeAttribute("theme_sortable_class")
    theme_sorted_class = ThemeAttribute("theme_sorted_class")
    theme_sort_asc_class = ThemeAttribute("theme_sort_asc_class")
    theme_sort_desc_class = ThemeAttribute("theme_sort_desc_class")
    theme_button_class = ThemeAttribute("theme_button_class")
    theme_button_disabled_class = ThemeAttribute("theme_button_disabled_class")
    theme_button_active_class = ThemeAttribute("theme_button_active_class")
    theme_div_row_container_class = ThemeAttribute("theme_div_row_container_class")
    theme_row_class = ThemeAttribute("theme_row_class")
    theme_localized_small_device_styles_width = ThemeAttribute(
        "theme_localized_small_device_styles_width"
    )

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        self.request = None
        self.parsed_url = None
        self.page_context = None
        self.records = self.records_class(self)
        self.rows_context_list = []
        self.form_input_hiddens = []
        self.editing_hidden_form_fields = []
        self.editing_really_hidden_columns = set()
        self.can_edit_columns = []
        self.col_cell_renderers = {}
        init_dicts_from_class(self, ["global_context", "attrs", "row_attrs"])
        self._initialized = False
        self._render_initialized = False
        self._formset = None
        self._view = None
        self.form_params = {}
        self._have_to_refresh = False

        # listing initialisation must be in 2 steps because when a class is
        # passed to a template, it is automatically instanciated by Django
        # without any parameter.
        if isinstance(data, QuerySet) or data is not None:
            self.init(data, **kwargs)

    @classmethod
    def get_params_keys(cls):
        if not Listing.params_keys:
            Listing.params_keys = set(LISTING_PARAMS_KEYS)
            Listing.params_keys.update({"columns_%s" % k for k in COLUMNS_PARAMS_KEYS})
            Listing.params_keys.update(
                {"paginator_%s" % k for k in PAGINATOR_PARAMS_KEYS}
            )
            Listing.params_keys.update({"toolbar_%s" % k for k in TOOLBAR_PARAMS_KEYS})
            Listing.params_keys.update({"filters_%s" % k for k in FILTERS_PARAMS_KEYS})
            Listing.params_keys.update(
                {"form_%s" % k for k in LISTING_FORM_PARAMS_KEYS}
            )
        return Listing.params_keys

    def set_kwargs(self, **kwargs):
        self.store_kwargs(**kwargs)
        params_keys = self.get_params_keys()
        for k, v in self.stored_params.items():
            if k in params_keys or ("__" in k and not k.startswith("__")):
                setattr(self, k, v)
        self.stored_params = {}

    def have_to_refresh(self):
        return self._have_to_refresh

    def plan_refresh(self):
        self._have_to_refresh = True

    def add_onready_snippet(self, snippet):
        if not hasattr(self.request, "django_listing_onready_snippets"):
            self.request.django_listing_onready_snippets = []
        if snippet not in self.request.django_listing_onready_snippets:
            self.request.django_listing_onready_snippets.append(snippet)

    def add_header_snippet(self, snippet):
        if not hasattr(self.request, "django_listing_header_snippets"):
            self.request.django_listing_header_snippets = []
        if snippet not in self.request.django_listing_header_snippets:
            self.request.django_listing_header_snippets.append(snippet)

    def add_footer_dict_list(self, key, dct):
        if not hasattr(self.request, "django_listing_footer_dict_list"):
            self.request.django_listing_footer_dict_list = {}
        dict_list = self.request.django_listing_footer_dict_list.setdefault(key, [])
        dict_list.append(dct)

    def add_footer_snippet(self, snippet):
        if not hasattr(self.request, "django_listing_footer_snippets"):
            self.request.django_listing_footer_snippets = []
        if snippet not in self.request.django_listing_footer_snippets:
            self.request.django_listing_footer_snippets.append(snippet)

    def need_media_for(self, feature_name):
        if not hasattr(self.request, "need_media_for"):
            self.request.need_media_for = {}
        self.request.need_media_for[feature_name] = True

    def create_missing_columns(self):
        if self.columns is None:
            if isinstance(self.columns_headers, str):
                self.columns_headers = self.columns_headers.split(",")
            if self.model:
                self.columns = ModelColumns(
                    self.model,
                    listing=self,
                    link_object_columns=self.link_object_columns,
                )
            elif self.data and isinstance(self.data, collections.abc.Sequence):
                self.columns = SequenceColumns(
                    self.data, self.columns_headers, listing=self
                )
        if isinstance(self.columns, (ModelColumns, SequenceColumns)):
            self.columns.set_listing(self)
            self.columns.init()
        if not self.columns:
            raise InvalidListing(
                _("Please configure at least one column " "in your listing")
            )
        if self.selectable:
            if self.selection_position == "left":
                self.columns.insert(0, SelectionColumn(LISTING_SELECTION_CHECKBOX_NAME))
            elif self.selection_position == "right":
                self.columns.append(SelectionColumn(LISTING_SELECTION_CHECKBOX_NAME))

    def create_missing_toolbar_items(self):
        if self.toolbar is None:
            return
        if not isinstance(self, Toolbar):
            self.toolbar = Toolbar(self.toolbar)

    def create_missing_filters(self):
        if self.filters is None:
            return
        if isinstance(self.filters, str):
            # if filters attribute is a string, it means a layout was declared,
            # so we have to extract filters names
            form_layout = self.filters
            filters_name = list(
                map(
                    lambda s: s.split("|")[0].strip(),
                    sum(map(lambda s: s.split(","), form_layout.split(";")), []),
                )
            )
            self.filters = Filters(*filters_name)
            self.filters.form_layout = form_layout

    def get_model(self):
        if self.model:
            return self.model
        if self.columns:
            return self.columns.get_model()
        return None

    def is_empty(self):
        return not bool(self.data)

    def is_initialized(self):
        return self._initialized

    def is_render_initialized(self):
        return self._render_initialized

    def manage_page_context(self, context):
        if context:
            if not self.page_context:
                self.page_context = context
                self.request = context.request
                self.parsed_url = urlsplit(self.request.get_full_path())
                self.suffix = self.get_suffix(self.request, self)
                self.extract_params()
                if self.filters:
                    self.filters.extract_params()
            else:
                self.page_context = context

    def validate_parameters(self):
        if self.editable and self.accept_ajax:
            if self.row_form_errors is None:
                self.row_form_errors = []
            self.row_form_errors.append(_("[CANNOT_EDIT_IN_AJAX]"))
            self.editable = False

    def init(self, data, context=None, **kwargs):
        if not self.is_initialized():
            self.set_kwargs(**kwargs)
            self.validate_parameters()
            if data is None:
                data = self.model or self.columns.get_model()
            if isinstance(data, type) and issubclass(data, Model):
                self.model = data
                data = self.model.objects.all()
            elif isinstance(data, Model):
                self.model = type(data)
                data = self.model.objects.all()
            elif isinstance(data, QuerySet):
                self.model = data.model
            if self.record_label is None:
                if self.model:
                    self.record_label = self.model._meta.verbose_name
                else:
                    self.record_label = _("record")
            if self.record_label_plural is None:
                if self.model:
                    self.record_label_plural = self.model._meta.verbose_name_plural
                else:
                    self.record_label_plural = _("records")
            self.data = data
            self.create_missing_filters()
            if self.filters:
                self.filters = self.filters.bind_to_listing(self)
            if self.form:
                self.form = self.form.bind_to_listing(self)
            self.manage_page_context(context)
            self.create_missing_columns()
            self.create_missing_toolbar_items()
            self.has_toolbar = bool(self.toolbar)
            self.columns = self.columns.bind_to_listing(self)
            if self.toolbar:
                self.toolbar = self.toolbar.bind_to_listing(self)
            self.col_cell_renderers = {
                col: getattr(self, "render_{}".format(col.name), col.render_cell)
                for col in self.columns
            }
            self._initialized = True

    def datetimepicker_init(self):
        if self.use_datetimepicker:
            self.need_media_for("datetimepicker")
            self.add_footer_dict_list(
                "datetimepickers", dict(listing=self, div_id=self.id)
            )

    def dropzone_init(self):
        self.need_media_for("dropzone")
        dz_suffix = self.suffix[1:] if isinstance(self.suffix, str) else ""
        dz_camel_name = f"actionForm{dz_suffix}"
        self.add_footer_dict_list(
            "dropzones",
            dict(
                listing=self,
                dz_camel_name=dz_camel_name,
                options=settings.django_listing_settings.DROPZONE_PARAMS,
            ),
        )

    def global_context_init(self):
        self.global_context.update(settings.django_listing_settings.context)
        if self.request and (self.can_edit or self.has_upload):
            self.global_context["csrf_token"] = get_csrf_token(self.request)

    def render_init(self, context):
        if not self._render_initialized:
            self.manage_page_context(context)
            self.normalize_params()
            for col in self.columns:
                col.render_init()
            if isinstance(self.editable_columns, str):
                self.editable_columns = set(
                    map(str.strip, self.editable_columns.split(","))
                )
            if self.editing_hidden_columns is None:
                if self.model and self.primary_key in self.columns.names():
                    self.editing_hidden_columns = {self.primary_key}
                else:
                    self.editing_hidden_columns = set()
            if isinstance(self.editing_hidden_columns, str):
                self.editing_hidden_columns = set(
                    map(str.strip, self.editing_hidden_columns.split(","))
                )
            if self.editing is None:
                self.editing = True
            if self.editing_columns is None:
                self.editing_columns = "all"
            if isinstance(self.editing, str) and self.editing.lower() == "false":
                self.editing = False
            if isinstance(self.editing_columns, str):
                self.editing_columns = set(
                    map(str.strip, self.editing_columns.split(","))
                )
            self.columns.editing_init()
            self.can_edit = self.editable and self.editing
            if isinstance(self.selecting, str) and self.selecting.lower() == "false":
                self.selecting = False
            if self.selecting is None:
                self.selecting = True
            self.can_select = self.selectable and self.selecting
            self.has_hidden_selection = (
                self.selectable
                and self.selecting
                and self.selection_position == "hidden"
            )
            self.columns_sort_ascending = {}
            self.columns_sort_list = []
            if self.sort:
                if isinstance(self.sort, str):
                    sort_list = map(str.strip, self.sort.split(","))
                else:
                    sort_list = self.sort
                for col_name in sort_list:
                    ascending = True
                    if col_name.startswith("-"):
                        col_name = col_name[1:]
                        ascending = False
                    self.columns_sort_list.append(col_name)
                    self.columns_sort_ascending[col_name] = ascending
            if not isinstance(self.attrs, HTMLAttributes):
                self.attrs = HTMLAttributes(self.attrs)
            html_class = "listing-" + self.__class__.__name__.lower()
            self.attrs.add("class", {html_class, self.theme_listing_class})
            if self.variation is not None:
                self.attrs.add("class", "variation-{}".format(self.variation))
            if not self.id:
                self.id = "{}{}-id".format(html_class, self.suffix)
            self.css_id = self.id.replace("_", "-")
            if isinstance(self.suffix, str):
                self.css_suffix = self.suffix.replace("_", "-")
            if not isinstance(self.row_attrs, HTMLAttributes):
                self.row_attrs = HTMLAttributes(self.row_attrs)
            self.row_attrs.add(
                "class", {self.theme_div_row_container_class, self.theme_row_class}
            )
            self.selected_columns = self.columns.select(
                self.select_columns, self.exclude_columns
            )
            is_exporting = self.export_data()
            if is_exporting:
                return "Sending listing export file..."
            self.can_edit_columns = [c for c in self.selected_columns if c.can_edit]
            self.can_edit_columns_names = set(c.name for c in self.can_edit_columns)
            self.editing_really_hidden_columns = (
                self.editing_hidden_columns - self.can_edit_columns_names
            )
            self.selected_hidden_columns = self.columns.select(
                self.editing_really_hidden_columns
            )
            if self.can_edit:
                self.datetimepicker_init()
            if self.has_upload:
                self.dropzone_init()
            if self.can_edit or self.can_select or self.form or self.has_upload:
                self.add_form_input_hiddens(
                    listing_id=self.id, listing_suffix=self.suffix
                )
            if self.onready_snippet:
                self.add_onready_snippet(self.onready_snippet)
            if self.footer_snippet:
                self.add_footer_snippet(self.footer_snippet)
            if not isinstance(self.selection_initial, list):
                self.selection_initial = [self.selection_initial]
            self.selection_has_overlay = self.selection_mode in ["overlay", "hover"]
            self.global_context_init()
            self.records.compute_current_page_records()
            self._render_initialized = True

    def render(self, context):
        response = self.render_init(context)
        if response is not None:
            return response
        return self.render_template()

    def export_data(self):
        if self.export:
            export_format = self.export.upper()
            if export_format in EXPORT_FORMATS:
                use_col_name = export_format in EXPORT_FORMATS_USE_COL_NAME
                headers = self.exported_headers(use_col_name)
                if export_format == "DBF":
                    headers = list(map(lambda h: h[:10], headers))
                data = tablib.Dataset()
                data.headers = headers
                keep_original_type = export_format in EXPORT_FORMATS_KEEP_ORIGINAL_TYPE
                for row in self.exported_rows(keep_original_type):
                    data.append(row)
                self.request.export_data = data.export(export_format.lower())
                self.request.export_filename = "{}.{}".format(
                    self.name, self.export.lower()
                )
        return hasattr(self.request, "export_data")

    def django_listing_info(self):
        if hasattr(self, "request"):
            if self.request.GET.get("__django_listing_info__"):
                out = "<b><u>django-listing informations :</u></b><br>"
                import django_listing

                out += f"django-listing version : {django_listing.__version__}<br>"
                import django

                out += f"django version : {django.__version__}<br>"
                import tablib

                out += f"tablib version : {tablib.__version__}<br>"
                import sys

                out += f"Python version : {sys.version.split()[0]}<br>"
                return out

    def render_template(self):
        request_for_info = self.django_listing_info()
        if request_for_info:
            return request_for_info
        ctx = self.get_listing_context()
        template = loader.get_template(self.listing_template_name)
        out = template.render(ctx)
        return out

    def get_listing_css_id(self):
        return str(self.id).replace("_", "-")

    def get_listing_context(self):
        has_top_toolbar = self.has_toolbar and self.toolbar_placement in ["top", "both"]
        has_bottom_toolbar = self.has_toolbar and self.toolbar_placement in [
            "bottom",
            "both",
        ]
        listing_container_class = "{} {}".format(
            self.theme_container_class, self.theme_class
        )
        if self.accept_ajax:
            listing_container_class += " django-listing-ajax"
        if self.can_edit:
            listing_container_class += " django-listing-editing"
        if self.can_select:
            listing_container_class += " django-listing-selecting"
            if self.selection_multiple:
                listing_container_class += " selection_multiple"
            else:
                listing_container_class += " selection_unique"
            listing_container_class += " selection_position_{}".format(
                self.selection_position
            )
        if self.has_upload:
            listing_container_class += " has_upload"
        sel_css_class = LISTING_SELECTOR_CSS_CLASS if self.selection_has_overlay else ""
        hover_css_class = (
            LISTING_SELECTION_HOVER_CSS_CLASS if self.selection_mode == "hover" else ""
        )
        ctx = RenderContext(
            self.global_context,
            self.page_context.flatten(),
            nb_columns=len(self.selected_columns),
            listing=self,
            listing_container_class=listing_container_class,
            has_top_toolbar=has_top_toolbar,
            has_bottom_toolbar=has_bottom_toolbar,
            get=self.request.GET,
            overlay_selector_css_class=sel_css_class,
            hover_selection_css_class=hover_css_class,
        )
        if self.paginator:
            ctx.update(self.paginator.get_context())
        if self.toolbar:
            ctx.update(self.toolbar.get_context())
        return ctx

    def add_form_input_hiddens(self, **kwargs):
        for name, value in kwargs.items():
            self.form_input_hiddens.append((name, value))

    def add_edit_form_hidden_field(self, field_instance):
        self.editing_hidden_form_fields.append(field_instance)

    def aggregate(self, rec):
        for col in self.selected_columns:
            if col.aggregation:
                col.aggregation.aggregate(rec)

        if self.can_edit:
            for col in self.selected_hidden_columns:
                form = rec.get_form()
                if form:
                    self.add_edit_form_hidden_field(form[col.name])

    def div_rows(self):
        for rec in self.records.current_page():
            self.rows_context_list.append(rec)
            index = rec.get_index()
            attrs = self.get_row_attrs(rec)  # must be executed before creating the dict
            row = dict(
                attrs=attrs,
                index=index,
                index1=index + 1,
                selected=rec.is_selected(),
                rec=rec,
            )
            if self.has_hidden_selection:
                row.update(selection_value=rec.get(self.selection_key))
            self.aggregate(rec)
            yield row

    def rows(self):
        for rec in self.records.current_page():
            index = rec.get_index()
            attrs = self.get_row_attrs(rec)  # must be executed before creating the dict
            row = dict(
                attrs=attrs,
                ctx=self.get_row_context(rec),
                columns=self.get_rendered_cells(rec),
                index=index,
                index1=index + 1,
                selected=rec.is_selected(),
                rec=rec,
            )
            if self.has_hidden_selection:
                row.update(selection_value=rec.get(self.selection_key))
            self.aggregate(rec)
            yield row

    def exported_headers(self, use_col_name=True):
        if use_col_name:
            return [c.name for c in self.selected_columns]
        else:
            return [str(c.get_header_value()) for c in self.selected_columns]

    def exported_rows(self, keep_original_type=True):
        for rec in self.records.export():
            yield [
                c.get_cell_exported_value(rec, keep_original_type)
                for c in self.selected_columns
            ]

    def get_rendered_cells(self, rec):
        rendered_columns = []
        for col in self.selected_columns:
            rendered_col = dict(
                html=self.col_cell_renderers[col](rec),
                obj=col,
            )
            rendered_columns.append(rendered_col)
        return rendered_columns

    def header_columns(self):
        if self.has_header:
            rendered_columns = []
            for col in self.selected_columns:
                rendered_col = dict(
                    html=col.render_header(),
                    obj=col,
                )
                rendered_columns.append(rendered_col)
            return rendered_columns
        else:
            return []

    def get_localized_small_device_styles(self):
        styles = [
            ("#{listing_css_id} th:before {{" 'content:"{sort_msg}";' "}}").format(
                listing_css_id=self.get_listing_css_id(),
                sort_msg=_("Sort by:"),
                two_dots=_(":"),
            )
        ]
        for col in self.selected_columns:
            style = (
                "#{listing_css_id} td.col-{col_name}:before {{"
                'content:"{header}{two_dots} ";'
                "{sd_style};"
                "}}"
            ).format(
                listing_css_id=self.get_listing_css_id(),
                col_name=col.name,
                header=col.get_header_value(),
                two_dots=_(":"),
                sd_style=self.small_device_header_style,
            )
            styles.append(style)
        return styles

    def footer_columns(self):
        if self.has_footer:
            rendered_columns = []
            for col in self.selected_columns:
                rendered_col = dict(
                    html=col.render_footer(),
                    obj=col,
                )
                rendered_columns.append(rendered_col)
            return rendered_columns
        else:
            return []

    def get_url(self, context=None, without=None, anchor_hash=None, **kwargs):
        """Get listing url with some updated parameters if needed
        Note : Do not remove 'context=None' because needed by listing variations
        """
        querystring = QueryDict(self.parsed_url.query, mutable=True)
        for k, v in kwargs.items():
            if not isinstance(v, str):
                v = str(v)
            if k in LISTING_QUERY_STRING_KEYS:
                k += self.suffix
            querystring[k] = v
        del_keys = LISTING_NOT_PERSISTENT_QUERY_STRING_KEYS - set(kwargs.keys())
        if without:
            if isinstance(without, str):
                without = without.split(",")
            del_keys = del_keys | set(without)
        for k in del_keys:
            k += self.suffix
            if k in querystring:
                del querystring[k]
        fragment = anchor_hash or self.anchor_hash
        return urlunsplit(
            self.parsed_url._replace(query=querystring.urlencode(), fragment=fragment)
        )

    def get_hiddens(self, without=None):
        hiddens = QueryDict(self.parsed_url.query, mutable=True)
        if without:
            if isinstance(without, str):
                without = list(map(str.strip, without.split(",")))
            without = list(map(lambda s: s.strip() + self.suffix, without))
            if isinstance(without, (list, tuple)):
                for k in without:
                    if k in hiddens:
                        del hiddens[k]
        return hiddens

    def get_hiddens_html(self, without=None):
        hiddens = self.get_hiddens(without)
        out = [
            '<input type="hidden" name="{name}" value="{value}">'.format(
                name=name, value=value
            )
            for name, value in hiddens.items()
        ]
        return "".join(out)

    @classmethod
    def get_suffix_request_data(cls, request):
        if not hasattr(request, LISTING_SUFFIX_REQUEST_DATA_FIELD):
            setattr(
                request,
                LISTING_SUFFIX_REQUEST_DATA_FIELD,
                {
                    "listings_suffixes": {},
                    "counter": 0,
                },
            )
        return getattr(request, LISTING_SUFFIX_REQUEST_DATA_FIELD)

    @classmethod
    def get_suffix(cls, request, listing):
        listing = getattr(listing, "variations", None) or listing
        data = cls.get_suffix_request_data(request)
        suffix = data["listings_suffixes"].get(listing)
        if suffix is None:
            counter = data["counter"]
            suffixes = data["listings_suffixes"].values()
            while True:
                if counter == 0:
                    suffix = ""
                else:
                    suffix = LISTING_SUFFIX_PATTERN.format(counter)
                if suffix not in suffixes:
                    data["listings_suffixes"][listing] = suffix
                    break
                counter += 1
            data["counter"] = counter + 1
        return suffix

    @classmethod
    def set_suffix(cls, request, listing, suffix):
        listing = getattr(listing, "variations", None) or listing
        data = cls.get_suffix_request_data(request)
        data["listings_suffixes"][listing] = suffix
        listing.suffix = suffix

    def extract_params(self):
        get_dict = self.request.GET
        post_dict = self.request.POST
        for k in LISTING_QUERY_STRING_KEYS:
            qs_key = k + self.suffix
            v = None
            if qs_key in post_dict:
                v = post_dict.get(qs_key)
            elif qs_key in get_dict:
                v = get_dict.get(qs_key)
            if v is not None and k in LISTING_QUERY_STRING_INT_KEYS:
                try:
                    v = int(v)
                except ValueError:
                    pass
            if v is not None:
                setattr(self, k, v)

    def normalize_params(self):
        if self.per_page < -1 or self.per_page == 0:
            self.per_page = self.__class__.per_page

    def get_row_attrs(self, rec):
        attrs = HTMLAttributes(self.row_attrs)  # create a copy
        if rec.pk:
            attrs.add("data-pk", str(rec.pk))
        attrs.add("class", "odd" if rec.get_index() % 2 else "even")
        if self.can_select:
            if not self.selection_has_overlay:
                attrs.add("class", LISTING_SELECTOR_CSS_CLASS)
            selection_value = rec.get(self.selection_key)
            if self.selection_initial and selection_value in self.selection_initial:
                attrs.add("class", "selected")
                rec._selected = True
        return attrs

    def get_row_context(self, rec):
        return {}

    def get_formset_initial_values(self):
        initial_values = [
            {
                c.name: c.get_cell_form_value(rec)
                for c in (self.can_edit_columns + self.selected_hidden_columns)
            }
            for rec in self.records.current_page()
            if not self.editing_row_pk or rec.pk == self.editing_row_pk
        ]
        return initial_values

    def get_formset(self):
        if not self._formset:
            post_data = None
            post_files = None
            if self.request.method == "POST":
                posted_listing_id = self.request.POST.get("listing_id", "")
                if posted_listing_id == self.id:
                    post_data = self.request.POST
                    post_files = self.request.FILES
            fields = {
                c.name: c.create_hidden_form_field()
                for c in self.selected_hidden_columns
            }
            fields.update(
                {c.name: c.create_form_field() for c in self.can_edit_columns}
            )
            form_class = type(
                "ListingRowForm{}".format(self.suffix),
                (self.row_form_base_class,),
                {"base_fields": fields},
            )
            formset_class = forms.formset_factory(form_class, extra=0)
            self._formset = formset_class(
                post_data,
                post_files,
                initial=self.get_formset_initial_values(),
                prefix="{}{}".format(LISTING_FORMSET_PREFIX, self.suffix),
            )
            for form in self._formset:
                form.listing = self
                form.form_name = "row_form"
        return self._formset

    def get_selected_rows(self):
        if self.request and self.request.POST:
            return self.request.POST.getlist(
                LISTING_SELECTION_INPUT_NAME_KEY + self.suffix
            )

    def set_view(self, view):
        self._view = view

    def get_view(self):
        return self._view


class DivListing(Listing):
    listing_template_name = ThemeTemplate("listing_div.html")
    theme_row_class = "row-container"
