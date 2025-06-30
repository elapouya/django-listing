#
# Created : 2018-02-09
#
# @author: Eric Lapouyade
#
import base64
import collections
import os
import re
import types
from urllib.parse import quote_plus

from django.core.exceptions import FieldDoesNotExist
from django.core.serializers.json import Serializer
from django.db import models
from django.db.models import F, Model
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from . import FILTER_QUERYSTRING_PREFIX
from .exceptions import *
from .utils import to_js_timestamp

__all__ = [
    "RecordManager",
    "Record",
    "cache_in_record",
    "object_serializer",
    "FORM_LABEL_METHOD_NAME",
]


FORM_LABEL_METHOD_NAME = "get_form_label"


def cache_in_record(value_func):
    def cached_value_func(self, rec):
        cached, value = rec.get_cached_cell_value(self)
        if not cached:
            value = value_func(self, rec)
            rec.set_cached_cell_value(self, value)
        return value

    return cached_value_func


class SequenceItem:
    def __init__(self, pk, obj):
        self.pk = pk
        self.obj = obj


class ObjectSerializer(Serializer):
    def serialize(self, *args, **kwargs):
        self.additional_data = kwargs.pop("additional_data", None)
        self.form_data = kwargs.pop("form_data", None)
        return super().serialize(*args, **kwargs)

    def start_serialization(self):
        self._init_options()

    def end_serialization(self):
        pass

    def get_dump_object(self, obj):
        data = {"fields": self._current}
        data["fields"][obj._meta.pk.attname] = obj.pk
        if self.additional_data:
            data["data"] = self.additional_data
        if self.form_data:
            data["formfields"] = self.form_data
        return data


object_serializer = ObjectSerializer()


