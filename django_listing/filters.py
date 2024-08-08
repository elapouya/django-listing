#
# Created : 2018-04-04
#
# @author: Eric Lapouyade
#
import copy
import re
from datetime import timedelta
from itertools import chain

from dal import autocomplete
from django import forms
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models import DateTimeField, QuerySet
from django.forms import FileField
from django.template import loader
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext_lazy

from .context import RenderContext
from .exceptions import InvalidFilters
from .html_attributes import HTMLAttributes
from .theme_config import ThemeTemplate, ThemeAttribute
from .utils import init_dicts_from_class

__all__ = [
    "Filter",
    "AutocompleteForeignKeyFilter",
    "AutocompleteMultipleForeignKeyFilter",
    "BooleanFilter",
    "ChoiceFilter",
    "DateFilter",
    "DateTimeFilter",
    "FILTER_QUERYSTRING_PREFIX",
    "Filters",
    "FILTERS_PARAMS_KEYS",
    "ForeignKeyFilter",
    "IntegerFilter",
    "FloatFilter",
    "MultipleChoiceFilter",
    "MultipleForeignKeyFilter",
    "TimeFilter",
]

# Declare keys only for "Filters" object
FILTERS_KEYS = {
    "form_attrs",
    "form_buttons",
    "form_layout",
    "form_layout_advanced",
    "form_reset_label",
    "form_submit_label",
    "form_advanced_label",
    "form_template_name",
    "theme_form_submit_icon",
    "theme_form_reset_icon",
    "theme_form_submit_class",
    "theme_form_reset_class",
}

# Declare keys for "Filter" object (not "Filters" with an ending 's')
FILTERS_PARAMS_KEYS = {
    "format_label",
    "container_attrs",
    "filter_key",
    "field_name",
    "input_type",
    "key_type",
    "model_field",
    "name",
    "no_choice_msg",
    "order_by",
    "queryset",
    "shrink_width",
    "widget_attrs",
    "widget_class",
    "widget_params",
    "word_search",
    "url",
    "choices",
    "filter_queryset_method",
    "add_one_day",
    "default_value",
}

# Declare keys for django form fields
FILTERS_FORM_FIELD_KEYS = {
    "choices",
    "disabled",
    "empty_value",
    "empty_label",
    "queryset",
    "error_messages",
    "help_text",
    "initial",
    "label",
    "label_suffix",
    "localize",
    "max_length",
    "min_length",
    "required",
    "strip",
    "validators",
    "widget",
}

FILTERS_PARAMS_KEYS.update(FILTERS_KEYS)
FILTERS_PARAMS_KEYS.update(FILTERS_FORM_FIELD_KEYS)
FILTER_QUERYSTRING_PREFIX = "f_"


class FiltersBaseForm(forms.BaseForm):
    def _clean_fields(self):
        for name, field in self.fields.items():
            if field.disabled:
                value = self.get_initial_for_field(field, name)
            else:
                value = field.widget.value_from_datadict(
                    self.data, self.files, self.add_prefix(name)
                )
            try:
                if isinstance(field, FileField):
                    initial = self.get_initial_for_field(field, name)
                    value = field.clean(value, initial)
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value

                if value is None and not field.required:
                    continue
                filter_name = name[len(FILTER_QUERYSTRING_PREFIX) :]
                method_name = f"filter_form_clean_{filter_name}"
                method = getattr(self.listing, method_name, None)
                if method:
                    value = method(self)
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)

    def _clean_form(self):
        try:
            method_name = f"filter_form_clean"
            method = getattr(self.listing, method_name, None)
            if method:
                cleaned_data = method(self)
            else:
                cleaned_data = self.cleaned_data
        except ValidationError as e:
            self.add_error(None, e)
        else:
            if cleaned_data is not None:
                self.cleaned_data = cleaned_data


