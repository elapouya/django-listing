#
# Created : 2018-02-09
#
# @author: Eric Lapouyade
#

import copy
import datetime
import os
import re
from collections import OrderedDict
from types import GeneratorType

from django import forms
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import ForeignKey
from django.forms import widgets
from django.template.defaultfilters import filesizeformat
from django.utils import formats
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_str
from django.utils.html import conditional_escape, strip_tags, escape
from django.utils.safestring import mark_safe, SafeData
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _

from .aggregations import Aggregation, AggregationMeta
from .context import RenderContext
from .exceptions import *
from .html_attributes import HTMLAttributes
from .record import cache_in_record
from .theme_config import ThemeAttribute
from .utils import init_dicts_from_class


__all__ = [
    "AutoCompleteColumn",
    "AvgColumn",
    "BooleanColumn",
    "ButtonColumn",
    "ButtonLinkColumn",
    "CheckboxColumn",
    "ChoiceColumn",
    "Column",
    "Columns",
    "COLUMNS_FORM_FIELD_KEYS",
    "COLUMNS_PARAMS_KEYS",
    "DateColumn",
    "DateTimeColumn",
    "FileSizeColumn",
    "FloatColumn",
    "DecimalColumn",
    "ForeignKeyColumn",
    "InputColumn",
    "JsonDateTimeColumn",
    "LinkColumn",
    "LinkObjectColumn",
    "ListingMethodRef",
    "ModelMethodRef",
    "RelatedModelMethodRef",
    "ManyColumn",
    "MaxColumn",
    "MinColumn",
    "ModelColumns",
    "MultipleChoiceColumn",
    "SelectColumn",
    "SequenceColumns",
    "TimeColumn",
    "TotalColumn",
]

COLUMNS_PARAMS_KEYS = {
    "aggregation",
    "ascending_by_default",
    "cell_attrs",
    "cell_edit_tpl",
    "cell_tpl",
    "cell_value",
    "cell_with_filter_link",
    "cell_with_filter_name",
    "cell_with_filter_tpl",
    "column_class",
    "column_instance",
    "data_key",
    "date_format",
    "datetime_format",
    "default_footer_value",
    "default_value",
    "editable",
    "exportable",
    "exported_header",
    "float_format",
    "footer",
    "footer_attrs",
    "footer_tpl",
    "footer_value_tpl",
    "form_field",
    "form_field_class",
    "form_field_params",
    "form_field_widget_class",
    "form_field_widget_params",
    "form_field_serialize",
    "form_no_autofill",
    "has_cell_filter",
    "header",
    "header_attrs",
    "header_sortable_tpl",
    "header_tpl",
    "input_type",
    "is_safe_value",
    "label",
    "link_target",
    "model_field",
    "name",
    "no_choice_msg",
    "true_msg",
    "false_msg",
    "no_foreignkey_link",
    "sort_key",
    "sortable",
    "start",
    "theme_button_class",
    "theme_button_link_class",
    "theme_link_class",
    "theme_cell_class",
    "theme_cell_with_filter_icon",
    "theme_footer_class",
    "theme_form_checkbox_widget_class",
    "theme_form_radio_widget_class",
    "theme_form_select_widget_class",
    "theme_form_widget_class",
    "theme_header_class",
    "theme_header_icon",
    "time_format",
    "use_raw_value",
    "value_tpl",
    "widget_attrs",
}

COLUMNS_FORM_FIELD_KEYS = {
    "disabled",
    "empty_value",
    "error_messages",
    "help_text",
    "initial",
    "input_formats",
    "label",
    "label_suffix",
    "localize",
    "max_length",
    "max_value",
    "min_length",
    "min_value",
    "queryset",
    "required",
    "strip",
    "validators",
    "widget",
}


FORM_FIELD_BASE_KEYS = {
    "required",
    "widget",
    "label",
    "initial",
    "help_text",
    "error_messages",
    "show_hidden_initial",
    "validators",
    "localize",
    "disabled",
    "label_suffix",
    "format",
}

EXPORT_XLSX_ILLEGAL_CHARACTERS_RE = re.compile(r"[\000-\010]|[\013-\014]|[\016-\037]")


class ListingMethodRef:
    """Helper to reference a Listing method in column.cell_value instead of a lambda"""

    def __init__(self, method_name):
        self.method_name = method_name

    def __call__(self, listing, *args, **kwargs):
        method = getattr(listing, self.method_name)
        return method(*args, **kwargs)


class ModelMethodRef:
    """Helper to reference a Model method in column.cell_value instead of a lambda"""

    def __init__(self, method_name, *args, **kwargs):
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs

    def __call__(self, rec):
        obj = rec.get_object()
        method = getattr(obj, self.method_name)
        return method(*self.args, **self.kwargs)


class RelatedModelMethodRef:
    """Helper to reference a Model method of a foreign object"""

    def __init__(self, method_name, default=None, *args, **kwargs):
        self.method_name = method_name
        self.default = default
        self.args = args
        self.kwargs = kwargs

    def __call__(self, col, rec):
        obj = rec.get_object()
        if isinstance(obj, dict):
            related_obj = obj.get(col.model_field.name)
        else:
            related_obj = getattr(obj, col.model_field.name, None)
        if related_obj is None:
            return self.default
        method = getattr(related_obj, self.method_name)
        return method(*self.args, **self.kwargs)


class Columns(list):
    def __init__(self, *cols, params=None):
        if params is None:
            params = {}
        self._params = params
        if cols:
            if isinstance(cols[0], (list, tuple)):
                cols = cols[0]
            elif isinstance(cols[0], GeneratorType):
                cols = list(cols[0])
        self.name2col = {c.init_args[0]: c for c in cols if c.init_args}
        super().__init__(cols)

    def get(self, name, default=None):
        return self.name2col.get(name, default)

    def exists(self, name):
        return name in self.name2col

    def get_model(self):
        return None

    def get_params(self):
        return self._params

    def names(self):
        return [c.name for c in self]

    def select_exported(self, exported_cols_name):
        cols = None
        if isinstance(exported_cols_name, str):
            exported_cols_name = list(map(str.strip, exported_cols_name.split(",")))
        if exported_cols_name:
            cols = [self.name2col[c] for c in exported_cols_name]
        return cols

    def select(self, select_cols_name=None, exclude_cols_name=None):
        if isinstance(select_cols_name, str):
            select_cols_name = list(map(str.strip, select_cols_name.split(",")))
        if isinstance(exclude_cols_name, str):
            exclude_cols_name = list(map(str.strip, exclude_cols_name.split(",")))
        if select_cols_name is None:
            select_cols_name = self.names()
        exclude_cols_name = exclude_cols_name or []
        cols = []
        for col_name in select_cols_name:
            if isinstance(col_name, (tuple, list)):
                col_name, header = col_name
            elif ":" in col_name:
                col_name, header = col_name.split(":", maxsplit=1)
            else:
                header = None
            col_name = col_name.replace(".", "__")
            if col_name not in exclude_cols_name and col_name in self.name2col:
                col = self.get(col_name.strip())
                if col:
                    if header:
                        col.header = header
                    cols.append(col)
        return cols

    def bind_to_listing(self, listing):
        cols = Columns(params=self._params)
        for i, col in enumerate(self):
            # check col is a Column instance
            if not isinstance(col, Column):
                raise InvalidColumn(
                    gettext(
                        "column {col_id} of listing {listing} is not "
                        "a Column instance (class = {colclass})"
                    ).format(
                        col_id=i,
                        listing=listing.__class__.__name__,
                        colclass=col.__class__.__name__,
                    )
                )
            # ensure there is one column instance per listing
            if not col.listing:
                col = copy.deepcopy(col)
            col.bind_to_listing(listing)
            cols.append(col)

        # Auto-add foreign-key columns specified in select_columns
        select_cols_name = listing.select_columns or []
        if isinstance(select_cols_name, str):
            select_cols_name = list(map(str.strip, select_cols_name.split(",")))
        for col_name in select_cols_name:
            if isinstance(col_name, (tuple, list)):
                col_name = col_name[0]
            else:
                col_name = re.sub(":.*$", "", col_name)
            if "." in col_name:
                col_name = col_name.replace(".", "__")
                data_key = col_name.replace("__", ".")
                col = Column(col_name, data_key=data_key)
                col.bind_to_listing(listing)
                cols.append(col)

        cols.name2col = {c.name: c for c in cols if isinstance(c, Column)}
        cols.listing = listing
        return cols

    def editing_init(self):
        for col in self:
            col.editing_init()


