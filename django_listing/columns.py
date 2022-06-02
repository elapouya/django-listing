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
from django.db import models
from django.forms import widgets
from django.template.defaultfilters import filesizeformat
from django.utils import formats
from django.utils.encoding import force_str
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext
from django.utils.dateparse import parse_datetime

from .aggregations import AggregationMeta, Aggregation
from .context import RenderContext
from .exceptions import *
from .html_attributes import HTMLAttributes
from .record import cache_in_record
from .utils import init_dicts_from_class
from .app_settings import app_settings

__all__ = ['COLUMNS_PARAMS_KEYS', 'Columns', 'ModelColumns', 'SequenceColumns',
           'Column', 'BooleanColumn', 'CheckboxColumn', 'ChoiceColumn',
           'ManyColumn', 'DateColumn', 'DateTimeColumn', 'TimeColumn',
           'LinkColumn', 'TotalColumn', 'AvgColumn', 'MaxColumn', 'MinColumn',
           'MultipleChoiceColumn','ButtonColumn','InputColumn', 'FileSizeColumn',
           'SelectColumn', 'ForeignKeyColumn', 'LinkObjectColumn', 'ListingMethodRef',
           'ButtonLinkColumn', 'COLUMNS_FORM_FIELD_KEYS', 'JsonDateTimeColumn', ]

COLUMNS_PARAMS_KEYS = {
    'name', 'header', 'footer', 'data_key', 'cell_edit_tpl',
    'cell_tpl', 'cell_attrs', 'value_tpl', 'cell_value', 'label',
    'header_tpl', 'header_sortable_tpl',
    'footer_tpl', 'footer_value_tpl', 'sort_key', 'sortable', 'header_attrs',
    'footer_attrs', 'ascending_by_default', 'model_field',
    'editable', 'default_value', 'form_field_class', 'form_field_widget_class',
    'default_footer_value', 'aggregation', 'date_format', 'datetime_format',
    'time_format', 'input_type', 'theme_header_class', 'theme_cell_class',
    'theme_footer_class', 'theme_header_icon', 'widget_attrs',
    'theme_form_widget_class','theme_button_class','no_choice_msg',
}

COLUMNS_FORM_FIELD_KEYS = {
    'max_length','min_length','strip','empty_value','label','required',
    'label_suffix', 'initial', 'widget', 'help_text', 'error_messages',
    'validators', 'localize', 'disabled','input_formats','min_value',
    'max_value',
}


class ListingMethodRef:
    """ Helper to reference a Listing method in column.cell_value instead of a lambda"""
    def __init__(self, method_name):
        self.method_name = method_name

    def __call__(self, listing, *args, **kwargs):
        method = getattr(listing, self.method_name)
        return method(*args, **kwargs)


class Columns(list):
    def __init__(self, *cols, params=None):
        if params is None:
            params = {}
        self._params = params
        self.name2col = {}
        if cols:
            if isinstance(cols[0],(list,tuple)):
                cols = cols[0]
            elif isinstance(cols[0],GeneratorType):
                cols = list(cols[0])
        super().__init__(cols)

    def get(self,name,default=None):
        return self.name2col.get(name,default)

    def exists(self,name):
        return name in self.name2col

    def get_model(self):
        return None

    def get_params(self):
        return self._params

    def names(self):
        return [ c.name for c in self ]

    def select(self,select_cols_name=None, exclude_cols_name=None):
        if isinstance(select_cols_name,str):
            select_cols_name = list(map(str.strip,select_cols_name.split(',')))
        if isinstance(exclude_cols_name,str):
            exclude_cols_name = list(map(str.strip,exclude_cols_name.split(',')))
        if select_cols_name is None:
            select_cols_name = self.names()
        exclude_cols_name = exclude_cols_name or []
        return [ self.get(c.strip())
                 for c in select_cols_name
                 if c not in exclude_cols_name and c in self.name2col ]

    def bind_to_listing(self, listing):
        cols = Columns(params=self._params)
        for i,col in enumerate(self):
            # check col is a Column instance
            if not isinstance(col,Column):
                raise InvalidColumn(
                    gettext('column {col_id} of listing {listing} is not '
                             'a Column instance (class = {colclass})')
                    .format(col_id=i, listing=listing.__class__.__name__,
                            colclass=col.__class__.__name__))
            # ensure there is one column instance per listing
            if not col.listing:
                col = copy.deepcopy(col)
            col.bind_to_listing(listing)
            cols.append(col)
        cols.name2col = { c.name : c for c in cols if isinstance(c,Column) }
        cols.listing = listing
        return cols

    def editing_init(self):
        for col in self:
            col.editing_init()


