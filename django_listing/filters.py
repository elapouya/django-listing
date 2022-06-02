#
# Created : 2018-04-04
#
# @author: Eric Lapouyade
#

from django.db import models
from django import forms
from django.template import loader
from django.utils.translation import gettext_lazy, pgettext_lazy
from django.utils.translation import gettext as _
import copy
import re
from .context import RenderContext
from .html_attributes import HTMLAttributes
from .exceptions import InvalidFilters
from .utils import init_dicts_from_class


__all__ = ['FILTERS_PARAMS_KEYS', 'FILTER_QUERYSTRING_PREFIX', 'Filters',
           'Filter', 'IntegerFilter', 'ChoiceFilter', 'MultipleChoiceFilter',
           'DateFilter', 'DateTimeFilter', 'TimeFilter']

# Declare keys only for "Filters" object
FILTERS_KEYS = {
    'form_reset_label', 'form_submit_label', 'form_template_name',
    'form_layout', 'form_attrs', 'form_buttons',
}

# Declare keys for "Filter" object (not "Filters" with an ending 's')
FILTERS_PARAMS_KEYS = {
    'name', 'filter_key', 'input_type', 'widget_attrs', 'model_field',
    'no_choice_msg',
}

# Declare keys for django form fields
FILTERS_FORM_FIELD_KEYS = {
    'max_length','min_length','strip','empty_value','label','required',
    'label_suffix', 'initial', 'widget', 'help_text', 'error_messages',
    'validators', 'localize', 'disabled',
}

FILTERS_PARAMS_KEYS.update(FILTERS_KEYS)
FILTERS_PARAMS_KEYS.update(FILTERS_FORM_FIELD_KEYS)
FILTER_QUERYSTRING_PREFIX = 'f_'


class FiltersBaseForm(forms.BaseForm):
    pass