class ModelColumns(Columns):
    def __init__(
        self,
        model,
        *cols,
        params=None,
        listing=None,
        link_object_columns=None,
        **kwargs,
    ):
        self.model = model
        self.cols = cols
        self.params = params
        self.listing = listing
        self.link_object_columns = link_object_columns
        self.kwargs = kwargs

    def set_listing(self, listing):
        self.listing = listing

    def init(self):
        if self.params is None:
            self.params = {}
        if not self.link_object_columns:
            self.link_object_columns = self.listing.link_object_columns or ""
        if isinstance(self.link_object_columns, str):
            self.link_object_columns = set(
                map(str.strip, self.link_object_columns.split(","))
            )

        model_cols = []
        # when not yet initialized, column name is in init_args[0]
        name2col = OrderedDict((c.name or c.init_args[0], c) for c in self.cols)
        select_columns = []
        if self.listing:
            if isinstance(self.listing.select_columns, str):
                select_columns = list(
                    map(str.strip, self.listing.select_columns.split(","))
                )
            else:
                select_columns = self.listing.select_columns or []

        for f in self.model._meta.get_fields():
            if f.name in select_columns or not isinstance(
                f, (models.ManyToManyRel, models.ManyToOneRel)
            ):
                if not hasattr(self.listing, f"{f.name}__header"):
                    if getattr(f, "related_model", None):
                        header = getattr(f, "verbose_name", None)
                        if not header:
                            header = f.related_model._meta.verbose_name
                    else:
                        header = getattr(f, "verbose_name", f.name.capitalize())
                else:
                    header = getattr(self.listing, f"{f.name}__header")
                col_class = getattr(self.listing, f"{f.name}__column_class", None)
                if col_class and not issubclass(col_class, Column):
                    raise InvalidColumn(
                        f"{f.name}__override_class must be a class derived from "
                        f"Column class"
                    )
                col_instance = getattr(self.listing, f"{f.name}__column_instance", None)
                if col_instance and not isinstance(col_instance, Column):
                    raise InvalidColumn(
                        f"{f.name}__override_instance must be an instance of Column "
                        f"class or a derived class"
                    )
                if f.name in name2col:
                    col = name2col.pop(f.name)
                    col.header = header
                    model_cols.append(col)
                else:
                    if col_instance:
                        col_instance.header = header
                        col_instance.model_field = f
                        model_cols.append(col_instance)
                    elif col_class:
                        model_cols.append(
                            col_class(
                                f.name, model_field=f, header=header, **self.kwargs
                            )
                        )
                    elif f.name in self.link_object_columns:
                        model_cols.append(
                            LinkObjectColumn(
                                f.name, model_field=f, header=header, **self.kwargs
                            )
                        )
                    else:
                        model_cols.append(
                            self.create_column(f, header=header, **self.kwargs)
                        )

        super().__init__(*(model_cols + list(name2col.values())))
        if self.listing:
            for col in self:
                col.set_listing(self.listing)
        self._model = self.model
        self._params = self.params

    @classmethod
    def create_column_name(cls, listing, name, **kwargs):
        model = listing.model
        if model:
            model_field = model._meta.get_field(name)
            if not model_field:
                return None
            if not hasattr(listing, f"{model_field.name}__header"):
                header = getattr(model_field, "verbose_name", model_field.name)
            else:
                header = getattr(listing, f"{model_field.name}__header")
            col = cls.create_column(model_field, header=header, **kwargs)
            col.bind_to_listing(listing)
            return col

    def get_model(self):
        return self._model

    @classmethod
    def create_column(cls, field, **kwargs):
        field_name = field.name
        for col_class in ColumnMeta.get_column_classes():
            if col_class is not Column:
                col = col_class.from_model_field(field, **kwargs)
                if col:
                    return col
        return Column(field_name, model_field=field, **kwargs)


class SequenceColumns(Columns):
    def __init__(self, seq, columns_headers=None, params=None, listing=None, **kwargs):
        self.seq = seq
        self.columns_headers = columns_headers
        self.params = params
        self.listing = listing
        self.kwargs = kwargs

    def set_listing(self, listing):
        self.listing = listing

    def init(self):
        if self.params is None:
            self.params = {}
        first_row = self.seq[0]
        if not isinstance(first_row, (dict, list, tuple)):
            for i, v in enumerate(self.seq):
                self.seq[i] = [self.seq[i]]
            first_row = self.seq[0]
        cols = []
        if isinstance(first_row, dict):
            if not isinstance(self.columns_headers, dict):
                self.columns_headers = {}
            for k, v in first_row.items():
                header = self.columns_headers.get(k)
                cols.append(self.create_column(v, k, header=header, **self.kwargs))
        elif isinstance(first_row, (list, tuple)):
            if not isinstance(self.columns_headers, (list, tuple)):
                self.columns_headers = ()
            for i, v in enumerate(first_row):
                if i < len(self.columns_headers) and self.columns_headers[i]:
                    header = self.columns_headers[i]
                else:
                    header = "Column{}".format(i + 1)
                cols.append(
                    self.create_column(v, header=header, data_key=i, **self.kwargs)
                )
        super().__init__(*cols)
        if self.listing:
            for col in self:
                col.set_listing(self.listing)
        self._params = self.params

    @classmethod
    def create_column(cls, value, name=None, header=None, data_key=None, **kwargs):
        if isinstance(value, datetime.datetime):
            return DateTimeColumn(name, header=header, data_key=data_key, **kwargs)
        elif isinstance(value, datetime.date):
            return DateColumn(name, header=header, data_key=data_key, **kwargs)
        return Column(name, header=header, data_key=data_key, **kwargs)