class ModelColumns(Columns):
    def __init__(self, model, *cols, params=None, listing=None,
                 link_object_columns=None, **kwargs):
        if params is None:
            params = {}
        if not link_object_columns:
            link_object_columns = ''
        if isinstance(link_object_columns, str):
            link_object_columns = set(map(str.strip,link_object_columns.split(',')))

        model_cols = []
        # when not yet initialized, column name is in init_args[0]
        name2col = OrderedDict( (c.name or c.init_args[0],c) for c in cols )
        for f in model._meta.get_fields():
            if not isinstance(f, (models.ManyToManyRel,models.ManyToOneRel)):
                header = getattr(f,'verbose_name',f.name)
                if f.name in name2col:
                    col = name2col.pop(f.name)
                    model_cols.append(col)
                else:
                    if f.name in link_object_columns:
                        model_cols.append(LinkObjectColumn(
                            f.name, model_field=f,
                            header=header,**kwargs)
                        )
                    else:
                        model_cols.append(self.create_column(
                            f,header=header,
                            **kwargs)
                        )

        super().__init__(*(model_cols + list(name2col.values())))
        if listing:
            for col in self:
                col.set_listing(listing)
        self._model = model
        self._params = params

    @classmethod
    def create_column_name(cls, listing, name, **kwargs):
        model = listing.model
        if model:
            model_field = model._meta.get_field(name)
            if not model_field:
                return None
            header = getattr(model_field, 'verbose_name', model_field.name)
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
                col = col_class.from_model_field(field,**kwargs)
                if col:
                    return col
        return Column(field_name, model_field=field, **kwargs)


class SequenceColumns(Columns):
    def __init__(self, seq, columns_headers=None, params=None,
                 listing=None, **kwargs):
        if params is None:
            params = {}
        first_row = seq[0]
        if not isinstance(first_row, (dict, list, tuple)):
            for i,v in enumerate(seq):
                seq[i] = [seq[i]]
            first_row = seq[0]
        cols = []
        if isinstance(first_row, dict):
            if not isinstance(columns_headers,dict):
                columns_headers={}
            for k,v in first_row.items():
                header = columns_headers.get(k)
                cols.append(self.create_column(v, k, header=header, **kwargs))
        elif isinstance(first_row, (list, tuple)):
            if not isinstance(columns_headers,(list, tuple)):
                columns_headers=()
            for i,v in enumerate(first_row):
                if i < len(columns_headers) and columns_headers[i]:
                    header = columns_headers[i]
                else:
                    header = 'Column{}'.format(i + 1)
                cols.append(self.create_column(v, header=header,
                                               data_key=i, **kwargs))
        super().__init__(*cols)
        if listing:
            for col in self:
                col.set_listing(listing)
        self._params = params

    @classmethod
    def create_column(cls, value, name=None,
                      header=None, data_key=None, **kwargs):
        if isinstance(value,datetime.datetime):
            return DateTimeColumn(name, header=header,
                                  data_key=data_key, **kwargs)
        elif isinstance(value,datetime.date):
            return DateColumn(name, header=header,data_key=data_key, **kwargs)
        return Column(name, header=header,data_key=data_key, **kwargs)