class Filters(list):
    id = None
    listing = None
    form_reset_label = pgettext_lazy("Filters form", "Reset")
    form_submit_label = pgettext_lazy("Filters form", "Filter")
    form_advanced_label = pgettext_lazy("Filters form", "Advanced")
    form_template_name = ThemeTemplate("filters_form.html")
    theme_form_reset_icon = ThemeAttribute("filters_theme_form_reset_icon")
    theme_form_reset_class = ThemeAttribute("filters_theme_form_reset_class")
    theme_form_submit_icon = ThemeAttribute("filters_theme_form_submit_icon")
    theme_form_submit_class = ThemeAttribute("filters_theme_form_submit_class")
    theme_form_advanced_down_icon = ThemeAttribute(
        "filters_theme_form_advanced_down_icon"
    )
    theme_form_advanced_up_icon = ThemeAttribute("filters_theme_form_advanced_up_icon")
    theme_form_advanced_class = ThemeAttribute("filters_theme_form_advanced_class")
    form_layout = None
    form_layout_advanced = None
    form_buttons = "reset,submit"
    show_advanced = False

    def __init__(self, *filters, params=None, **kwargs):
        self.init_kwargs = kwargs
        # params contains Filter objects parameters, ex :
        # params = {"filter1": {"param1" : "value1" ...}, "filter2": {"param2" : "value2" ...}
        if params is None:
            params = {}
        self._params = params
        self._form = None
        self.name2filter = {}
        init_dicts_from_class(self, ["form_attrs"])
        super().__init__(filters)

    def get(self, name, default=None):
        return self.name2filter.get(name, default)

    def get_params(self):
        return self._params

    def names(self):
        return self.name2filter.keys()

    def select(self, select_filters_name=None, exclude_filters_name=None):
        if isinstance(select_filters_name, str):
            select_filters_name = map(str.strip, select_filters_name.split(","))
        if isinstance(exclude_filters_name, str):
            exclude_filters_name = map(str.strip, exclude_filters_name.split(","))
        select_filters_name = select_filters_name or self.names()
        exclude_filters_name = exclude_filters_name or []
        return [
            self.get(c.strip())
            for c in select_filters_name
            if c not in exclude_filters_name
        ]

    def normalize_layout(self, layout):
        if isinstance(layout, str):
            # transform layout string into list of lists of lists
            layout = re.sub(r"\s", "", layout)
            layout = list(
                map(
                    lambda s: list(
                        map(
                            lambda t: (t.split("|") + [None, None, None])[:4],
                            filter(None, s.split(",")),
                        )
                    ),
                    filter(None, layout.split(";")),
                )
            )
        if layout is None:
            layout = []
        return layout

    def bind_to_listing(self, listing):
        filters = Filters(params=self._params, **self.init_kwargs)
        for k in FILTERS_KEYS:
            if k in self.init_kwargs:
                setattr(filters, k, self.init_kwargs[k])
            elif hasattr(self, k):
                setattr(filters, k, getattr(self, k))
            listing_key = "filters_" + k
            if hasattr(listing, listing_key):
                setattr(filters, k, getattr(listing, listing_key))
        if filters.form_layout is None:
            filters.form_layout = [
                [[filtr.name, None, None, None]]
                for filtr in filters
                if isinstance(filtr, Filter)
            ]
        filters.form_layout = self.normalize_layout(filters.form_layout)
        filters.form_layout_advanced = self.normalize_layout(
            filters.form_layout_advanced
        )
        for filtr in self:
            if not isinstance(filtr, Filter):
                # understand, filtr is a string
                filtr = self.create_filter(filtr, listing)
            # ensure there is one filter instance per listing
            elif not filtr.listing:
                filtr = copy.copy(filtr)  # do not use deepcopy here
            if isinstance(filtr, Filter):
                filtr.bind_to_listing(listing)
                filters.append(filtr)
        filters.name2filter = {f.name: f for f in filters if isinstance(f, Filter)}
        filters.modelfieldname2filter = {
            f.from_model_field_name: f for f in filters if isinstance(f, Filter)
        }
        filters.listing = listing
        # extract labels and endings from given layout
        for row in chain(filters.form_layout, filters.form_layout_advanced):
            for name, label, ending, input_type in row:
                filtr = filters.name2filter.get(name)
                if filtr:
                    if label:
                        filtr.label = label
                    if ending:
                        filtr.ending = ending
                    if input_type:
                        filtr.input_type = input_type
        fbuttons = filters.form_buttons
        if isinstance(fbuttons, str):
            filters.form_buttons = list(map(str.strip, fbuttons.split(",")))
        return filters

    def datetimepicker_init(self):
        if self.listing.use_datetimepicker:
            self.listing.need_media_for("datetimepicker")
            self.listing.add_onready_snippet(
                f"""
                $('#{self.id} .edit-datecolumn').datetimepicker({{timepicker:false, format:'{self.listing.datetimepicker_date_format}'}});
                $('#{self.id} .edit-datetimecolumn').datetimepicker({{format:'{self.listing.datetimepicker_datetime_format}'}});
                $('#{self.id} .edit-timecolumn').datetimepicker({{datepicker:false, format:'{self.listing.datetimepicker_time_format}'}});
                """
            )

    def create_filter(self, name, listing):
        if isinstance(name, str):
            model_attr_name, *dummy = name.split("__")
            if issubclass(listing.model, models.Model):
                field = listing.model._meta.get_field(model_attr_name)
                if field:
                    for filter_class in FilterMeta.get_filter_classes():
                        if filter_class is not Filter:
                            filtr = filter_class.from_model_field(name, field)
                            if filtr:
                                return filtr
            return Filter(name)
        return None

    def extract_params(self):
        request_get_data = self.listing.request.GET
        for f in self:
            if not request_get_data and f.default_value is not None:
                f.value = f.default_value
            else:
                f.extract_params(request_get_data)

    def form(self):
        if not self._form:
            fields = {
                f.input_name + self.listing.suffix: f.create_form_field() for f in self
            }
            initial = {
                f.input_name + self.listing.suffix: f.default_value
                for f in self
                if f.default_value is not None
            }
            form_class = type(
                "FilterForm{}".format(self.listing.suffix),
                (FiltersBaseForm,),
                {"base_fields": fields},
            )
            self._form = form_class(self.listing.request.GET or None, initial=initial)
            self._form.listing = self.listing
        return self._form

    def get_hiddens_html(self):
        query_fields = [(FILTER_QUERYSTRING_PREFIX + f.name) for f in self]
        query_fields.append(FILTER_QUERYSTRING_PREFIX + "do_filter")
        return self.listing.get_hiddens_html(without=query_fields)

    def render_init(self, context):
        self.listing.manage_page_context(context)
        advanced_filters_names = {b[0] for a in self.form_layout_advanced for b in a}
        requested_filter = {
            k[len(FILTER_QUERYSTRING_PREFIX) :]
            for k, v in self.listing.request.GET.items()
            if k.startswith(FILTER_QUERYSTRING_PREFIX) and v
        }
        if advanced_filters_names & requested_filter:
            self.show_advanced = True
        if not isinstance(self.form_attrs, HTMLAttributes):
            self.form_attrs = HTMLAttributes(self.form_attrs)
        self.form_attrs.add("class", {"listing-form", "filters-form"})
        if self.listing.accept_ajax:
            self.form_attrs.add("class", "django-filters-ajax")
        if "id" not in self.form_attrs:
            self.form_attrs.add("id", "filters-form-id{}".format(self.listing.suffix))
        self.id = self.form_attrs["id"]
        self.datetimepicker_init()

    def render_form(self, context):
        self.render_init(context)
        ctx = self.get_context()
        template = loader.get_template(self.form_template_name)
        out = template.render(ctx)
        return out

    def get_form_reset_url(self):
        query_fields = [(FILTER_QUERYSTRING_PREFIX + f.name) for f in self]
        query_fields += [f"{FILTER_QUERYSTRING_PREFIX}do_filter"]
        return self.listing.get_url(without=query_fields)

    def get_form_field(self, name):
        filter = self.get(name)
        if filter is None:
            raise InvalidFilters(
                _('Cannot find filter "{name}" definition').format(name=name)
            )
        return self.form()[filter.input_name + self.listing.suffix]

    def get_form_field_container_attrs(self, name):
        filter = self.get(name)
        if filter is None:
            raise InvalidFilters(
                _('Cannot find filter "{name}" definition').format(name=name)
            )
        form_field = self.form()[filter.input_name + self.listing.suffix]
        return filter.get_form_field_container_attrs(form_field)

    def get_context(self):
        ctx = RenderContext(
            self.listing.global_context,
            self.listing.page_context.flatten(),
            listing=self.listing,
            filters=self,
            get=self.listing.request.GET,
        )
        return ctx


