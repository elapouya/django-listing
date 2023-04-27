#
# Created : 2018-24-04
#
# @author: Eric Lapouyade
#

from django.db.models import Avg, Max, Min, Sum
from django.db.models.query import QuerySet
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .exceptions import InvalidAggregation

__all__ = [
    "Aggregation",
    "AggregationMeta",
    "AvgAggregation",
    "MaxAggregation",
    "MinAggregation",
    "SumAggregation",
]


class AggregationMeta(type):
    slug2class = {}

    def __new__(mcs, name, bases, attrs):
        cls = super(AggregationMeta, mcs).__new__(mcs, name, bases, attrs)
        AggregationMeta.slug2class[AggregationMeta.get_slug(cls)] = cls
        return cls

    @classmethod
    def get_slug(cls, mcs):
        return mcs.__name__.replace("Aggregation", "").lower()

    @classmethod
    def get_aggregation_slugs(cls):
        aggs = list(filter(None, cls.slug2class.keys()))
        return aggs + ["global_" + agg for agg in aggs]

    @classmethod
    def get_instance(cls, slug, column):
        global_aggregation = False
        if slug.startswith("global_"):
            global_aggregation = True
            slug = slug[7:]
        agg_cls = cls.slug2class.get(slug)
        if agg_cls is None:
            raise InvalidAggregation(
                gettext('Unknown "{}" aggregation, choose one of these : ' "{}").format(
                    slug, ",".join(cls.get_aggregation_slugs())
                )
            )
        return agg_cls(column, global_aggregation=global_aggregation)


class Aggregation(metaclass=AggregationMeta):
    footer_tpl = None
    value_tpl = "{value}"
    params_keys = None

    def __init__(self, column, global_aggregation=False):
        self.values = []
        self.column = column
        self.global_aggregation = global_aggregation
        if self.params_keys:
            params_to_check = self.params_keys
            if isinstance(params_to_check, str):
                params_to_check = params_to_check.split(",")
            for p in params_to_check:
                if not hasattr(column, p):
                    setattr(column, p, getattr(self, p))

    def get_numeric_values(self):
        return [v for v in self.values if isinstance(v, (int, float))]

    def aggregate(self, rec):
        if not self.global_aggregation:
            value = self.column.get_cell_value(rec)
            self.values.append(value)

    def get_footer_attrs(self, ctx, value):
        attrs = self.column.get_footer_attrs(ctx, value)
        attrs.add("class", "agg-{}".format(AggregationMeta.get_slug(self.__class__)))
        return attrs

    def get_footer_context(self, value):
        return self.column.get_footer_context(value)

    def get_footer_value_tpl(self, ctx, value):
        col = self.column
        if hasattr(col, "get_footer_aggregation_value_tpl"):
            return col.get_footer_aggregation_value_tpl(ctx, value)
        elif col.footer_value_tpl is not None:
            return col.footer_value_tpl
        elif self.value_tpl is not None:
            return self.value_tpl
        return "{value}"

    def get_footer_template(self, ctx, value):
        col = self.column
        if hasattr(col, "get_footer_aggregation_template"):
            return col.get_footer_aggregation_template(ctx, value)
        elif col.footer_tpl is not None:
            return col.footer_tpl
        elif self.footer_tpl is not None:
            return self.footer_tpl
        return "<td{attrs}>%s</td>" % self.get_footer_value_tpl(ctx, value)

    def render_footer(self):
        if self.values or self.global_aggregation:
            value = self.get_aggregated_value()
            ctx = self.get_footer_context(value)
            ctx.attrs = self.get_footer_attrs(ctx, value)
            tpl = self.get_footer_template(ctx, value)
            try:
                return tpl.format(**ctx)
            except (ValueError, AttributeError, IndexError) as e:
                return '<td class="render-error">{}</td>'.format(e)
        else:
            return self.column.default_footer_value

    def get_aggregated_value_from_sequence(self, seq):
        records = self.column.listing.records.get_all()
        self.values = [self.column.get_cell_value(rec) for rec in records]
        return self.get_aggregated_value_from_current_page()

    def get_aggregated_value(self):
        if self.global_aggregation:
            data = self.column.listing.data
            if isinstance(data, QuerySet):
                return self.get_aggregated_value_from_queryset(data)
            else:
                return self.get_aggregated_value_from_sequence(data)
        else:
            return self.get_aggregated_value_from_current_page()


class SumAggregation(Aggregation):
    value_tpl = _("Total :<br>{value}")

    def get_aggregated_value_from_current_page(self):
        return sum(self.get_numeric_values())

    def get_aggregated_value_from_queryset(self, qs):
        return qs.aggregate(val=Sum(self.column.data_key)).get("val")


class MinAggregation(Aggregation):
    value_tpl = _("Min :<br>{value}")

    def get_aggregated_value_from_current_page(self):
        return min(self.get_numeric_values())

    def get_aggregated_value_from_queryset(self, qs):
        return qs.aggregate(val=Min(self.column.data_key)).get("val")


class MaxAggregation(Aggregation):
    value_tpl = _("Max :<br>{value}")

    def get_aggregated_value_from_current_page(self):
        return max(self.get_numeric_values())

    def get_aggregated_value_from_queryset(self, qs):
        return qs.aggregate(val=Max(self.column.data_key)).get("val")


class MinMaxAggregation(Aggregation):
    value_tpl = _("Min : {min_val}<br>Max : {max_val}")

    def get_aggregated_value_from_current_page(self):
        return dict(
            min_val=min(self.get_numeric_values()),
            max_val=max(self.get_numeric_values()),
        )

    def get_aggregated_value_from_queryset(self, qs):
        return qs.aggregate(
            min_val=Min(self.column.data_key), max_val=Max(self.column.data_key)
        )


class MinMaxAvgAggregation(Aggregation):
    value_tpl = _(
        "Min : {min_val}<br>Max : {max_val}<br>"
        "Avg : {avg_val:.{col.footer_precision}f}"
    )
    params_keys = "footer_precision"
    footer_precision = 2

    def get_aggregated_value_from_current_page(self):
        num_values = self.get_numeric_values()
        return dict(
            min_val=min(num_values),
            max_val=max(num_values),
            avg_val=sum(num_values) / len(num_values),
        )

    def get_aggregated_value_from_queryset(self, qs):
        return qs.aggregate(
            min_val=Min(self.column.data_key),
            max_val=Max(self.column.data_key),
            avg_val=Avg(self.column.data_key),
        )


class AvgAggregation(Aggregation):
    value_tpl = "Average :<br>{value:.{col.footer_precision}f}"
    params_keys = "footer_precision"
    footer_precision = 2

    def get_aggregated_value_from_current_page(self):
        num_values = self.get_numeric_values()
        return sum(num_values) / len(num_values)

    def get_aggregated_value_from_queryset(self, qs):
        return qs.aggregate(val=Avg(self.column.data_key)).get("val")