class ColumnMeta(type):
    column_classes = []

    def __new__(mcs, name, bases, attrs):
        cls = super(ColumnMeta, mcs).__new__(mcs, name, bases, attrs)
        ColumnMeta.column_classes.append((cls,cls.from_model_field_order))
        params_keys = cls.params_keys
        if isinstance(params_keys,str):
            params_keys = set(map(str.strip,params_keys.split(',')))
        COLUMNS_PARAMS_KEYS.update(params_keys)
        COLUMNS_PARAMS_KEYS.discard('')
        form_field_keys = cls.form_field_keys
        if form_field_keys:
            if isinstance(form_field_keys,str):
                form_field_keys = set(map(str.strip,form_field_keys.split(',')))
            COLUMNS_FORM_FIELD_KEYS.update(form_field_keys)
            COLUMNS_FORM_FIELD_KEYS.discard('')
            COLUMNS_PARAMS_KEYS.update(COLUMNS_FORM_FIELD_KEYS)
        return cls

    @classmethod
    def get_column_classes(cls):
        return [ t[0] for t in sorted(cls.column_classes,key=lambda x:x[1]) ]


class Column(metaclass=ColumnMeta):
    aggregation = None
    ascending_by_default = True
    can_edit = False
    cell_tpl = None
    cell_edit_tpl = None
    cell_value = None
    data_key = None
    default_footer_value = ''
    default_value = '-'
    editable = None
    editing = False
    footer = None
    footer_tpl = None
    footer_value_tpl = None
    form_field_class = forms.CharField
    form_field_widget_class = None
    form_field_keys = None
    from_model_field_classes = []
    from_model_field_order = 100
    header = None
    header_sortable_tpl = None
    header_tpl = None
    help_text = None
    input_type = None
    listing = None
    model_field = None
    name = None
    no_choice_msg = _('Please choose...')
    params_keys = ''
    sort_key = None
    sortable = True
    value_tpl = '{value}'

    theme_header_class = ''
    theme_cell_class = ''
    theme_footer_class = ''
    theme_form_widget_class = 'form-control form-control-sm'
    theme_button_class = 'btn btn-primary btn-sm'

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        init_dicts_from_class(self, ['cell_attrs', 'header_attrs', 'cell_attrs',
                                     'footer_attrs', 'widget_attrs'])

    def bind_to_listing(self, listing):
        self.init(listing, *self.init_args, **self.init_kwargs)

    def set_listing(self, listing):
        self.listing = listing

    def init(self, listing, name=None, **kwargs):
        self.set_listing(listing)
        header = kwargs.get('header')
        if name:
            self.name = re.sub(r'\W','',name)
        if self.name is None:
            if header:
                self.name = re.sub(r'\W', '',header.strip().replace(' ','_').lower())
            else:
                self.name = 'noname'
        self.set_kwargs(**kwargs)
        self.apply_template_kwargs()
        if self.data_key is None:
            self.data_key = self.name
        if self.sort_key is None:
            self.sort_key = self.data_key
        if isinstance(self.aggregation,str):
            self.aggregation = AggregationMeta.get_instance(self.aggregation,self)
        if isinstance(self.theme_header_class,str):
            self.theme_header_class = set(self.theme_header_class.split())
        if isinstance(self.theme_cell_class,str):
            self.theme_cell_class = set(self.theme_cell_class.split())
        if isinstance(self.theme_footer_class,str):
            self.theme_footer_class = set(self.theme_footer_class.split())
        if isinstance(self.theme_form_widget_class,str):
            self.theme_form_widget_class = set(self.theme_form_widget_class.split())
        if isinstance(self.theme_button_class,str):
            self.theme_button_class = set(self.theme_button_class.split())

    def render_init(self):
        pass

    def editing_init(self):
        # editable attribute can be set via 'editable_columns'
        # only if not already set in the final column class
        if self.editable is None and {'all',self.name} & self.listing.editable_columns:
            self.editable = True
        if {'all',self.name} & self.listing.editing_columns:
            self.editing = True
        self.can_edit = ( self.editable and self.editing and
                          self.listing.editable and self.listing.editing )

    def set_kwargs(self, **kwargs):
        # if parameters given in columns : apply them
        for k, v in self.listing.columns.get_params().get(self.name,{}).items():
            if k in COLUMNS_PARAMS_KEYS:
                setattr(self, k, v)
        for k in COLUMNS_PARAMS_KEYS | COLUMNS_FORM_FIELD_KEYS:
            listing_key = 'columns_{}'.format(k)
            if hasattr(self.listing,listing_key):
                setattr(self,k,getattr(self.listing,listing_key))
        # col__param has higher priority than columns_param,
        # so getting col__params after columns_params
        for k, v in self.listing.__class__.__dict__.items():
            start_key = f'{self.name}__'
            if k.startswith(start_key):
                setattr(self, k[len(start_key):], v)
        for k, v in kwargs.items():
            if k in COLUMNS_PARAMS_KEYS:
                setattr(self,k,v)

    def apply_template_kwargs(self):
        kwargs = self.listing.get_column_kwargs(self.name)
        if kwargs:
            for k, v in kwargs.items():
                if k in COLUMNS_PARAMS_KEYS:
                    if isinstance(v,dict):
                        prev_value = getattr(self,k,None)
                        if isinstance(prev_value,dict):
                            prev_value.update(v)
                            continue
                    setattr(self,k,v)

    @classmethod
    def from_model_field(cls, field, **kwargs):
        if field.__class__ in cls.from_model_field_classes:
            return cls(field.name, model_field=field, **kwargs)

    def get_cell_attrs(self, rec, ctx, value):
        cell_attrs = self.cell_attrs
        if callable(cell_attrs):
            cell_attrs = cell_attrs(rec, ctx, value)
        attrs = HTMLAttributes(cell_attrs)
        attrs.add('class', {'col-'+self.name,
                           'type-'+type(value).__name__,
                           'cls-'+self.__class__.__name__.lower()
                           } | self.theme_cell_class)
        return attrs

    def get_default_value(self, rec):
        return self.default_value

    # def get_raw_value(self, rec):
    #     return rec.get(self.data_key)

    @cache_in_record
    def get_cell_value(self, rec):
        if isinstance(self.cell_value, ListingMethodRef):
            value = self.cell_value(self.listing, self, rec)
        elif callable(self.cell_value):
            value = self.cell_value(self, rec)
        else:
            value = rec.get(self.data_key)
            if value is None:
                value = self.get_default_value(rec)
        return value

    def get_cell_exported_value(self,rec):
        val = self.get_cell_value(rec)
        if not isinstance(val,(int, float, datetime.datetime,
                               datetime.date,datetime.time)):
            return force_str(val)
        return val

    def render_form_field(self, rec):
        """Render a cell edit field when a listing is being edited"""

        # get the django form field (a formset form is attached to each record)
        # you get an instance of forms.CharField, forms.DateField etc...
        form_field = rec.get_form()[self.name]
        errors = form_field.errors
        if errors:
            html = ('<div class="form-field errors"><span class='
                     '"listing-icon-attention"></span>{errors}{form_field}</div>').format(
                     errors=errors, form_field=form_field)
        else:
            html = ('<div class="form-field">{form_field}</div>').format(
                    form_field=form_field)
        return html

    def get_cell_context(self, rec, value):
        if isinstance(value,str):
            value = conditional_escape(value)
        return RenderContext(self.listing.global_context,
                             rec.get_format_ctx(),
                             value,  # if value is a dict it will be merged (see RenderContext)
                             value=value,  # if value is not a dict it will have the key 'value' in the context
                             rec=rec,
                             listing=self.listing,
                             col=self)

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
            cell_tpl = self.cell_tpl
            value_tpl = self.get_value_tpl(rec, ctx, value)
        tpl = cell_tpl or '<td{attrs}>%s</td>'
        return tpl % value_tpl

    def render_cell(self,rec):
        value = self.get_cell_value(rec)
        ctx = self.get_cell_context(rec, value)
        ctx.attrs = self.get_cell_attrs(rec, ctx, value)
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
        if self.sortable:
            attrs.add('class',self.listing.theme_sortable_class)
            asc = self.listing.columns_sort_ascending.get(self.name)
            if asc is not None:
                attrs.add('class', self.listing.theme_sort_asc_class if asc else
                                   self.listing.theme_sort_desc_class)
        attrs.add('class', {'col-'+self.name} | self.theme_header_class)
        return attrs

    def get_header_value(self):
        if self.header:
            if callable(self.header):
                # call to lambda function with column and listing as arguments
                header_value = self.header(self,self.listing)
            else:
                header_value = self.header
        else:
            header_value = self.name.replace('_', ' ').title()
        return header_value

    def get_header_context(self):
        sort_url = None
        icon = None
        if self.sortable and self.listing.sortable:
            actual_ascending = self.listing.columns_sort_ascending.get(self.name)
            ascending = not self.ascending_by_default \
                        if actual_ascending is None \
                        else actual_ascending
            sort_param = '{}{}'.format('-' if ascending else '',self.name)
            if ( actual_ascending is not None
                 and actual_ascending != self.ascending_by_default
                 and self.listing.unsortable ):
                sort_url = self.listing.get_url(without='sort')
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
                icon = ' ' + icon
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
            col=self)

    def get_header_template(self, ctx):
        if ctx.sort_url:
            return self.header_sortable_tpl or (
                   '<th{attrs}><a class="listing-nav" href="{sort_url}">{value}'
                   '<span class="sorting{icon}"></span></a></th>')
        else:
            return self.header_tpl or '<th{attrs}>{value}</th>'

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
        attrs.add('class',{'col-'+self.name,
                           'type-'+type(value).__name__,
                           'cls-'+self.__class__.__name__.lower()
                           } | self.theme_footer_class )
        return attrs

    def get_footer_value(self):
        if callable(self.footer):
            # call to lambda function with column and listing as arguments
            footer_value = self.footer(self,self.listing)
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
            col=self)

    def get_footer_value_tpl(self, ctx, value):
        footer_value_tpl = self.footer_value_tpl or '{value}'
        if callable(footer_value_tpl):
            footer_value_tpl = footer_value_tpl(ctx, value)
        return footer_value_tpl

    def get_footer_template(self, ctx, value):
        return self.footer_tpl or '<td{attrs}>%s</td>' % \
                    self.get_footer_value_tpl(ctx, value)

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

    def get_form_field_params(self, have_empty_choice=False):
        params = { p:getattr(self,p) for p in COLUMNS_FORM_FIELD_KEYS
                   if getattr(self,p,None) is not None }
        return params

    def get_form_field_class(self):
        cls = self.form_field_class
        if isinstance(cls, str):
            cls = getattr(forms, cls, None)
            if cls is None:
                raise InvalidColumn(
                    gettext('{} is not a valid django forms field class')
                    .format(self.form_field_class))
        return cls

    def get_form_field_widget(self, field_class):
        cls = self.form_field_widget_class or field_class.widget
        if isinstance(cls, str):
            cls = getattr(widgets, cls, None)
            if cls is None:
                raise InvalidColumn(
                    gettext('{} is not a valid django forms widget class')
                    .format(self.form_field_widget_class))
        widget_attrs=HTMLAttributes(self.widget_attrs)
        widget_attrs.add('class',self.theme_form_widget_class)
        return cls(attrs=widget_attrs)

    def create_form_field(self, have_empty_choice=False):
        cls = self.get_form_field_class()
        params = self.get_form_field_params(have_empty_choice)
        widget = self.get_form_field_widget(cls)
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

    def set_params_choices(self,params):
        if not params.get('choices'):
            if getattr(self,'model_field',None):
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

