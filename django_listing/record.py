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
from urllib.parse import quote_plus, quote

from django.core.serializers.json import Serializer
from django.db import models
from django.db.models import F, Model, Count
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.core.serializers import serialize

from .exceptions import *

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

    def group_by_foreignkey_object_map(self, records):
        lsg = self.listing
        if lsg.gb_cols:
            from . import ForeignKeyColumn  # local import to avoid circular import

            # Remap model instances if any:
            fk_cols = [c for c in lsg.columns if isinstance(c, ForeignKeyColumn)]
            for col in fk_cols:
                col_name = col.name
                model = col.model_field.related_model
                pks = [rec.get(col_name) for rec in records]
                objs = model.objects.filter(pk__in=pks)
                pk2obj = {obj.pk: obj for obj in objs}
                for rec in records:
                    rec.set(col_name, pk2obj[rec[col_name]])

    def current_page(self):
        if not self._records:
            lsg = self.listing
            self._records = [
                # lsg.current_page is set in RecordManager.compute_current_page_records()
                Record(lsg, obj, i)
                for i, obj in enumerate(lsg.current_page)
            ]
            self.group_by_foreignkey_object_map(self._records)
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
        qs = lsg.data
        if lsg.gb_cols:
            records = [Record(lsg, obj, i) for i, obj in enumerate(qs)]
            self.group_by_foreignkey_object_map(records)
            for rec in records:
                yield rec
        else:
            qs = self.filter_queryset(qs)
            for i, obj in enumerate(qs):
                yield Record(lsg, obj, i)

    def filter_queryset(self, qs):
        if self.listing.filters:
            form = self.listing.filters.form()
            cleaned_data = form.cleaned_data if form.is_valid() else None
            for filtr in self.listing.filters:
                qs = filtr.filter_queryset(qs, cleaned_data)
        return qs

    def get_filtered_queryset(self):
        qs = self.listing.data
        qs = self.filter_queryset(qs)
        return qs

    def get_objs_from_queryset(self):
        if not hasattr(self, "_queryset_objs"):
            qs = self.get_filtered_queryset()
            lsg = self.listing
            if lsg.force_order_by:
                order_by = lsg.force_order_by
            else:
                order_by = []
                if lsg.sort:
                    for col_name in lsg.columns_sort_list:
                        order_prefix = (
                            "" if lsg.columns_sort_ascending[col_name] else "-"
                        )
                        col = lsg.columns.get(col_name)
                        if col:
                            if isinstance(col.sort_key, (tuple, list)):
                                for sort_key in col.sort_key:
                                    order_by.append(order_prefix + sort_key)
                            else:
                                order_by.append(order_prefix + col.sort_key)
                # add a default sorting to avoid a Django 'UnorderedObjectListWarning'
                if not order_by:
                    order_by = ["pk"]
            self._queryset_objs = qs.order_by(*order_by)
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

    def get_form_serialized_cols(self, obj, cols):
        data = {}
        for col in cols:
            data_key = col.data_key
            final_object = None
            if "." in data_key:
                attr, foreign_attr = data_key.split(".", maxsplit=1)
                foreign_object = getattr(obj, attr, None)
                final_object = getattr(foreign_object, foreign_attr, None)
            else:
                final_object = getattr(obj, data_key, None)
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
        method = getattr(self._obj, "get_serialized_form_data", None)
        form_data = method() if method else {}
        if self._listing.form_serialize_cols:
            func = self._listing.form_serialize_cols_func
            if func is None:
                func = self.get_form_serialized_cols
            elif isinstance(func, str):
                func = getattr(self._obj.__class__, func)
            form_data.update(func(self._obj, self._listing.form_serialize_cols))
        if self._listing.form_no_autofill_cols:
            additional_data["no_autofill"] = self._listing.form_no_autofill_cols
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

    def get_filter(self, obj, filter_name, params):
        if filter_name == "urlencode" and isinstance(obj, str):
            obj = quote_plus(obj)
        elif filter_name == "replace":
            obj = obj.replace(*params)
        elif filter_name == "sub":
            obj = re.sub(*params, obj)
        elif filter_name == "basename":
            obj = os.path.basename(obj)
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
                kwargs[fname] = val
        return self._listing.get_url(**kwargs)

    def get(self, key, default=None):
        obj = self._obj
        try:
            if isinstance(key, int):
                obj = obj[key]
            else:
                key, *filter = key.split("|", 1)
                for subkey in re.split(r"\.|__", key):
                    op = None
                    if "|" in subkey:
                        subkey, op = subkey.split("|")
                    if subkey.isdigit():
                        obj = obj[int(subkey)]
                    else:
                        if isinstance(obj, dict):
                            obj = obj[subkey]
                        else:
                            obj = getattr(obj, subkey)
                    if isinstance(obj, types.MethodType):
                        obj = obj()
                if obj is not None and filter:
                    filter = filter[0]
                    filter_name, *params = re.split(r"(?<!\\):", filter)
                    params = tuple(map(lambda s: re.sub(r"\\:", ":", s), params))
                    obj = self.get_filter(obj, filter_name, params)
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

    def set(self, item, value):
        if isinstance(self._obj, dict):
            self._obj[item] = value
        else:
            setattr(self._obj, item, value)