# Records are always bound to a listing instance
class RecordManager:
    def __init__(self, listing):
        self.listing = listing
        self._records = None

    def get_all(self):
        # used only for sequences (and short sequences please !)
        lsg = self.listing
        if isinstance(lsg.data, QuerySet):
            raise InvalidListing(
                _(
                    "Getting all records is only supported on "
                    "SMALL sequence data, not on Django querysets"
                )
            )
        if not hasattr(lsg, "_all_records"):
            lsg._all_records = [Record(lsg, rec, i) for i, rec in enumerate(lsg.data)]
        return lsg._all_records

    def get_first_obj(self):
        if not hasattr(self, "_first_obj"):
            qs = self.get_objs_from_queryset()
            self._first_obj = qs.first()
        return self._first_obj

    def get_last_obj(self):
        if not hasattr(self, "_last_obj"):
            qs = self.get_objs_from_queryset()
            self._last_obj = qs.last()
        return self._last_obj

    def clear_first_last_cache(self):
        if hasattr(self, "_first_obj"):
            delattr(self, "_first_obj")
        if hasattr(self, "_last_obj"):
            delattr(self, "_last_obj")

    def get_obj(self, **kwargs):
        lsg = self.listing
        if isinstance(lsg.data, QuerySet):
            qs = self.get_objs_from_queryset()
            try:
                return qs.get(**kwargs)
            except qs.DoesNotExist:
                return None
        else:
            # actually work only with 'id' or 'pk'
            pk = kwargs.get("pk")
            if pk is None:
                pk = kwargs.get("id")
            if pk is None:
                return None
            return self.get_objs_from_sequence()[pk].obj

    def get_unfiltered_count(self):
        data = self.listing.data
        if isinstance(data, QuerySet):
            return data.count()
        else:
            return len(data)

    def get_rec(self, **kwargs):
        obj = self.get_obj(**kwargs)
        if obj is None:
            return None
        return Record(self.listing, obj)

    def move_obj_order(self, obj, field, delta):
        qs = self.get_objs_from_queryset()
        obj_order = getattr(obj, field)
        if not isinstance(obj_order, int):
            raise ListingException(
                _(
                    'field "{field}" must be an integer, please choose the '
                    "correct field that will be used to change object ordering"
                ).format(field=field)
            )
        new_order = obj_order + delta
        if delta < 0:
            qs = qs.filter(**{f"{field}__gte": new_order, f"{field}__lt": obj_order})
            qs.update(**{field: F(field) + 1})
            setattr(obj, field, new_order)
            obj.save()
            self.clear_first_last_cache()
        elif delta > 0:
            qs = qs.filter(**{f"{field}__gt": obj_order, f"{field}__lte": new_order})
            qs.update(**{field: F(field) - 1})
            setattr(obj, field, new_order)
            obj.save()
            self.clear_first_last_cache()

    def compute_current_page_records(self):
        lsg = self.listing
        if not isinstance(lsg.data, (collections.abc.Sequence, QuerySet)):
            raise InvalidData(_("Listing data must be a sequence or a QuerySet."))
        if isinstance(lsg.data, QuerySet):
            objs = self.get_objs_from_queryset()
        else:
            objs = self.get_objs_from_sequence()

        per_page = int(lsg.per_page)
        if per_page <= 0 or per_page > lsg.per_page_max:
            per_page = lsg.per_page_max
        lsg.paginator = lsg.paginator_class(
            lsg, objs, per_page, lsg.orphans, lsg.allow_empty_first_page
        )
        lsg.current_page = lsg.paginator.get_page(lsg.page or 1)
        if lsg.editable and lsg.editing:
            self.bind_formset()

    def group_by_model_field_map(self, records, col, model, field):
        try:
            if "__" in field:
                # if field is "aa__bb__cc"
                # then left = aa and right == bb__cc
                left, right = re.match(r"^(.*?)(?:__)(.*?)$", field).groups()
                model_field = model._meta.get_field(left)
                if model_field.__class__.__name__ == "ForeignKey":
                    # recurse to the right part of the field
                    self.group_by_model_field_map(
                        records, col, model_field.related_model, right
                    )
            else:
                model_field = model._meta.get_field(field)
                if model_field.__class__.__name__ == "ForeignKey":
                    # As it is a group by queryset, ForeignKey's does not give object
                    # But only their PK's, so translating that into objects...
                    rec_key = col.data_key
                    pks = [rec.get(rec_key) for rec in records]
                    objs = model_field.related_model.objects.filter(pk__in=pks)
                    pk2obj = {obj.pk: obj for obj in objs}
                    for rec in records:
                        rec.set(col.data_key, pk2obj.get(rec.get(rec_key)))
        except FieldDoesNotExist:
            pass

    def group_by_foreignkey_object_map(self, records):
        lsg = self.listing
        if lsg.gb_cols:
            # Remap col where data_key is not part of the main model
            for col in lsg.columns:
                self.group_by_model_field_map(records, col, lsg.model, col.data_key)

    def current_page(self):
        if not self._records:
            lsg = self.listing
            self._records = [
                # lsg.current_page is set in RecordManager.compute_current_page_records()
                Record(lsg, obj, i)
                for i, obj in enumerate(lsg.current_page)
            ]
            self.group_by_foreignkey_object_map(self._records)
            lsg.update_page_records(self._records)
        return self._records

    def bind_formset(self):
        if self.listing.editing_row_pk:
            formset = self.listing.get_formset()
            for rec in self.current_page():
                if rec.pk == self.listing.editing_row_pk:
                    rec.set_form(formset[0])
        else:
            for rec, form in zip(self.current_page(), self.listing.get_formset()):
                rec.set_form(form)

    def export(self):
        lsg = self.listing
        export_data = self.get_export_data()
        export_data = self.order_data(export_data)
        if lsg.gb_cols:
            records = [Record(lsg, obj, i) for i, obj in enumerate(export_data)]
            self.group_by_foreignkey_object_map(records)
            for rec in records:
                yield rec
        else:
            for i, obj in enumerate(export_data):
                yield Record(lsg, obj, i)

    def get_export_data(self):
        data = self.listing.data
        if isinstance(data, QuerySet):
            export_data = self.filter_queryset(data)
        else:
            export_data = self.filter_sequence(data)
        return export_data

    def export_count(self):
        export_data = self.get_export_data()
        if isinstance(export_data, QuerySet):
            return export_data.count()
        else:
            return len(export_data)

    def filter_queryset(self, qs):
        if self.listing.filters:
            qs = self.listing.filters.filter_queryset(qs)
        return qs

    def get_filtered_queryset(self):
        qs = self.listing.data
        qs = self.filter_queryset(qs)
        return qs

    def order_data(self, data):
        if isinstance(data, QuerySet):
            data = self.order_queryset(data)
        else:
            data = self.order_sequence(data)
        return data

    def get_order_by(self):
        lsg = self.listing
        if lsg.force_order_by:
            if isinstance(lsg.force_order_by, str):
                order_by = (lsg.force_order_by,)
            else:
                order_by = lsg.force_order_by
        else:
            order_by = []
            if lsg.sort:
                for col_name in lsg.columns_sort_list:
                    order_prefix = "" if lsg.columns_sort_ascending[col_name] else "-"
                    col = lsg.columns.get(col_name)
                    if col:
                        if isinstance(col.sort_key, (tuple, list)):
                            for sort_key in col.sort_key:
                                order_by.append(order_prefix + sort_key)
                        else:
                            order_by.append(order_prefix + col.sort_key)
            # add a default sorting to avoid a Django 'UnorderedObjectListWarning'
            if not order_by:
                if lsg.gb_cols:
                    # if "group by" feature activated
                    order_by = lsg.gb_queryset_fields
                else:
                    order_by = ["pk"]
        return order_by

    def order_queryset(self, qs):
        order_by = self.get_order_by()
        return qs.order_by(*order_by)

    def order_sequence(self, data):
        # only manage one level sort
        order_by = self.get_order_by()
        if order_by:
            sort_key = order_by[0]
            sort_desc = sort_key[0] == "-"
            if sort_desc:
                sort_key = sort_key[1:]
            data = sorted(data, key=lambda x: x[sort_key], reverse=sort_desc)
        return data

    def get_objs_from_queryset(self):
        if not hasattr(self, "_queryset_objs"):
            qs = self.get_filtered_queryset()
            qs = self.order_queryset(qs)
            self._queryset_objs = qs
        return self._queryset_objs

    def filter_sequence(self, seq):
        if self.listing.filters:
            for filtr in self.listing.filters:
                seq = filtr.filter_sequence(seq)
        return seq

    def get_objs_from_sequence(self):
        lsg = self.listing
        seq = self.listing.data
        seq = self.filter_sequence(seq)
        if lsg.sort:
            for col_name in reversed(lsg.columns_sort_list):
                col = lsg.columns.get(col_name)
                if col:
                    sort_key = col.sort_key
                    if callable(sort_key):
                        key_func = sort_key
                    else:

                        def key_func(rec):
                            return rec[sort_key]

                    seq = sorted(
                        seq,
                        key=key_func,
                        reverse=not lsg.columns_sort_ascending[col_name],
                    )
        return [SequenceItem(i, obj) for i, obj in enumerate(seq)]