class TextColumn(Column):
    from_model_field_classes = (models.TextField,)
    form_field_widget_class = widgets.Textarea
    widget_attrs = {'rows':'3'}


class BooleanColumn(Column):
    true_tpl = _('True')
    false_tpl = _('False')
    params_keys = 'true_tpl,false_tpl'
    from_model_field_classes = (models.BooleanField, models.NullBooleanField)
    form_field_class = forms.BooleanField
    required = False

    def get_value_tpl(self, rec, ctx, value):
        return self.true_tpl if value else self.false_tpl


class IntegerColumn(Column):
    from_model_field_classes = (models.IntegerField,)
    form_field_class = forms.IntegerField


class ChoiceColumn(Column):
    choices={}
    params_keys = 'choices'
    from_model_field_order = 50
    form_field_class = forms.ChoiceField

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        if not isinstance(self.choices,dict):
            self.choices = OrderedDict(self.choices)

    @classmethod
    def from_model_field(cls, field, **kwargs):
        if hasattr(field, 'choices') and field.choices:
            return ChoiceColumn(field.name,
                                model_field=field,
                                choices=OrderedDict(field.choices),
                                **kwargs)

    def get_value_tpl(self,rec, ctx, value):
        return self.choices.get(value,value)

    def get_form_field_params(self, have_empty_choice=False):
        params = super().get_form_field_params()
        self.set_params_choices(params)
        if have_empty_choice and self.input_type not in ('radio','radioinline'):
            params['choices'] = [ ('', self.no_choice_msg) ] + \
                                list(params['choices'])
        return params

    def get_form_field_widget(self, field_class):
        if self.input_type == 'radio':
            return forms.RadioSelect(
                attrs={'class':'multiple-radios'})
        elif self.input_type == 'radioinline':
            return forms.RadioSelect(
                attrs={'class':'multiple-radios inline'})
        return super().get_form_field_widget(field_class)