class FilterMeta(type):
    filter_classes = []

    def __new__(mcs, name, bases, attrs):
        cls = super(FilterMeta, mcs).__new__(mcs, name, bases, attrs)
        FilterMeta.filter_classes.append((cls, cls.from_model_field_order))
        params_keys = cls.params_keys
        if params_keys:
            if isinstance(params_keys, str):
                params_keys = set(map(str.strip, params_keys.split(",")))
            FILTERS_PARAMS_KEYS.update(params_keys)
            FILTERS_PARAMS_KEYS.discard("")
        form_field_keys = cls.form_field_keys
        if form_field_keys:
            if isinstance(form_field_keys, str):
                form_field_keys = set(map(str.strip, form_field_keys.split(",")))
            FILTERS_FORM_FIELD_KEYS.update(form_field_keys)
            FILTERS_FORM_FIELD_KEYS.discard("")
            FILTERS_PARAMS_KEYS.update(FILTERS_FORM_FIELD_KEYS)
        return cls

    @classmethod
    def get_filter_classes(cls):
        return [t[0] for t in sorted(cls.filter_classes, key=lambda x: x[1])]


class Filter(metaclass=FilterMeta):
    from_model_field_order = 100
    from_model_field_classes = ()
    from_model_field_name = None  # used by GroupByFilterColumn indirectly
    form_field_class = forms.CharField
    container_attrs = {"class": "form-field"}
    shrink_width = None
    form_field_keys = None
    params_keys = None
    name = None
    label = None
    value = None
    url = None
    filter_key = None
    field_name = None
    order_by = None
    queryset = None
    format_label = None
    key_type = None
    input_name = None
    input_type = None
    required = False
    listing = None
    widget_attrs = None
    widget_class = None
    widget_params = None
    no_choice_msg = gettext_lazy("- No filtering -")
    help_text = None
    word_search = False
    filter_queryset_method = None
    default_value = None

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

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        init_dicts_from_class(
            self, ["widget_attrs", "form_field_attrs", "widget_params"]
        )
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

    def bind_to_listing(self, listing):
        self.init(listing, *self.init_args, **self.init_kwargs)

    def set_listing(self, listing):
        self.listing = listing

    def init(self, listing, name=None, **kwargs):
        self.set_listing(listing)
        lsg = self.listing
        if name:
            self.name = re.sub(r"\W", "", name)
        self.set_kwargs(**kwargs)
        self.apply_template_kwargs()
        if self.filter_key is None:
            self.filter_key = self.name
        if self.field_name is None:
            self.field_name, *dummy = self.filter_key.split("__")
        if self.format_label is None:
            self.format_label = lambda obj: str(obj)
        elif isinstance(self.format_label, str):
            field = str(self.format_label)
            self.format_label = lambda obj: getattr(obj, field, "-")
        if self.input_name is None:
            self.input_name = FILTER_QUERYSTRING_PREFIX + self.name
        self.label = self.get_label()
        if self.help_text is None:
            self.help_text = "&nbsp;"  # otherwise formfields may me not aligned vertically. keep align-items: flex-end; on row
        if self.from_model_field_name is None:
            self.from_model_field_name, *dummy = self.filter_key.split("__")

    def get_label(self):
        label = self.label
        if label is None:
            try:
                label = self.listing.model._meta.get_field(self.field_name).verbose_name
            except FieldDoesNotExist:
                pass
        if label is None:
            label = self.field_name.replace("_", " ").capitalize()
        return label

    def get_form_field_container_attrs(self, form_field):
        attrs = HTMLAttributes(self.container_attrs)
        attrs.add(
            "class",
            {
                "col-" + self.name,
                "cls-" + self.__class__.__name__.lower(),
                # self.listing.filters.theme_field_class,
            },
        )
        if self.shrink_width:
            attrs.add("style", f"flex-shrink: {self.shrink_width}")
        if form_field.errors:
            attrs.add("class", {"errors"})
        return attrs

    def set_kwargs(self, **kwargs):
        # If filters_<filterclass>_<params> exists in listing attributes :
        # take is as a default value
        for k in FILTERS_PARAMS_KEYS:
            listing_key = "filters_{}".format(k)
            if hasattr(self.listing, listing_key):
                setattr(self, k, getattr(self.listing, listing_key))
        for k, v in kwargs.items():
            if k in FILTERS_PARAMS_KEYS:
                setattr(self, k, v)
        # if parameters given in filters : apply them
        for k, v in self.listing.filters.get_params().get(self.name, {}).items():
            if k in FILTERS_PARAMS_KEYS:
                setattr(self, k, v)
        # if parameters given in listing apply them to specified filter
        for k in FILTERS_PARAMS_KEYS:
            key = "{}{}__{}".format(FILTER_QUERYSTRING_PREFIX, self.name, k)
            v = getattr(self.listing, key, None)
            if v is not None:
                setattr(self, k, v)

    def apply_template_kwargs(self):
        kwargs = self.listing.get_filter_kwargs(self.name)
        if kwargs:
            for k, v in kwargs.items():
                if k in FILTERS_PARAMS_KEYS:
                    if isinstance(v, dict):
                        prev_value = getattr(self, k, None)
                        if isinstance(prev_value, dict):
                            prev_value.update(v)
                            continue
                    setattr(self, k, v)

    @classmethod
    def from_model_field(cls, name, field):
        if field.__class__ in cls.from_model_field_classes:
            return cls(name, model_field=field, label=field.verbose_name)

    def get_form_field_params(self, **kwargs):
        params = {
            p: getattr(self, p)
            for p in FILTERS_FORM_FIELD_KEYS
            if getattr(self, p, None) is not None
        }
        return params

    def get_form_field_class(self, **kwargs):
        return self.form_field_class

    def get_form_field_widget(self, field_class, **kwargs):
        widget_class = self.widget_class or field_class.widget
        widget_attrs = HTMLAttributes(self.widget_attrs)
        widget_attrs.add("class", self.theme_form_widget_class)
        widget_id = f"id-filter-{self.name}{self.listing.suffix}".replace("_", "-")
        widget_attrs.add("id", widget_id)
        params = dict(self.widget_params, attrs=widget_attrs)
        return widget_class(**params)

    def create_form_field(self):
        cls = self.get_form_field_class()
        params = self.get_form_field_params()
        widget = self.get_form_field_widget(cls)
        field = cls(widget=widget, **params)

        patch_help_text_method = getattr(widget, "patch_help_text", None)
        if callable(patch_help_text_method):
            field.help_text = patch_help_text_method(field.help_text)

        return field

    def filter_queryset(self, qs, cleaned_data=None):
        if cleaned_data is not None:
            if not self.value:
                return qs
            cleaned_value = cleaned_data.get(self.input_name + self.listing.suffix)
        else:
            if self.default_value is None:
                return qs
            cleaned_value = self.default_value
        method_name = f"filter_queryset_{self.name}"
        method = getattr(self.listing, method_name, None)
        if not method and self.filter_queryset_method:
            if isinstance(self.filter_queryset_method, str):
                method = getattr(self.listing, self.filter_queryset_method, None)
            else:
                method = self.filter_queryset_method
        if method:
            if self.word_search and isinstance(cleaned_value, str):
                words = filter(None, cleaned_value.split())
                for word in words:
                    qs = method(qs, word)
                return qs
            return method(qs, cleaned_value)
        if self.word_search and isinstance(cleaned_value, str):
            words = filter(None, cleaned_value.split())
            for word in words:
                qs = qs.filter(**{self.filter_key: word})
            return qs
        if "__" not in self.filter_key and isinstance(
            cleaned_value, (QuerySet, list, tuple)
        ):
            return qs.filter(**{f"{self.filter_key}__in": cleaned_value})
        return qs.filter(**{self.filter_key: cleaned_value})

    def filter_sequence(self, seq):
        if not self.value:
            return seq
        key_filter = (
            self.filter_key if "__" in self.filter_key else f"{self.filter_key}__equal"
        )
        key, filtr = key_filter.split("__", 1)
        if filtr == "equal":
            return filter(lambda rec: rec[key] == self.value, seq)
        elif filtr == "contains":
            return filter(
                lambda rec: rec[key] is not None and self.value in str(rec[key]), seq
            )
        elif filtr == "icontains":
            return filter(
                lambda rec: rec[key] is not None
                and self.value.lower() in str(rec[key]).lower(),
                seq,
            )
        elif filtr == "regex":
            return filter(lambda rec: re.search(self.value, rec[key]), seq)
        elif filtr == "iregex":
            return filter(lambda rec: re.search(self.value, rec[key], flags=re.I), seq)
        elif filtr == "lt":
            return filter(
                lambda rec: rec[key] is not None and rec[key] < self.value, seq
            )
        elif filtr == "lte":
            return filter(
                lambda rec: rec[key] is not None and rec[key] <= self.value, seq
            )
        elif filtr == "gt":
            return filter(
                lambda rec: rec[key] is not None and rec[key] > self.value, seq
            )
        elif filtr == "gte":
            return filter(
                lambda rec: rec[key] is not None and rec[key] >= self.value, seq
            )
        return seq

    def extract_params(self, request_get_data):
        self.value = request_get_data.get(self.input_name + self.listing.suffix)

    def set_params_choices(self, params):
        if not params.get("choices"):
            if hasattr(self, "model_field"):
                params["choices"] = self.model_field.choices
            elif self.listing.model:
                try:
                    model = self.listing.model
                    params["choices"] = model._meta.get_field(self.field_name).choices
                except AttributeError:
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