class Filters(list):
    id = None
    listing=None
    form_reset_label = pgettext_lazy('Filters form', 'Reset')
    form_submit_label = pgettext_lazy('Filters form', 'Filter')
    form_template_name = 'django_listing/filters_form.html'
    form_layout = None
    form_buttons = 'reset,submit'

    def __init__(self, *filters, params=None):
        if params is None:
            params = {}
        self._params = params
        self._form = None
        self.name2filter = {}
        init_dicts_from_class(self, ['form_attrs'])
        super().__init__(filters)

    def get(self,name,default=None):
        return self.name2filter.get(name,default)

    def get_params(self):
        return self._params

    def names(self):
        return self.name2filter.keys()

    def select(self,select_filters_name=None, exclude_filters_name=None):
        if isinstance(select_filters_name,str):
            select_filters_name = map(str.strip,select_filters_name.split(','))
        if isinstance(exclude_filters_name,str):
            exclude_filters_name = map(str.strip,exclude_filters_name.split(','))
        select_filters_name = select_filters_name or self.names()
        exclude_filters_name = exclude_filters_name or []
        return [ self.get(c.strip())
                 for c in select_filters_name
                 if c not in exclude_filters_name ]

    def bind_to_listing(self, listing):
        filters = Filters(params=self._params)
        for k in FILTERS_KEYS:
            if hasattr(self,k):
                setattr(filters, k, getattr(self, k))
            listing_key = 'filters_' + k
            if hasattr(listing,listing_key):
                setattr(filters,k,getattr(listing,listing_key))
        if isinstance(self.form_layout, str):
            # transform layout string into list of lists of lists
            self.form_layout = re.sub(r'\s', '', self.form_layout)
            filters.form_layout = list(map(lambda s:list(map(
                lambda t:(t.split('|')+[None,None,None])[:4],s.split(','))),
                self.form_layout.split(';')))
        for filtr in self:
            if not isinstance(filtr,Filter):
                # understand, filtr is a string
                filtr = self.create_filter(filtr, listing)
            # ensure there is one filter instance per listing
            elif not filtr.listing:
                filtr = copy.deepcopy(filtr)
            if isinstance(filtr,Filter):
                filtr.bind_to_listing(listing)
                filters.append(filtr)
        filters.name2filter = {f.name : f for f in filters if isinstance(f,Filter)}
        filters.listing = listing
        # extract labels and endings from given layout
        if filters.form_layout:
            for row in filters.form_layout:
                for name, label, ending, input_type in row:
                    filtr = filters.name2filter.get(name)
                    if filtr:
                        if label:
                            filtr.label = label
                        if ending:
                            filtr.ending = ending
                        if input_type:
                            filtr.input_type = input_type
        if filters.form_layout is None:
            filters.form_layout = [ [[filtr.name,None,None,None]]
                                    for filtr in filters
                                    if isinstance(filtr,Filter) ]
        fbuttons = filters.form_buttons
        if isinstance(fbuttons,str):
            filters.form_buttons = list(map(str.strip,fbuttons.split(',')))
        return filters

    def datetimepicker_init(self):
        self.listing.need_media_for('datetimepicker')
        self.listing.add_onready_snippet(f"""
            $('#{self.id} .edit-datecolumn').datetimepicker({{timepicker:false, format:'{self.listing.datetimepicker_date_format}'}});
            $('#{self.id} .edit-datetimecolumn').datetimepicker({{format:'{self.listing.datetimepicker_datetime_format}'}});
            $('#{self.id} .edit-timecolumn').datetimepicker({{datepicker:false, format:'{self.listing.datetimepicker_time_format}'}});
            """)

    def create_filter(self, name, listing):
        if isinstance(name,str):
            model_attr_name, *_ = name.split('__')
            if issubclass(listing.model,models.Model):
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
            f.extract_params(request_get_data)

    def form(self):
        if not self._form:
            fields = { f.input_name + self.listing.suffix : f.create_form_field()
                       for f in self }
            form_class = type('FilterForm{}'.format(self.listing.suffix),
                              (FiltersBaseForm,),
                              {'base_fields': fields})
            self._form = form_class(self.listing.request.GET)
        return self._form

    def get_hiddens_html(self):
        query_fields = [ (FILTER_QUERYSTRING_PREFIX + f.name) for f in self ]
        return self.listing.get_hiddens_html(without=query_fields)

    def render_init(self,context):
        self.listing.manage_page_context(context)
        if not isinstance(self.form_attrs,HTMLAttributes):
            self.form_attrs = HTMLAttributes(self.form_attrs)
        self.form_attrs.add('class','listing-form')
        if self.listing.accept_ajax:
            self.form_attrs.add('class', 'django-filters-ajax')
        if 'id' not in self.form_attrs:
            self.form_attrs.add('id',
                                'filters-form{}'.format(self.listing.suffix))
        self.id = self.form_attrs['id']
        self.datetimepicker_init()

    def render_form(self, context):
        self.render_init(context)
        ctx = self.get_context()
        template = loader.get_template(self.form_template_name)
        out = template.render(ctx)
        return out

    def get_form_reset_url(self):
        query_fields = [ (FILTER_QUERYSTRING_PREFIX + f.name) for f in self]
        return self.listing.get_url(without=query_fields)

    def get_form_field(self,name):
        filter = self.get(name)
        if filter is None:
            raise InvalidFilters(
                _('Cannot find filter "{name}" definition').format(name=name)
            )
        return self.form()[filter.input_name + self.listing.suffix]

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
        FilterMeta.filter_classes.append((cls,cls.from_model_field_order))
        params_keys = cls.params_keys
        if params_keys:
            if isinstance(params_keys,str):
                params_keys = set(map(str.strip,params_keys.split(',')))
            FILTERS_PARAMS_KEYS.update(params_keys)
            FILTERS_PARAMS_KEYS.discard('')
        form_field_keys = cls.form_field_keys
        if form_field_keys:
            if isinstance(form_field_keys,str):
                form_field_keys = set(map(str.strip,form_field_keys.split(',')))
            FILTERS_FORM_FIELD_KEYS.update(form_field_keys)
            FILTERS_FORM_FIELD_KEYS.discard('')
            FILTERS_PARAMS_KEYS.update(FILTERS_FORM_FIELD_KEYS)
        return cls

    @classmethod
    def get_filter_classes(cls):
        return [ t[0] for t in sorted(cls.filter_classes,key=lambda x:x[1]) ]