class MultipleChoiceColumn(Column):
    choices={}
    params_keys = 'choices'
    from_model_field_order = 90
    form_field_class = forms.MultipleChoiceField

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        if not isinstance(self.choices,dict):
            self.choices = OrderedDict(self.choices)

    @classmethod
    def from_model_field(cls, field, **kwargs):
        if hasattr(field, 'choices') and field.choices:
            return MultipleChoiceColumn(field.name,
                                model_field=field,
                                choices=OrderedDict(field.choices),
                                **kwargs)

    def get_cell_value(self,rec):
        value = super().get_cell_value(rec)
        return self.choices.get(value,value)

    def get_form_field_params(self, have_empty_choice=False):
        params = super().get_form_field_params()
        self.set_params_choices(params)
        if have_empty_choice and self.input_type not in ('checkbox','checkboxinline'):
            params['choices'] = [ ('', self.no_choice_msg) ] + \
                                list(params['choices'])
        return params

    def get_form_field_widget(self, field_class):
        if self.input_type == 'checkbox':
            return forms.CheckboxSelectMultiple(
                attrs={'class':'multiple-checkboxes'})
        elif self.input_type == 'checkboxinline':
            return forms.CheckboxSelectMultiple(
                attrs={'class':'multiple-checkboxes inline'})
        return super().get_form_field_widget(field_class)