class IntegerFilter(Filter):
    from_model_field_classes = (models.IntegerField,)
    form_field_class = forms.IntegerField


class FloatFilter(Filter):
    from_model_field_classes = (models.FloatField,)
    form_field_class = forms.FloatField


class DateFilter(Filter):
    from_model_field_classes = (models.DateField,)
    form_field_class = forms.DateField
    widget_attrs = {"class": "form-control edit-datecolumn", "type": "date"}
    add_one_day = False  # useful for DateFilter on DateTimeField

    def filter_queryset(self, qs, cleaned_data):
        if not self.value:
            return qs
        if self.add_one_day:
            data_key = self.input_name + self.listing.suffix
            cleaned_value = cleaned_data.get(data_key)
            if cleaned_value:
                cleaned_data[data_key] = cleaned_value + timedelta(days=1)
        return super().filter_queryset(qs, cleaned_data)


class DateTimeFilter(Filter):
    from_model_field_classes = (models.DateTimeField,)
    form_field_class = forms.DateTimeField
    widget_attrs = {
        "class": "form-control edit-datetimecolumn",
        "type": "datetime-local",
    }


class TimeFilter(Filter):
    from_model_field_classes = (models.TimeField,)
    form_field_class = forms.TimeField
    widget_attrs = {"class": "form-control edit-timecolumn", "type": "time"}