class ColumnMeta(type):
    column_classes = []

    def __new__(mcs, name, bases, attrs):
        cls = super(ColumnMeta, mcs).__new__(mcs, name, bases, attrs)
        ColumnMeta.column_classes.append((cls, cls.from_model_field_order))
        params_keys = cls.params_keys
        if isinstance(params_keys, str):
            params_keys = set(map(str.strip, params_keys.split(",")))
        COLUMNS_PARAMS_KEYS.update(params_keys)
        COLUMNS_PARAMS_KEYS.discard("")
        form_field_keys = cls.form_field_keys
        if form_field_keys:
            if isinstance(form_field_keys, str):
                form_field_keys = set(map(str.strip, form_field_keys.split(",")))
            COLUMNS_FORM_FIELD_KEYS.update(form_field_keys)
            COLUMNS_FORM_FIELD_KEYS.discard("")
            COLUMNS_PARAMS_KEYS.update(COLUMNS_FORM_FIELD_KEYS)
        return cls

    @classmethod
    def get_column_classes(cls):
        return [t[0] for t in sorted(cls.column_classes, key=lambda x: x[1])]


class Column(metaclass=ColumnMeta):
    aggregation = None
    ascending_by_default = True
    can_edit = False
    cell_tpl = None
    cell_edit_tpl = None
    cell_value = None
    cell_with_filter_link = None
    cell_with_filter_name = None
    cell_with_filter_tpl = (
        '<td{attrs}><span class="cell-with-filter">'
        '<span class="cell-value">%s</span>'
        '<a href="{filter_link}" '
        'class="cell-filter {col.theme_cell_with_filter_icon}">'
        "</a></span></td>"
    )
    data_key = None
    default_footer_value = ""
    default_value = "-"
    editable = None
    editing = False
    exportable = True
    exported_header = None
    footer = None
    footer_tpl = None
    footer_value_tpl = None
    form_field = None
    form_field_params = None
    form_field_class = forms.CharField
    form_field_widget_class = None
    form_field_keys = None
    form_field_serialize = False
    from_model_field_classes = []
    from_model_field_order = 100
    form_no_autofill = False
    has_cell_filter = False
    header = None
    header_sortable_tpl = None
    header_tpl = None
    help_text = None
    input_type = None
    is_safe_value = False  # to avoid XSS attack
    listing = None
    link_target = None
    model_field = None
    model_form_field = None
    name = None
    no_choice_msg = _("Please choose...")
    true_msg = _("Yes")
    false_msg = _("No")
    params_keys = ""
    sort_key = None
    sortable = True
    use_raw_value = False
    value_tpl = "{value}"

    theme_header_class = ThemeAttribute("column_theme_header_class")
    theme_cell_class = ThemeAttribute("column_theme_cell_class")
    theme_footer_class = ThemeAttribute("column_theme_footer_class")
    theme_form_widget_class = ThemeAttribute("column_theme_form_widget_class")
    theme_form_select_widget_class = ThemeAttribute(
        "column_theme_form_select_widget_class"
    )
    theme_form_checkbox_widget_class = ThemeAttribute(
        "column_theme_form_checkbox_widget_class"
    )
    theme_form_radio_widget_class = ThemeAttribute(
        "column_theme_form_radio_widget_class"
    )
    theme_button_class = ThemeAttribute("column_theme_button_class")
    theme_button_link_class = ThemeAttribute("column_theme_button_link_class")
    theme_link_class = ThemeAttribute("column_theme_link_class")
    theme_cell_with_filter_icon = ThemeAttribute("column_theme_cell_with_filter_icon")

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        init_dicts_from_class(
            self,
            [
                "cell_attrs",
                "header_attrs",
                "footer_attrs",
                "widget_attrs",
                "form_field_widget_params",
            ],
        )

    def bind_to_listing(self, listing):
        self.init(listing, *self.init_args, **self.init_kwargs)

    def set_listing(self, listing):
        self.listing = listing

    def init(self, listing, name=None, **kwargs):
        self.set_listing(listing)
        header = kwargs.get("header")
        if name:
            self.name = re.sub(r"\W", "", name)
        if self.name is None:
            if header:
                self.name = re.sub(r"\W", "", header.strip().replace(" ", "_").lower())
            else:
                self.name = "noname"
        self.set_kwargs(**kwargs)
        self.apply_template_kwargs()
        if self.data_key is None:
            self.data_key = self.name
        if listing.model:
            try:
                if "." in self.data_key:
                    attr, foreign_attr = self.data_key.split(".", maxsplit=1)
                    f = listing.model._meta.get_field(attr)
                    f = f.related_model._meta.get_field(foreign_attr)
                else:
                    f = listing.model._meta.get_field(self.data_key)
                self.model_field = f
                if hasattr(f, "formfield"):
                    self.model_form_field = f.formfield(validators=f.validators)
            except FieldDoesNotExist:
                pass
        if self.sort_key is None:
            if isinstance(self.data_key, str):
                self.sort_key = self.data_key.replace(".", "__")
            else:
                self.sort_key = 0
        if isinstance(self.aggregation, str):
            self.aggregation = AggregationMeta.get_instance(self.aggregation, self)
        if isinstance(self.theme_header_class, str):
            self.theme_header_class = set(self.theme_header_class.split())
        if isinstance(self.theme_cell_class, str):
            self.theme_cell_class = set(self.theme_cell_class.split())
        if isinstance(self.theme_footer_class, str):
            self.theme_footer_class = set(self.theme_footer_class.split())
        if isinstance(self.theme_form_widget_class, str):
            self.theme_form_widget_class = set(self.theme_form_widget_class.split())
        if isinstance(self.theme_form_select_widget_class, str):
            self.theme_form_select_widget_class = set(
                self.theme_form_select_widget_class.split()
            )
        if isinstance(self.theme_form_checkbox_widget_class, str):
            self.theme_form_checkbox_widget_class = set(
                self.theme_form_checkbox_widget_class.split()
            )
        if isinstance(self.theme_form_radio_widget_class, str):
            self.theme_form_radio_widget_class = set(
                self.theme_form_radio_widget_class.split()
            )
        if isinstance(self.theme_button_class, str):
            self.theme_button_class = set(self.theme_button_class.split())

    def render_init(self):
        pass

    def render_init_context(self, context):
        pass

    def editing_init(self):
        # editable attribute can be set via 'editable_columns'
        # only if not already set in the final column class
        if (
            self.editable is None
            and self.listing.editable_columns is not None
            and {"all", self.name} & self.listing.editable_columns
        ):
            self.editable = True
        if (
            self.listing.editing_columns is not None
            and {"all", self.name} & self.listing.editing_columns
        ):
            self.editing = True
        self.can_edit = (
            self.editable
            and self.editing
            and self.listing.editable
            and self.listing.editing
        )

    def set_kwargs(self, **kwargs):
        # if parameters given in columns : apply them
        for k, v in self.listing.columns.get_params().get(self.name, {}).items():
            if k in COLUMNS_PARAMS_KEYS:
                setattr(self, k, v)
        for k in COLUMNS_PARAMS_KEYS | COLUMNS_FORM_FIELD_KEYS:
            listing_key = "columns_{}".format(k)
            if hasattr(self.listing, listing_key):
                setattr(self, k, getattr(self.listing, listing_key))
        # col__param has higher priority than columns_param,
        # so getting col__params AFTER columns_params
        for k, v in kwargs.items():
            if k in COLUMNS_PARAMS_KEYS:
                setattr(self, k, v)
        # DO NOT swap with above for-loop, otherwise <col>__choices won't work
        # See showcase BoolChoicesImgColumnsListing "gender" column
        for k in dir(self.listing):
            start_key = f"{self.name}__"
            if k.startswith(start_key):
                v = getattr(self.listing, k)
                setattr(self, k[len(start_key) :], v)

    def apply_template_kwargs(self):
        kwargs = self.listing.get_column_kwargs(self.name)
        if kwargs:
            for k, v in kwargs.items():
                if k in COLUMNS_PARAMS_KEYS:
                    if isinstance(v, dict):
                        prev_value = getattr(self, k, None)
                        if isinstance(prev_value, dict):
                            prev_value.update(v)
                            continue
                    setattr(self, k, v)

    @classmethod
    def from_model_field(cls, field, **kwargs):
        if field.__class__ in cls.from_model_field_classes:
            return cls(field.name, model_field=field, **kwargs)

    def get_cell_attrs(self, rec, ctx, value):
        cell_attrs = self.cell_attrs
        if callable(cell_attrs):
            cell_attrs = cell_attrs(rec, ctx, value)
        attrs = HTMLAttributes(cell_attrs)
        attrs.add(
            "class",
            {
                "col-" + self.name,
                "type-" + type(value).__name__,
                "cls-" + self.__class__.__name__.lower(),
            }
            | self.theme_cell_class,
        )
        return attrs

    def get_cell_filter_link(self, rec, ctx, value):
        if callable(self.cell_with_filter_link):
            return self.cell_with_filter_link(self, rec, ctx, value)
        listing = self.listing
        filters = listing.filters
        if filters:
            filter_name = self.cell_with_filter_name or self.name
            filter_obj = filters.get(filter_name)
            if filter_obj:
                rec_val = rec.get(filter_name)
                rec_val = getattr(rec_val, "pk", rec_val)  # case it is a model object
                return listing.get_url(**{filter_obj.input_name: rec_val})
        return None

    def get_default_value(self, rec):
        return self.default_value

    @cache_in_record
    def get_cell_value(self, rec):
        if isinstance(self.cell_value, RelatedModelMethodRef):
            value = self.cell_value(self, rec)
        elif isinstance(self.cell_value, ModelMethodRef):
            value = self.cell_value(rec)
        elif isinstance(self.cell_value, ListingMethodRef):
            value = self.cell_value(self.listing, self, rec)
        elif callable(self.cell_value):
            value = self.cell_value(self, rec)
        else:
            value = rec.get(self.data_key)
            if value is None:
                value = self.get_default_value(rec)
        if hasattr(self, "choices") and not self.use_raw_value:
            value = self.choices.get(value, value)
        return value

    def get_cell_form_value(self, rec):
        value = rec.get(self.data_key)
        return value

    def get_cell_exported_value(self, rec, keep_original_type=True):
        val = self.get_cell_value(rec)
        if isinstance(val, str):
            val = strip_tags(val)
            if self.listing.export == "XLSX":
                val = EXPORT_XLSX_ILLEGAL_CHARACTERS_RE.sub("?", val)
        if not isinstance(
            val, (int, float, datetime.datetime, datetime.date, datetime.time, bool)
        ):
            return force_str(val)
        return val

    def render_form_field(self, rec):
        """Render a cell edit field when a listing is being edited"""

        # get the django form field (a formset form is attached to each record)
        # you get an instance of forms.CharField, forms.DateField etc...
        form_field = rec.get_form()[self.name]
        errors = form_field.errors
        if errors:
            html = (
                '<div class="form-field errors"><span class='
                '"listing-icon-attention"></span>{errors}{form_field}</div>'
            ).format(errors=errors, form_field=form_field)
        else:
            html = ('<div class="form-field">{form_field}</div>').format(
                form_field=form_field
            )
        return html

    def get_cell_context(self, rec, value):
        if isinstance(value, str):
            value = conditional_escape(value)
        ctx = RenderContext(
            self.listing.global_context,
            rec.get_format_ctx(),
            value,  # if value is a dict it will be merged (see RenderContext)
            value=value,  # if value is not a dict it will have the key 'value' in the context
            rec=rec,
            listing=self.listing,
            col=self,
        )
        # if self.has_cell_filter:
        #     ctx["filter_link"] = self.get_cell_filter_link(rec, ctx, value)
        return ctx

    def get_edit_value_tpl(self, rec, ctx, value):
        return self.render_form_field(rec)

    def get_value_tpl(self, rec, ctx, value):
        value_tpl = self.value_tpl
        if callable(value_tpl):
            value_tpl = value_tpl(rec, ctx, value)
        return value_tpl

    def get_cell_template(self, rec, ctx, value):
        if self.can_edit and rec.get_form() is not None:
            value_tpl = self.get_edit_value_tpl(rec, ctx, value)
            cell_tpl = self.cell_edit_tpl or self.cell_tpl
        else:
            if self.has_cell_filter and ctx.get("filter_link"):
                cell_tpl = self.cell_with_filter_tpl
            else:
                cell_tpl = self.cell_tpl
            value_tpl = self.get_value_tpl(rec, ctx, value)
        tpl = cell_tpl or "<td{attrs}>%s</td>"
        return tpl % value_tpl

    def render_cell(self, rec):
        value = self.get_cell_value(rec)
        ctx = self.get_cell_context(rec, value)
        ctx.attrs = self.get_cell_attrs(rec, ctx, value)
        if self.has_cell_filter:
            ctx.filter_link = self.get_cell_filter_link(rec, ctx, value)
        tpl = self.get_cell_template(rec, ctx, value)
        try:
            return tpl.format(**ctx)
        except (ValueError, AttributeError, IndexError) as e:
            return '<td class="render-error">{}</td>'.format(e)

    def get_header_attrs(self, ctx):
        header_attrs = self.header_attrs
        if callable(header_attrs):
            header_attrs = header_attrs(ctx)
        attrs = HTMLAttributes(header_attrs)
        if self.sortable and self.listing.sortable:
            attrs.add("class", self.listing.theme_sortable_class)
            asc = self.listing.columns_sort_ascending.get(self.name)
            if asc is not None:
                attrs.add("class", self.listing.theme_sorted_class)
                attrs.add(
                    "class",
                    self.listing.theme_sort_asc_class
                    if asc
                    else self.listing.theme_sort_desc_class,
                )
        else:
            attrs.add("class", "not-sortable")
        attrs.add("class", {"col-" + self.name} | self.theme_header_class)
        return attrs

    def get_exported_header_value(self):
        if self.exported_header is not None:
            return self.exported_header
        return self.get_header_value()

    def get_header_value(self):
        if self.header:
            if callable(self.header):
                # call to lambda function with column and listing as arguments
                header_value = self.header(self, self.listing)
            else:
                header_value = self.header
        else:
            header_value = self.name.replace("_", " ").title()
        return header_value

    def get_header_context(self):
        sort_url = None
        icon = None
        if self.sortable and self.listing.sortable:
            actual_ascending = self.listing.columns_sort_ascending.get(self.name)
            ascending = (
                not self.ascending_by_default
                if actual_ascending is None
                else actual_ascending
            )
            sort_param = "{}{}".format("-" if ascending else "", self.name)
            if (
                actual_ascending is not None
                and actual_ascending != self.ascending_by_default
                and self.listing.unsortable
            ):
                sort_url = self.listing.get_url(without="sort")
            else:
                sort_url = self.listing.get_url(sort=sort_param)
            asc = self.listing.columns_sort_ascending.get(self.name)
            if asc is None:
                icon = self.listing.theme_sort_none_icon
            elif asc:
                icon = self.listing.theme_sort_asc_icon
            else:
                icon = self.listing.theme_sort_desc_icon
            if icon:
                icon = " " + icon
        value = self.get_header_value()
        if isinstance(value, str):
            value = conditional_escape(value)
        return RenderContext(
            self.listing.global_context,
            value,  # if value is a dict it will be merged (see RenderContext)
            value=value,  # if value is not a dict it will have the key 'value' in the context
            sort_url=sort_url,
            icon=icon,
            listing=self.listing,
            col=self,
        )

    def get_header_template(self, ctx):
        if ctx.sort_url:
            return self.header_sortable_tpl or (
                '<th{attrs}><a class="listing-nav" href="{sort_url}">{value}'
                '<span class="sorting{icon}"></span></a></th>'
            )
        else:
            return self.header_tpl or "<th{attrs}>{value}</th>"

    def render_header(self):
        ctx = self.get_header_context()
        ctx.attrs = self.get_header_attrs(ctx)
        tpl = self.get_header_template(ctx)
        return tpl.format(**ctx)

    def get_footer_attrs(self, ctx, value):
        footer_attrs = self.footer_attrs
        if callable(footer_attrs):
            footer_attrs = footer_attrs(ctx)
        attrs = HTMLAttributes(footer_attrs)
        attrs.add(
            "class",
            {
                "col-" + self.name,
                "type-" + type(value).__name__,
                "cls-" + self.__class__.__name__.lower(),
            }
            | self.theme_footer_class,
        )
        return attrs

    def get_footer_value(self):
        if callable(self.footer):
            # call to lambda function with column and listing as arguments
            footer_value = self.footer(self, self.listing)
        else:
            footer_value = self.footer
        if footer_value is None:
            return self.default_footer_value
        return footer_value

    def get_footer_context(self, value):
        if isinstance(value, str):
            value = conditional_escape(value)
        return RenderContext(
            self.listing.global_context,
            value,  # if value is a dict it will be merged (see RenderContext)
            value=value,  # if value is not a dict it will have the key 'value' in the context
            listing=self.listing,
            col=self,
        )

    def get_footer_value_tpl(self, ctx, value):
        footer_value_tpl = self.footer_value_tpl or "{value}"
        if callable(footer_value_tpl):
            footer_value_tpl = footer_value_tpl(ctx, value)
        return footer_value_tpl

    def get_footer_template(self, ctx, value):
        return self.footer_tpl or "<td{attrs}>%s</td>" % self.get_footer_value_tpl(
            ctx, value
        )

    def render_footer(self):
        if isinstance(self.aggregation, Aggregation):
            return self.aggregation.render_footer()
        value = self.get_footer_value()
        ctx = self.get_footer_context(value)
        ctx.attrs = self.get_footer_attrs(ctx, value)
        tpl = self.get_footer_template(ctx, value)
        try:
            return tpl.format(**ctx)
        except (ValueError, AttributeError, IndexError) as e:
            return '<td class="render-error">{}</td>'.format(e)

    def get_form_field_params(
        self, force_select=False, force_not_required=False, **kwargs
    ):
        # Get form field params from the listing first,
        # if not available use model informations
        if self.form_field_params:
            params = copy.deepcopy(self.form_field_params)
        else:
            params = {}
        for p in COLUMNS_FORM_FIELD_KEYS:
            if p != "widget":
                if getattr(self, p, None) is not None:
                    params[p] = getattr(self, p)
                elif (
                    p in FORM_FIELD_BASE_KEYS
                    and getattr(self.model_form_field, p, None) is not None
                ):
                    params[p] = getattr(self.model_form_field, p)
        if force_not_required:
            params["required"] = False
        elif force_select and self.model_field and not self.model_field.blank:
            params["required"] = True
        return params

    def get_form_field_class(self, force_select=False, **kwargs):
        cls = self.form_field_class
        if isinstance(cls, str):
            cls = getattr(forms, cls, None)
            if cls is None:
                raise InvalidColumn(
                    gettext("{} is not a valid django forms field class").format(
                        self.form_field_class
                    )
                )
        if force_select and issubclass(cls, forms.BooleanField):
            cls = forms.ChoiceField
        return cls

    def get_form_field_widget(self, field_class, **kwargs):
        cls = self.form_field_widget_class or field_class.widget
        if isinstance(cls, str):
            cls = getattr(widgets, cls, None)
            if cls is None:
                raise InvalidColumn(
                    gettext("{} is not a valid django forms widget class").format(
                        self.form_field_widget_class
                    )
                )
        widget_attrs = self.widget_attrs or {}
        attrs = self.form_field_widget_params.pop("attrs", {})
        widget_attrs = HTMLAttributes({**widget_attrs, **attrs})
        if issubclass(cls, forms.Select):
            widget_attrs.add("class", self.theme_form_select_widget_class)
        else:
            widget_attrs.add("class", self.theme_form_widget_class)
        widget_id = f"id-attachedForm-{self.name}{self.listing.suffix}".replace(
            "_", "-"
        )
        widget_attrs.add("id", widget_id)
        return cls(attrs=widget_attrs, **self.form_field_widget_params)

    def create_form_field(self, **kwargs):
        if self.form_field:
            return self.form_field
        cls = self.get_form_field_class(**kwargs)
        params = self.get_form_field_params(**kwargs)
        widget = self.get_form_field_widget(cls, **kwargs)
        if self.listing.model and self.model_field:
            widget.attrs["data-model-field"] = self.model_field.name
            if isinstance(self.model_field, ForeignKey) and "queryset" not in params:
                params["queryset"] = self.model_field.related_model.objects.all()
        field = cls(widget=widget, **params)
        return field

    def get_hidden_form_field_params(self):
        return dict(required=False)

    def create_hidden_form_field(self):
        cls = self.get_form_field_class()
        params = self.get_hidden_form_field_params()
        widget = widgets.HiddenInput()
        field = cls(widget=widget, **params)
        return field

    def set_params_choices(self, params):
        if not params.get("choices"):
            if getattr(self, "model_field", None):
                params["choices"] = self.model_field.choices
            elif self.listing.model:
                try:
                    model = self.listing.model
                    params["choices"] = model._meta.get_field(self.name).choices
                except (models.FieldDoesNotExist, AttributeError):
                    raise InvalidFilters(
                        _(
                            "Cannot find choices from model "
                            'for filter "{name}", Please specify the choices to '
                            "display"
                        ).format(name=self.name)
                    )
            else:
                raise InvalidFilters(
                    _(
                        "Please specify the choices to display " 'for filter "{name}"'
                    ).format(name=self.name)
                )