class ManyColumn(Column):
    many_separator = ', '
    params_keys = 'many_separator,cell_map,cell_filter,cell_reduce'
    from_model_field_classes = (models.ManyToManyField,)
    editable = False

    def get_cell_value(self,rec):
        value = super().get_cell_value(rec)
        value = self.cell_filter(value)
        value = map(self.cell_map,value)
        value = self.cell_reduce(value)
        return value

    def cell_filter(self,value):
        if isinstance(value,models.Manager):
            value = value.all()
        return value

    def cell_map(self,value):
        return force_str(value)

    def cell_reduce(self,value):
        return self.many_separator.join(value)


class CheckboxColumn(Column):
    sortable = False

    def get_value_tpl(self,rec, ctx, value):
        attrs = HTMLAttributes(self.widget_attrs)
        attrs.add('type','checkbox')
        attrs.add('name',self.name)
        # If a value is set at definition time : take it
        # otherwise : take cell value
        if self.cell_value is not None:
            value = self.cell_value
        if value:
            attrs.set('checked')
        return '<input{}>'.format(attrs)


class ButtonColumn(Column):
    label = 'Button'
    sortable = False

    def get_value_tpl(self,rec, ctx, value):
        attrs = HTMLAttributes(self.widget_attrs)
        attrs.add('type','button')
        attrs.add('name',self.name)
        attrs.add('class',self.theme_button_class)
        return '<button{attrs}>{label}</button>'.format(
            attrs=attrs,label=conditional_escape(self.label))