class BooleanFilter(Filter):
    from_model_field_classes = (models.BooleanField,)
    form_field_class = forms.ChoiceField
    true_msg = gettext_lazy("Yes")
    false_msg = gettext_lazy("No")
    indifferent_msg = gettext_lazy("Indiff.")

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
        params = dict(self.widget_params, attrs=widget_attrs)
        return widget(**params)

    def get_form_field_params(self, **kwargs):
        params = super().get_form_field_params(**kwargs)
        params["choices"] = [
            ("", self.indifferent_msg),
            ("True", self.true_msg),
            ("False", self.false_msg),
        ]
        return params


class ChoiceFilter(Filter):
    form_field_class = forms.ChoiceField
    form_field_keys = "choices"

    @classmethod
    def from_model_field(cls, name, field):
        choices = getattr(field, "choices", None)
        if choices:
            return cls(
                name, model_field=field, label=field.verbose_name, choices=choices
            )

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
        params = dict(self.widget_params, attrs=widget_attrs)
        return widget(**params)

    def get_form_field_params(self, **kwargs):
        params = super().get_form_field_params(**kwargs)
        self.set_params_choices(params)
        params["choices"] = [("", self.no_choice_msg)] + list(params["choices"])
        return params


class MultipleChoiceFilter(Filter):
    form_field_class = forms.MultipleChoiceField
    form_field_keys = "choices"
    from_model_field_order = 90
    # 90 < 100 (default) means it will consider MultipleChoiceFilter before
    # ChoiceFilter when searching the right filter for a model field.

    def init(self, listing, name=None, **kwargs):
        super().init(listing, name, **kwargs)
        if not self.filter_key.endswith("__in"):
            self.filter_key += "__in"

    @classmethod
    def from_model_field(cls, name, field):
        choices = getattr(field, "choices", None)
        if choices and name.endswith("__in"):
            return cls(name, model_field=field, label=field.verbose_name)

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
        params = dict(self.widget_params, attrs=widget_attrs)
        return widget(**params)

    def get_form_field_params(self, **kwargs):
        params = super().get_form_field_params(**kwargs)
        self.set_params_choices(params)
        if params.get("help_text") is None and self.input_type not in [
            "checkbox",
            "checkboxinline",
        ]:
            params["help_text"] = _(
                "Use CTRL+click to select/deselect multiple choices"
            )
        return params

    def extract_params(self, request_get_data):
        self.value = request_get_data.getlist(self.input_name + self.listing.suffix)