class TextColumn(Column):
    from_model_field_classes = (models.TextField,)
    form_field_widget_class = widgets.Textarea
    widget_attrs = {"rows": "3"}


class BooleanColumn(Column):
    true_tpl = _("True")
    false_tpl = _("False")
    params_keys = "true_tpl,false_tpl"
    from_model_field_classes = (models.BooleanField, models.NullBooleanField)
    form_field_class = forms.BooleanField
    required = False

    def get_value_tpl(self, rec, ctx, value):
        return self.true_tpl if value else self.false_tpl

    def get_form_field_widget(self, field_class, force_select=False, **kwargs):
        widget_attrs = HTMLAttributes(self.widget_attrs)
        if force_select:
            widget_attrs.add("class", self.theme_form_select_widget_class)
            return forms.Select(attrs=widget_attrs)
        else:
            widget_attrs.add("class", self.theme_form_checkbox_widget_class)
            return forms.CheckboxInput(attrs=widget_attrs)

    def get_form_field_params(self, force_select=False, **kwargs):
        params = super().get_form_field_params(force_select=force_select, **kwargs)
        if force_select:
            params["choices"] = [
                ("", self.no_choice_msg),
                ("True", self.true_msg),
                ("False", self.false_msg),
            ]
        return params


class IntegerColumn(Column):
    from_model_field_classes = (models.IntegerField,)
    form_field_class = forms.IntegerField