class Filter(metaclass=FilterMeta):
    from_model_field_order = 100
    from_model_field_classes = ()
    form_field_class = forms.CharField
    form_field_keys = None
    params_keys = None
    name = None
    label = None
    value = None
    filter_key = None
    input_name = None
    input_type = None
    required = False
    listing = None
    widget_attrs = {'class': 'form-control'}
    no_choice_msg = gettext_lazy('- No filtering -')
    help_text = None

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        init_dicts_from_class(self, ['widget_attrs'])

    def bind_to_listing(self, listing):
        self.init(listing, *self.init_args, **self.init_kwargs)

    def set_listing(self, listing):
        self.listing = listing

    def init(self, listing, name=None, **kwargs):
        self.set_listing(listing)
        lsg = self.listing
        suffix = lsg.suffix
        if name:
            self.name = re.sub(r'\W','',name)
        self.set_kwargs(**kwargs)
        self.apply_template_kwargs()
        if self.filter_key is None:
            self.filter_key = self.name
        if self.input_name is None:
            self.input_name = FILTER_QUERYSTRING_PREFIX + self.name
        self.label = self.get_label()

    def get_label(self):
        label = self.label
        if label is None:
            label,*_ = self.name.split('__')
            label = label.replace('_',' ').title()
        return label

    def set_kwargs(self, **kwargs):
        # If filters_<filterclass>_<params> exists in listing attributes :
        # take is as a default value
        for k in FILTERS_PARAMS_KEYS:
            listing_key = 'filters_{}'.format(k)
            if hasattr(self.listing,listing_key):
                setattr(self,k,getattr(self.listing,listing_key))
        for k, v in kwargs.items():
            if k in FILTERS_PARAMS_KEYS:
                setattr(self,k,v)
        # if parameters given in filters : apply them
        for k, v in self.listing.filters.get_params().get(self.name,{}).items():
            if k in FILTERS_PARAMS_KEYS:
                setattr(self, k, v)
        # if parameters given in listing apply them to specified filter
        for k in FILTERS_PARAMS_KEYS:
            key = '{}{}__{}'.format(FILTER_QUERYSTRING_PREFIX,self.name,k)
            v = getattr(self.listing, key, None)
            if v is not None:
                setattr(self, k, v)

    def apply_template_kwargs(self):
        kwargs = self.listing.get_filter_kwargs(self.name)
        if kwargs:
            for k, v in kwargs.items():
                if k in FILTERS_PARAMS_KEYS:
                    if isinstance(v,dict):
                        prev_value = getattr(self,k,None)
                        if isinstance(prev_value,dict):
                            prev_value.update(v)
                            continue
                    setattr(self,k,v)

    @classmethod
    def from_model_field(cls, name, field):
        if field.__class__ in cls.from_model_field_classes:
            return cls(name, model_field=field, label=field.verbose_name)

    def get_form_field_params(self):
        params = { p:getattr(self,p) for p in FILTERS_FORM_FIELD_KEYS
                   if getattr(self,p,None) is not None }
        return params

    def get_form_field_class(self):
        return self.form_field_class

    def get_form_field_widget(self, field_class):
        return field_class.widget(attrs=self.widget_attrs)

    def create_form_field(self):
        cls = self.get_form_field_class()
        params = self.get_form_field_params()
        widget = self.get_form_field_widget(cls)
        field = cls(widget=widget, **params)
        return field

    def filter_queryset(self, qs, cleaned_data):
        if not self.value:
            return qs
        cleaned_value = cleaned_data.get(self.input_name + self.listing.suffix)
        return qs.filter(**{self.filter_key:cleaned_value})

    def filter_sequence(self, seq):
        if not self.value:
            return seq
        return filter(lambda rec:rec[self.filter_key]==self.value, seq)

    def extract_params(self, request_get_data):
        self.value = request_get_data.get(self.input_name + self.listing.suffix)

    def set_params_choices(self,params):
        if not params.get('choices'):
            if hasattr(self,'model_field'):
                params['choices'] = self.model_field.choices
            elif self.listing.model:
                try:
                    model = self.listing.model
                    params['choices'] = model._meta.get_field(self.name).choices
                except (models.FieldDoesNotExist, AttributeError):
                    raise InvalidFilters(_('Cannot find choices from model '
                        'for filter "{name}", Please specify the choices to '
                        'display').format(name=self.name))
            else:
                raise InvalidFilters(_('Please specify the choices to display '
                    'for filter "{name}"').format(name = self.name ))