class ForeignKeyFilter(Filter):
    form_field_class = forms.ChoiceField

    def get_form_field_widget(self, field_class, **kwargs):
        widget_attrs = HTMLAttributes(self.widget_attrs)
        widget = forms.Select
        widget_attrs.add("class", self.theme_form_select_widget_class)
        params = dict(self.widget_params, attrs=widget_attrs)
        return widget(**params)

    def get_choices_order(self):
        return self.order_by

    def get_related_qs(self):
        if self.queryset is not None:
            return self.queryset
        related_model = self.listing.model
        for f_name in self.filter_key.split("__"):
            related_model = related_model._meta.get_field(f_name).related_model
        qs = related_model.objects.all()
        order_by = self.get_choices_order()
        if order_by:
            qs = qs.order_by(order_by)
        return qs

    def get_form_field_params(self, **kwargs):
        params = super().get_form_field_params(**kwargs)
        self.set_params_choices(params)
        choices = [("", self.no_choice_msg)]
        choices += [(obj.pk, self.format_label(obj)) for obj in self.get_related_qs()]
        params["choices"] = choices
        return params


class MultipleForeignKeyFilter(Filter):
    form_field_class = forms.ModelMultipleChoiceField

    def get_form_field_widget(self, field_class, **kwargs):
        widget_attrs = HTMLAttributes(self.widget_attrs)
        widget = forms.SelectMultiple
        widget_attrs.add("class", self.theme_form_select_widget_class)
        params = dict(self.widget_params, attrs=widget_attrs)
        return widget(**params)

    def get_form_field_params(self, **kwargs):
        params = super().get_form_field_params(**kwargs)
        params["queryset"] = self.queryset
        return params