class FloatColumn(Column):
    from_model_field_classes = (models.FloatField,)
    form_field_class = forms.FloatField
    float_format = ".2f"
    params_keys = "float_format"

    # /!\ do not redefine get_cell_value otherwise the value will be modified on export
    def get_cell_context(self, rec, value):
        if not isinstance(value, float):
            try:
                value = float(value)
            except ValueError:
                pass
        if isinstance(value, float):
            value = f"{value:{self.float_format}}"
        return super().get_cell_context(rec, value)


class DecimalColumn(FloatColumn):
    from_model_field_classes = (models.DecimalField,)
    form_field_class = forms.DecimalField


class ChoiceColumn(Column):
    choices = {}
    params_keys = "choices"
    from_model_field_order = 50
    form_field_class = forms.ChoiceField

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        if not isinstance(self.choices, dict):
            self.choices = OrderedDict(self.choices)

    @classmethod
    def from_model_field(cls, field, **kwargs):
        if hasattr(field, "choices") and field.choices:
            return ChoiceColumn(
                field.name,
                model_field=field,
                choices=OrderedDict(field.choices),
                **kwargs,
            )

    def get_value_tpl(self, rec, ctx, value):
        if self.use_raw_value:
            return value
        return self.choices.get(value, value)

    def get_form_field_params(
        self, have_empty_choice=False, force_select=False, **kwargs
    ):
        params = super().get_form_field_params(
            have_empty_choice=have_empty_choice, force_select=force_select, **kwargs
        )
        self.set_params_choices(params)
        if have_empty_choice and (
            self.input_type not in ("radio", "radioinline") or force_select
        ):
            params["choices"] = [("", self.no_choice_msg)] + list(params["choices"])
        return params

    def get_form_field_widget(self, field_class, force_select=False, **kwargs):
        widget_attrs = HTMLAttributes(self.widget_attrs)
        if self.input_type == "radio" and not force_select:
            widget = forms.RadioSelect
            widget_attrs.add("class", self.theme_form_radio_widget_class)
            widget_attrs.add("class", "multiple-radios")
        elif self.input_type == "radioinline" and not force_select:
            widget = forms.RadioSelect
            widget_attrs.add("class", self.theme_form_radio_widget_class)
            widget_attrs.add("class", "multiple-radios inline")
        else:
            widget = forms.Select
            widget_attrs.add("class", self.theme_form_select_widget_class)
        return widget(attrs=widget_attrs)