class Record:
    def __init__(self, listing, obj, index=0, form=None):
        self._listing = listing
        if isinstance(obj, SequenceItem):
            self._obj = obj.obj
            self.pk = obj.pk
        else:
            self._obj = obj
        self._index = index
        self._cell_values = {}
        self._form = form
        self._selected = False
        self._is_qs_first = False
        self._is_qs_last = False
        self._qs_record_index = 0
        if isinstance(self._obj, dict):
            self._format_ctx = self._obj
        elif isinstance(self._obj, (tuple, list)):
            self._format_ctx = {
                self._listing.columns[i].name: val for i, val in enumerate(self._obj)
            }
        else:
            self._format_ctx = vars(self._obj)
        cp = listing.current_page
        if cp:
            self._qs_record_index = cp.start_index() + index  # 1-based index
            if self._qs_record_index == 1:
                self._is_qs_first = True
            if self._qs_record_index == cp.paginator.count:
                self._is_qs_last = True

    def get_object(self):
        return self._obj

    def get_in_obj(self, key, default=None):
        return self._obj.get(key, default)

    def get_form_serialized_cols(self, obj, cols):
        data = {}
        for col in cols:
            if col.form_field_serialize_func:
                value = col.form_field_serialize_func(col, obj)
                if value is not None:
                    data[col.name] = value
                continue
            data_key = col.data_key
            from django_listing import MultiAutoCompleteColumn

            if isinstance(col, MultiAutoCompleteColumn):
                m2m_qs = getattr(obj, data_key).all()
                m2m_pks_labels = []
                for m2m_obj in m2m_qs:
                    form_label_func = getattr(m2m_obj, FORM_LABEL_METHOD_NAME, None)
                    if form_label_func is None:
                        form_label_func = lambda: str(m2m_obj)
                    m2m_pks_labels.append((m2m_obj.pk, form_label_func()))
                data[col.name] = m2m_pks_labels
                continue

            final_object = None
            if "__" in data_key:
                attr, foreign_attr = data_key.split("__", maxsplit=1)
                foreign_object = getattr(obj, attr, None)
                final_object = getattr(foreign_object, foreign_attr, None)
            else:
                final_object = getattr(obj, data_key, None)

            from django_listing import AutoCompleteColumn

            if (
                isinstance(final_object, int)
                # use class name to avoid cyclic import
                and isinstance(col, AutoCompleteColumn)
                and hasattr(col, "queryset")
            ):
                final_object = col.queryset.filter(pk=final_object).first()
            if final_object is None:
                continue
            if isinstance(final_object, Model):
                form_label_func = getattr(final_object, FORM_LABEL_METHOD_NAME, None)
                if form_label_func is None:
                    form_label_func = lambda: str(final_object)
                data[col.name] = (final_object.pk, form_label_func())
            else:
                # final_object is a value, not a model object
                data[col.name] = final_object
        return data

    def get_serialized_object(self, **kwargs):
        method = getattr(self._obj, "get_serialized_additional_data", None)
        additional_data = method() if method else {}
        form_data = {}
        if self._listing.form_serialize_cols:
            func = self._listing.form_serialize_cols_func
            if func is None:
                func = self.get_form_serialized_cols
            elif isinstance(func, str):
                func = getattr(self._obj.__class__, func)
            form_data.update(func(self._obj, self._listing.form_serialize_cols))
        if self._listing.form_no_autofill_cols:
            additional_data["no_autofill"] = self._listing.form_no_autofill_cols
        method = getattr(self._obj, "get_serialized_form_data", None)
        if method:
            form_data.update(method())
        serialized_obj = object_serializer.serialize(
            [self._obj],
            form_data=form_data,
            additional_data=additional_data,
            separators=(",", ":"),
            **kwargs,
        )
        return base64.b64encode(serialized_obj.encode()).decode()

    def is_first_qs_record(self):
        return self._is_qs_first

    def is_last_qs_record(self):
        return self._is_qs_last

    def is_selected(self):
        return self._selected

    def set_selected(self):
        self._selected = True

    def get_form(self):
        return self._form

    def set_form(self, form):
        self._form = form

    def get_cached_cell_value(self, col):
        if col in self._cell_values:
            return True, self._cell_values[col]
        return False, None

    def set_cached_cell_value(self, col, value):
        self._cell_values[col] = value

    def get_format_ctx(self):
        return self._format_ctx

    def format_str(self, str_to_format, extra_context=None):
        context = {**self._format_ctx}
        obj = self.get_object()
        context.update(rec_object=obj)
        if hasattr(obj, "get_absolute_url"):
            context.update(rec_object_url=obj.get_absolute_url())
        return mark_safe(str_to_format.format(**context))

    def get_listing(self):
        return self._listing

    def get_index(self):
        return self._index

    def do_filter_object(self, obj, filter_name, params):
        if filter_name == "urlencode" and isinstance(obj, str):
            obj = quote_plus(obj)
        elif filter_name == "replace":
            obj = obj.replace(*params)
        elif filter_name == "sub":
            obj = re.sub(*params, obj)
        elif filter_name == "basename":
            obj = os.path.basename(obj)
        elif filter_name == "js_timestamp":
            obj = to_js_timestamp(obj)
        else:
            func = getattr(obj, filter_name, None)
            if func is not None:
                obj = func()
        return obj

    def get_href(self):
        if hasattr(self._obj, "get_absolute_url"):
            return self._obj.get_absolute_url()

    def get_url(self, filters=None, **kwargs):
        if isinstance(filters, dict):
            for filter_name, rec_key in filters.items():
                fname = filter_name + self._listing.suffix
                val = self.get(rec_key)
                if isinstance(val, Model):
                    val = val.pk
                kwargs[f"{FILTER_QUERYSTRING_PREFIX}{fname}"] = val
        return self._listing.get_url(**kwargs)

    def get(self, key, default=None):
        obj = self._obj
        # case obj is a dict, try without splitting key (case group by)
        if isinstance(obj, dict) and key in obj:
            return obj.get(key)
        try:
            if isinstance(key, int):
                obj = obj[key]
            else:
                key, *filter_names = key.split("|", 1)
                for subkey in key.split("__"):
                    if "|" in subkey:
                        subkey, *filter_names = subkey.split("|", 1)
                    if subkey.isdigit():
                        obj = obj[int(subkey)]
                    else:
                        if isinstance(obj, dict):
                            obj = obj[subkey]
                        else:
                            obj = getattr(obj, subkey)
                    if isinstance(obj, types.MethodType):
                        obj = obj()
                if obj is not None and filter_names:
                    filter_names = filter_names[0]
                    filter_name, *params = re.split(r"(?<!\\):", filter_names)
                    params = tuple(map(lambda s: re.sub(r"\\:", ":", s), params))
                    obj = self.do_filter_object(obj, filter_name, params)
        except (
            IndexError,
            AttributeError,
            TypeError,
            KeyError,
            models.ObjectDoesNotExist,
        ):
            return default
        return obj

    def _digest(self):
        out = ""
        for c in self._listing.columns:
            out += "<b>{} :</b> {}<br>\n".format(c.name, c.get_cell_value(self))
        return out

    def __str__(self):
        return mark_safe(self._digest())

    def __getattr__(self, item):
        return self.get(item)

    def __getitem__(self, item):
        return self.get(item)

    def __delitem__(self, key):
        del self._obj[key]

    def set(self, item, value):
        if isinstance(self._obj, dict):
            self._obj[item] = value
        else:
            setattr(self._obj, item, value)