class IntegerFilter(Filter):
    from_model_field_classes = (models.IntegerField,)
    form_field_class = forms.IntegerField


class DateFilter(Filter):
    from_model_field_classes = (models.DateField,)
    form_field_class = forms.DateField
    widget_attrs = {'class': 'form-control edit-datecolumn'}


class DateTimeFilter(Filter):
    from_model_field_classes = (models.DateTimeField,)
    form_field_class = forms.DateTimeField
    widget_attrs = {'class': 'form-control edit-datetimecolumn'}


class TimeFilter(Filter):
    from_model_field_classes = (models.TimeField,)
    form_field_class = forms.TimeField
    widget_attrs = {'class': 'form-control edit-timecolumn'}


class ChoiceFilter(Filter):
    form_field_class = forms.ChoiceField
    form_field_keys = 'choices'

    @classmethod
    def from_model_field(cls, name, field):
        choices = getattr(field, 'choices', None)
        if choices:
            return cls(name, model_field=field, label=field.verbose_name)

    def get_form_field_widget(self, field_class):
        if self.input_type == 'radio':
            return forms.RadioSelect(
                attrs={'class':'multiple-radios'})
        elif self.input_type == 'radioinline':
            return forms.RadioSelect(
                attrs={'class':'multiple-radios inline'})
        return super().get_form_field_widget(field_class)

    def get_form_field_params(self):
        params = super().get_form_field_params()
        self.set_params_choices(params)
        params['choices'] = [ ('',self.no_choice_msg) ] + \
                            list(params['choices'])
        return params


class MultipleChoiceFilter(Filter):
    form_field_class = forms.MultipleChoiceField
    form_field_keys = 'choices'
    from_model_field_order = 90
    # 90 < 100 (default) means it will consider MultipleChoiceFilter before
    # ChoiceFilter when searching the right filter for a model field.

    def init(self, listing, name=None, **kwargs):
        super().init(listing, name, **kwargs)
        if not self.filter_key.endswith('__in'):
            self.filter_key += '__in'

    @classmethod
    def from_model_field(cls, name, field):
        choices = getattr(field, 'choices', None)
        if choices and name.endswith('__in'):
            return cls(name, model_field=field, label=field.verbose_name)

    def get_form_field_widget(self, field_class):
        if self.input_type == 'checkbox':
            return forms.CheckboxSelectMultiple(
                attrs={'class':'multiple-checkboxes'})
        elif self.input_type == 'checkboxinline':
            return forms.CheckboxSelectMultiple(
                attrs={'class':'multiple-checkboxes inline'})
        return super().get_form_field_widget(field_class)

    def get_form_field_params(self):
        params = super().get_form_field_params()
        self.set_params_choices(params)
        if ( params.get('help_text') is None and
             self.input_type not in ['checkbox', 'checkboxinline']):
            params['help_text'] = _(
                'Use CTRL+click to select/deselect multiple choices')
        return params

    def extract_params(self, request_get_data):
        self.value = request_get_data.getlist(self.input_name+self.listing.suffix)