class MultipleChoiceColumn(Column):
    choices = {}
    params_keys = "choices"
    from_model_field_order = 90
    form_field_class = forms.MultipleChoiceField

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        if not isinstance(self.choices, dict):
            self.choices = OrderedDict(self.choices)

    @classmethod
    def from_model_field(cls, field, **kwargs):
        if hasattr(field, "choices") and field.choices:
            return MultipleChoiceColumn(
                field.name,
                model_field=field,
                choices=OrderedDict(field.choices),
                **kwargs,
            )

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        return self.choices.get(value, value)

    def get_form_field_params(self, have_empty_choice=False, **kwargs):
        params = super().get_form_field_params(
            have_empty_choice=have_empty_choice, **kwargs
        )
        self.set_params_choices(params)
        if have_empty_choice and self.input_type not in ("checkbox", "checkboxinline"):
            params["choices"] = [("", self.no_choice_msg)] + list(params["choices"])
        return params

    def get_form_field_widget(self, field_class, **kwargs):
        widget_attrs = HTMLAttributes(self.widget_attrs)
        if self.input_type == "checkbox":
            widget = forms.CheckboxSelectMultiple
            widget_attrs.add("class", self.theme_form_radio_widget_class)
            widget_attrs.add("class", "multiple-checkboxes")
        elif self.input_type == "checkboxinline":
            widget = forms.CheckboxSelectMultiple
            widget_attrs.add("class", self.theme_form_radio_widget_class)
            widget_attrs.add("class", "multiple-checkboxes inline")
        else:
            widget = forms.CheckboxInput
            widget_attrs.add("class", self.theme_form_select_widget_class)
        return widget(attrs=widget_attrs)


class ManyColumn(Column):
    many_separator = ", "
    params_keys = "many_separator,cell_map,cell_map_value,cell_filter,cell_reduce"
    from_model_field_classes = (models.ManyToManyField, models.ManyToManyRel)
    form_field_class = forms.ModelMultipleChoiceField
    params_keys = "no_foreignkey_link"
    no_foreignkey_link = False
    editable = False

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        qs = getattr(self, "queryset", None)
        if not qs and self.model_field:
            self.queryset = self.model_field.related_model.objects.all()

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        value = self.cell_filter(value)
        value = map(self.cell_map, value)
        value = self.cell_reduce(value)
        return mark_safe(value)

    def get_cell_filter_link(self, rec, ctx, value):
        return None

    def cell_filter(self, value):
        if isinstance(value, models.Manager):
            value = value.all()
        return value

    def cell_map_add_filter(self, out, value):
        listing = self.listing
        filters = listing.filters
        if filters:
            filter_name = self.cell_with_filter_name or self.name
            filter_obj = filters.get(filter_name)
            if filter_obj:
                filter_link = listing.get_url(**{filter_obj.input_name: value.pk})
                out += (
                    f'<a href="{filter_link}" '
                    f'class="cell-filter {self.theme_cell_with_filter_icon}"></a>'
                )
        return out

    def cell_map_value(self, obj):
        return force_str(obj)

    def cell_map(self, obj):
        out = self.cell_map_value(obj)
        if not self.no_foreignkey_link and hasattr(obj, "get_absolute_url"):
            url = obj.get_absolute_url()
            if url is not None:
                out = f'<a href="{url}">{out}</a>'
        if self.has_cell_filter:
            out = self.cell_map_add_filter(out, obj)
        return out

    def cell_reduce(self, value):
        return self.many_separator.join(value)