class SelectColumn(Column):
    sortable = False
    choices={}

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        if not isinstance(self.choices,dict):
            self.choices = OrderedDict(self.choices)

    def get_value_tpl(self,rec, ctx, value):
        attrs = HTMLAttributes(self.widget_attrs)
        attrs.add('name',self.name)
        attrs.add('class',self.theme_form_widget_class)
        # If a value is set at definition time : take it
        # otherwise : take cell value
        if self.cell_value is not None:
            value = self.cell_value
        options = [ '<option value="{key}"{sel}>{val}</option>\n'
            .format( key=k,
                     val=conditional_escape(v),
                     sel=' selected' if value==k else '')
            for k,v in self.choices.items() ]
        return '<select{}>\n{}</select>'.format(attrs, options)


class InputColumn(Column):
    widget_attrs = {'type':'text'}
    sortable = False

    def get_value_tpl(self,rec, ctx, value):
        attrs = HTMLAttributes(self.widget_attrs)
        attrs.add('name',self.name)
        attrs.add('class',self.theme_form_widget_class)
        return '<input{attrs}>'.format(attrs=attrs)


class DateColumn(Column):
    date_format = settings.DATE_FORMAT
    params_keys = 'date_format'
    from_model_field_classes = (models.DateField,)
    form_field_class = forms.DateField
    widget_attrs = {'class': 'edit-datecolumn', 'autocomplete':'off'}

    def get_cell_value(self,rec):
        value = super().get_cell_value(rec)
        if isinstance(value, datetime.date):
            return formats.date_format(value, self.date_format)
        return value


class DateTimeColumn(Column):
    datetime_format = settings.DATETIME_FORMAT
    params_keys = 'datetime_format'
    from_model_field_classes = (models.DateTimeField,)
    widget_attrs = {'class': 'edit-datetimecolumn', 'autocomplete':'off'}

    def get_cell_value(self,rec):
        value = super().get_cell_value(rec)
        if isinstance(value, datetime.date):  # date also match datetime
            return formats.date_format(value, self.datetime_format)
        return value


class JsonDateTimeColumn(Column):
    datetime_format = settings.DATETIME_FORMAT
    params_keys = 'datetime_format'

    def get_cell_value(self,rec):
        value = super().get_cell_value(rec)
        if isinstance(value, str):
            value = parse_datetime(value) or value  # convert json date to datetime object
        if isinstance(value, datetime.date):  # date also match datetime
            return formats.date_format(value, self.datetime_format)
        return value


class FileSizeColumn(Column):
    def get_cell_value(self,rec):
        value = super().get_cell_value(rec)
        if isinstance(value, (int, float)):
            return filesizeformat(value)
        return value


class TimeColumn(Column):
    time_format = settings.TIME_FORMAT
    params_keys = 'time_format'
    from_model_field_classes = (models.TimeField,)
    widget_attrs = {'class': 'edit-timecolumn', 'autocomplete':'off'}

    def get_cell_value(self, rec):
        value = super().get_cell_value(rec)
        if isinstance(value, datetime.date):  # date also match datetime
            return formats.time_format(value, self.time_format)
        return value


class LinkColumn(Column):
    params_keys = 'link_attrs,href_tpl,no_link'
    href_tpl = None
    no_link = False
    link_attrs = None
    cell_tpl = '<td{attrs}><a{link_attrs}>%s</a></td>'
    cell_edit_tpl = '<td{attrs}>%s</td>'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def get_href(self,rec, ctx, value):
        href_tpl = self.get_href_tpl(rec, value)
        if isinstance(href_tpl, str):
            return href_tpl.format(**ctx)
        return None

    def get_cell_context(self, rec, value):
        ctx = super().get_cell_context(rec, value)
        ctx.link_attrs = self.get_link_attrs(rec, value)
        if not self.no_link:
            ctx.link_attrs.add('href', self.get_href(rec, ctx, value))
        return ctx


class ButtonLinkColumn(LinkColumn):
    label = 'Button'

    def get_link_attrs(self, rec, value):
        attrs = super().get_link_attrs(rec, value)
        attrs.add('class', self.theme_button_class)
        return attrs

    def get_cell_value(self, rec):
        value = mark_safe(self.label)
        return value


class URLColumn(LinkColumn):
    href_tpl = '{value}'
    from_model_field_classes = (models.URLField,)
    form_field_widget_class = widgets.URLInput
    params_keys = 'remove_proto'
    remove_proto = True

    def get_cell_context(self, rec, value):
        ctx = super().get_cell_context(rec, value)
        if self.remove_proto and not self.can_edit:
            ctx.value = re.sub('^.*?//','',ctx.value)
        return ctx