class AutocompleteForeignKeyFilter(Filter):
    form_field_class = forms.ModelChoiceField
    widget_class = autocomplete.ModelSelect2

    def get_form_field_params(self, **kwargs):
        params = super().get_form_field_params(**kwargs)
        params["required"] = False
        if self.queryset is not None:
            params["queryset"] = self.queryset
        else:
            related_model = self.listing.model
            for f_name in self.filter_key.split("__"):
                if f_name == "in":
                    break
                related_model = related_model._meta.get_field(f_name).related_model
            params["queryset"] = related_model.objects.all()
        return params

    def get_form_field_widget(self, field_class, **kwargs):
        self.listing.need_media_for("autocomplete")
        widget_attrs = HTMLAttributes(self.widget_attrs)
        widget_attrs.add("class", self.theme_form_select_widget_class)
        if "data-placeholder" not in widget_attrs:
            widget_attrs["data-placeholder"] = _("Select a value...")
        widget = self.widget_class
        if self.url is None:
            raise InvalidFilters(
                f"Please specify the url name to autocomplete view for {self.name}"
            )
        if widget_attrs.get("data-html") is not False:
            widget_attrs["data-html"] = True
        params = dict(self.widget_params, url=self.url, attrs=widget_attrs)
        return widget(**params)


class AutocompleteMultipleForeignKeyFilter(AutocompleteForeignKeyFilter):
    form_field_class = forms.ModelMultipleChoiceField
    widget_class = autocomplete.ModelSelect2Multiple