class CheckboxColumn(Column):
    sortable = False

    def get_value_tpl(self, rec, ctx, value):
        attrs = HTMLAttributes(self.widget_attrs)
        attrs.add("type", "checkbox")
        attrs.add("name", self.name)
        attrs.add("class", self.theme_form_checkbox_widget_class)
        # If a value is set at definition time : take it
        # otherwise : take cell value
        if self.cell_value is not None:
            value = self.cell_value
        if value:
            attrs.set("checked")
        return "<input{}>".format(attrs)


class ButtonColumn(Column):
    label = _("Button")
    sortable = False

    def get_value_tpl(self, rec, ctx, value):
        attrs = HTMLAttributes(self.widget_attrs)
        attrs.add("type", "button")
        attrs.add("name", self.name)
        attrs.add("class", self.theme_button_class)
        return "<button{attrs}>{label}</button>".format(
            attrs=attrs, label=conditional_escape(self.label)
        )


class SelectColumn(Column):
    sortable = False
    choices = {}

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        if not isinstance(self.choices, dict):
            self.choices = OrderedDict(self.choices)

    def get_value_tpl(self, rec, ctx, value):
        attrs = HTMLAttributes(self.widget_attrs)
        attrs.add("name", self.name)
        attrs.add("class", self.theme_form_select_widget_class)
        # If a value is set at definition time : take it
        # otherwise : take cell value
        if self.cell_value is not None:
            value = self.cell_value
        options = [
            '<option value="{key}"{sel}>{val}</option>\n'.format(
                key=k, val=conditional_escape(v), sel=" selected" if value == k else ""
            )
            for k, v in self.choices.items()
        ]
        return "<select{}>\n{}</select>".format(attrs, options)


class InputColumn(Column):
    widget_attrs = {"type": "text"}
    sortable = False

    def get_value_tpl(self, rec, ctx, value):
        attrs = HTMLAttributes(self.widget_attrs)
        attrs.add("name", self.name)
        attrs.add("class", self.theme_form_widget_class)
        return "<input{attrs}>".format(attrs=attrs)


class DateColumn(Column):
    date_format = settings.DATE_FORMAT
    params_keys = "date_format"
    from_model_field_classes = (models.DateField,)
    form_field_class = forms.DateField
    form_field_widget_params = {"format": "%Y-%m-%d"}
    widget_attrs = {"class": "edit-datecolumn", "autocomplete": "off", "type": "date"}

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        if isinstance(value, datetime.date):
            return formats.date_format(value, self.date_format)
        return value

    def get_cell_exported_value(self, rec, keep_original_type=True):
        value = super().get_cell_value(rec)
        return value


class DateTimeColumn(Column):
    datetime_format = settings.DATETIME_FORMAT
    params_keys = "datetime_format"
    from_model_field_classes = (models.DateTimeField,)
    form_field_widget_params = {"format": "%Y-%m-%d %H:%M"}
    widget_attrs = {
        "class": "edit-datetimecolumn",
        "autocomplete": "off",
        "type": "datetime-local",
    }

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        if isinstance(value, datetime.date):  # date also match datetime
            return formats.date_format(value, self.datetime_format)
        return value

    def get_cell_exported_value(self, rec, keep_original_type=True):
        value = super().get_cell_value(rec)
        if isinstance(value, datetime.date):
            if keep_original_type:
                value = value.replace(tzinfo=None)
            else:
                value = formats.date_format(value, self.datetime_format)
        return value


class JsonDateTimeColumn(Column):
    datetime_format = settings.DATETIME_FORMAT
    params_keys = "datetime_format"

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        if isinstance(value, str):
            value = (
                parse_datetime(value) or value
            )  # convert json date to datetime object
        if isinstance(value, datetime.date):  # date also match datetime
            return formats.date_format(value, self.datetime_format)
        return value

    def get_cell_exported_value(self, rec, keep_original_type=True):
        value = super().get_cell_value(rec)
        if isinstance(value, str):
            value = (
                parse_datetime(value) or value
            )  # convert json date to datetime object
        if keep_original_type:
            value = value.replace(tzinfo=None)
        else:
            value = formats.date_format(value, self.datetime_format)
        return value


class FileSizeColumn(Column):
    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        if isinstance(value, (int, float)):
            return filesizeformat(value)
        return value


class TimeColumn(Column):
    time_format = settings.TIME_FORMAT
    params_keys = "time_format"
    from_model_field_classes = (models.TimeField,)
    widget_attrs = {"class": "edit-timecolumn", "autocomplete": "off"}

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        if isinstance(value, datetime.date):  # date also match datetime
            return formats.time_format(value, self.time_format)
        return value

    def get_cell_exported_value(self, rec, keep_original_type=True):
        value = super().get_cell_value(rec)
        if isinstance(value, datetime.date):
            if keep_original_type:
                value = value.replace(tzinfo=None)
            else:
                value = formats.time_format(value, self.time_format)
        return value