class EmailColumn(LinkColumn):
    href_tpl = 'mailto:{value}'
    from_model_field_classes = (models.EmailField,)
    form_field_widget_class = widgets.EmailInput


class LinkObjectColumn(LinkColumn):
    editable = False

    def get_href(self, rec, ctx, value):
        return rec.get_href()


class ForeignKeyColumn(LinkColumn):
    from_model_field_classes = (models.ForeignKey,)
    params_keys = 'no_foreignkey_link'
    no_foreignkey_link = False
    editable = False

    def get_href(self, rec, ctx, value):
        if self.no_foreignkey_link:
            return None
        if self.href_tpl:
            return super().get_href(rec, ctx, value)
        try:
            return rec[self.name].get_absolute_url()
        except (IndexError, AttributeError):
            return super().get_href(rec, ctx, value)


class FileColumn(LinkColumn):
    from_model_field_classes = (models.FileField,)
    form_field_class = forms.FileField
    params_keys = 'check_file, path_tpl, no_file_link'
    check_file = True
    no_file_link = False
    path_tpl = '{MEDIA_ROOT}/{value.name}'

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
            storage = getattr(value, 'storage', None)
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
                ctx.link_attrs.add('class', 'missing')
        return url


class ComputedColumnMixin:
    editable = False
    sortable = False

    def get_row_numeric_values(self,rec):
        values = []
        for col in self.listing.selected_columns:
            if not isinstance(col, ComputedColumnMixin):
                value = col.get_cell_value(rec)
                if isinstance(value, (int, float)):
                    values.append(value)
        return values


class TotalColumn(ComputedColumnMixin, Column):
    name = 'cc_total'  # 'cc' for computed column
    header = _('Total')
    aggregation = 'sum'  # aggregate rows
    footer_tpl = _('<td{attrs}>Grand Total:<br>{value}</td>')

    @cache_in_record
    def get_cell_value(self,rec):
        return sum(self.get_row_numeric_values(rec))  # aggregate columns


class MinColumn(ComputedColumnMixin, Column):
    name = 'cc_min_value'
    header = _('Min')
    aggregation = 'min'
    footer_tpl = _('<td{attrs}>Overall Min:<br>{value}</td>')

    def get_cell_value(self,rec):
        return min(self.get_row_numeric_values(rec))


class MaxColumn(ComputedColumnMixin, Column):
    name = 'cc_max_value'
    header = _('Max')
    aggregation = 'max'
    footer_tpl = _('<td{attrs}>Overall Max:<br>{value}</td>')

    def get_cell_value(self,rec):
        return max(self.get_row_numeric_values(rec))


class AvgColumn(ComputedColumnMixin, Column):
    params_keys = 'precision, footer_precision'
    name = 'cc_average'
    header = _('Average')
    precision = 2
    footer_precision = 2
    value_tpl = '{value:.{col.precision}f}'
    aggregation = 'avg'
    footer_tpl = _('<td{attrs}>Overall avg:<br>{value:.{col.footer_precision}f}</td>')

    def get_cell_value(self,rec):
        values = self.get_row_numeric_values(rec)
        if values:
            return sum(values)/len(values)
        return self.default_value


class SelectionColumn(Column):
    sortable = False
    theme_header_icon = 'listing-icon-ok'
    header_tpl = '<th{attrs}><span class={col.theme_header_icon}></span></th>'

    def get_cell_context(self, rec, value):
        context = super().get_cell_context(rec, value)
        context['selection_value'] = rec.get(self.listing.selection_key)
        context['checked'] = ' checked' if rec.is_selected() else ''
        return context

    def get_value_tpl(self, rec, ctx, value):
        if self.listing.selection_multiple:
            return '<input type="checkbox" name="selected_rows{listing.suffix}" class="selection-box" value="{selection_value}"{checked}>'
        else:
            return '<input type="radio" name="selected_rows{listing.suffix}" class="selection-box" value="{selection_value}"{checked}>'