class LinkColumn(Column):
    params_keys = "link_attrs,href_tpl,no_link"
    href_tpl = None
    no_link = False
    link_attrs = None
    cell_tpl = "<td{attrs}><a{link_attrs}>%s</a></td>"
    cell_edit_tpl = "<td{attrs}>%s</td>"
    cell_with_filter_tpl = (
        '<td{attrs}><span class="cell-with-filter">'
        '<span class="cell-value"><a{link_attrs}>%s</a></span>'
        '<a href="{filter_link}" '
        'class="cell-filter {col.theme_cell_with_filter_icon}">'
        "</a></span></td>"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        if self.is_safe_value:
            return value
        if isinstance(value, str):
            value = escape(value)
        return value

    def get_link_attrs(self, rec, value):
        link_attrs = self.link_attrs
        if isinstance(link_attrs, ListingMethodRef):
            link_attrs = link_attrs(self.listing, self, rec, value)
        elif callable(link_attrs):
            link_attrs = link_attrs(rec, value)
        attrs = HTMLAttributes(link_attrs or {})
        return attrs

    def get_href_tpl(self, rec, value):
        href_tpl = self.href_tpl
        if isinstance(href_tpl, ListingMethodRef):
            href_tpl = href_tpl(self.listing, self, rec, value)
        elif callable(href_tpl):
            href_tpl = href_tpl(rec, value)
        return href_tpl

    def get_href(self, rec, ctx, value):
        href_tpl = self.get_href_tpl(rec, value)
        if isinstance(href_tpl, str):
            return href_tpl.format(**ctx)
        return None

    def get_cell_context(self, rec, value):
        ctx = super().get_cell_context(rec, value)
        ctx.link_attrs = self.get_link_attrs(rec, value)
        if not self.no_link:
            ctx.link_attrs.add("href", self.get_href(rec, ctx, value))
        return ctx


class ButtonLinkColumn(LinkColumn):
    label = "Button"

    def get_link_attrs(self, rec, value):
        attrs = super().get_link_attrs(rec, value)
        attrs.add("class", self.theme_button_class)
        return attrs

    def get_cell_value(self, rec):
        value = mark_safe(self.label)
        return value


class URLColumn(LinkColumn):
    href_tpl = "{value}"
    from_model_field_classes = (models.URLField,)
    form_field_widget_class = widgets.URLInput
    params_keys = "remove_proto"
    remove_proto = True

    def get_cell_context(self, rec, value):
        ctx = super().get_cell_context(rec, value)
        if self.remove_proto and not self.can_edit:
            ctx.value = re.sub("^.*?//", "", ctx.value)
        return ctx


class EmailColumn(LinkColumn):
    href_tpl = "mailto:{value}"
    from_model_field_classes = (models.EmailField,)
    form_field_widget_class = widgets.EmailInput


class LinkObjectColumn(LinkColumn):
    editable = False

    def get_href(self, rec, ctx, value):
        return rec.get_href()


class ForeignKeyColumn(LinkColumn):
    from_model_field_classes = (models.ForeignKey,)
    form_field_class = forms.ModelChoiceField
    params_keys = "no_foreignkey_link"
    no_foreignkey_link = False
    editable = False

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        if "queryset" in kwargs:
            self.queryset = kwargs["queryset"]
        qs = getattr(self, "queryset", None)
        if qs is None and self.model_field:
            self.queryset = self.model_field.related_model.objects.all()

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        if self.is_safe_value:
            return value
        value = str(value)  # already escaped
        return value

    def get_href(self, rec, ctx, value):
        if self.no_foreignkey_link:
            return None
        if self.href_tpl:
            return super().get_href(rec, ctx, value)
        try:
            return rec[self.name].get_absolute_url()
        except (IndexError, AttributeError):
            return super().get_href(rec, ctx, value)


class AutoCompleteColumn(ForeignKeyColumn):
    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        self.listing.need_media_for("autocomplete")


class FileColumn(LinkColumn):
    from_model_field_classes = (models.FileField,)
    form_field_class = forms.FileField
    params_keys = "check_file, path_tpl, no_file_link"
    check_file = True
    no_file_link = False
    path_tpl = "{MEDIA_ROOT}/{value.name}"

    def get_path_tpl(self, rec, ctx, value):
        path_tpl = self.path_tpl
        if callable(path_tpl):
            path_tpl = path_tpl(rec, ctx, value)
        return path_tpl

    def get_href(self, rec, ctx, value):
        if self.no_file_link:
            return None
        url = None
        if self.check_file:
            storage = getattr(value, "storage", None)
            if storage:
                if storage.exists(value.name):
                    if self.href_tpl:
                        url = super().get_href(rec, ctx, value)
                    else:
                        url = storage.url(value.name)
            else:
                path = self.get_path_tpl(rec, ctx, value).format(**ctx)
                if os.path.exists(path):
                    url = super().get_href(rec, ctx, value)
            if not url:
                ctx.link_attrs.add("class", "missing")
        return url


class ComputedColumnMixin:
    editable = False
    sortable = False

    def get_row_numeric_values(self, rec):
        values = []
        for col in self.listing.selected_columns:
            if not isinstance(col, ComputedColumnMixin):
                value = col.get_cell_value(rec)
                if isinstance(value, (int, float)):
                    values.append(value)
        return values


class TotalColumn(ComputedColumnMixin, Column):
    name = "cc_total"  # 'cc' for computed column
    header = _("Total")
    aggregation = "sum"  # aggregate rows
    footer_tpl = _("<td{attrs}>Grand Total:<br>{value}</td>")

    @cache_in_record
    def get_cell_value(self, rec):
        return sum(self.get_row_numeric_values(rec))  # aggregate columns


class MinColumn(ComputedColumnMixin, Column):
    name = "cc_min_value"
    header = _("Min")
    aggregation = "min"
    footer_tpl = _("<td{attrs}>Overall Min:<br>{value}</td>")

    def get_cell_value(self, rec):
        return min(self.get_row_numeric_values(rec))


class MaxColumn(ComputedColumnMixin, Column):
    name = "cc_max_value"
    header = _("Max")
    aggregation = "max"
    footer_tpl = _("<td{attrs}>Overall Max:<br>{value}</td>")

    def get_cell_value(self, rec):
        return max(self.get_row_numeric_values(rec))


class AvgColumn(ComputedColumnMixin, Column):
    params_keys = "precision, footer_precision"
    name = "cc_average"
    header = _("Average")
    precision = 2
    footer_precision = 2
    value_tpl = "{value:.{col.precision}f}"
    aggregation = "avg"
    footer_tpl = _("<td{attrs}>Overall avg:<br>{value:.{col.footer_precision}f}</td>")

    def get_cell_value(self, rec):
        values = self.get_row_numeric_values(rec)
        if values:
            return sum(values) / len(values)
        return self.default_value


class LineNumberColumn(Column):
    name = "auto_line_number"
    header = "#"
    sortable = False
    start = 1

    def get_cell_value(self, rec):
        current_page = getattr(rec.get_listing(), "current_page", None)
        page_start = current_page.start_index() if current_page else 1
        return page_start + rec.get_index() + self.start - 1


class SelectionColumn(Column):
    sortable = False
    theme_header_icon = "listing-icon-ok"
    header_tpl = "<th{attrs}><span class={col.theme_header_icon}></span></th>"

    def get_cell_context(self, rec, value):
        context = super().get_cell_context(rec, value)
        context["selection_value"] = rec.get(self.listing.selection_key)
        context["checked"] = " checked" if rec.is_selected() else ""
        return context

    def get_value_tpl(self, rec, ctx, value):
        if self.listing.selection_multiple:
            widget_class = " ".join(self.theme_form_checkbox_widget_class)
            tpl = (
                '<input type="checkbox" name="selected_rows{listing.suffix}" '
                f'class="selection-box {widget_class}" '
                'value="{selection_value}"{checked}>'
            )
        else:
            widget_class = " ".join(self.theme_form_radio_widget_class)
            tpl = (
                '<input type="radio" name="selected_rows{listing.suffix}" '
                f'class="selection-box {widget_class}" '
                'value="{selection_value}"{checked}>'
            )
        return tpl


class GroupByFilterColumn(Column):
    sortable = False
    label = pgettext_lazy("verb", "Filter")
    name = "group_by_filter"
    header = pgettext_lazy("verb", "Filter")
    link_target = "_blank"
    theme_cell_with_filter_icon = "listing-icon-link-ext"
    exportable = False

    def action_filter(self, rec):
        url = rec.get_url(
            filters=self.listing.gb_model_filters_mapping,
            without="gb_cols,gb_annotate_cols",
        )
        out = f'<a class="{self.theme_button_link_class} gb-filter" href="{url}"'
        if self.link_target:
            out += f' target="{self.link_target}"'
        out += f">{self.label}"
        if self.theme_cell_with_filter_icon:
            out += f' <span class="{self.theme_cell_with_filter_icon}"></span>'
        out += "</a>"
        return mark_safe(out)

    @cache_in_record
    def get_cell_value(self, rec):
        if isinstance(self.cell_value, ListingMethodRef):
            value = self.cell_value(self.listing, self, rec)
        elif callable(self.cell_value):
            value = self.cell_value(self, rec)
        else:
            value = self.action_filter(rec)
        return value
