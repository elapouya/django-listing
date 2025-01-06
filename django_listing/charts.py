from django_listing import Listing
from django_listing.theme_config import ThemeTemplate
from decimal import Decimal
from django.conf import settings

__all__ = [
    "BaseChartMixin",
    "PieChartMixin",
    "TrendBarChartMixin",
]


# class BaseChartMixin:
#     def get_chart_records(self):
#         # If you derive this method, you need to cache results as this method
#         # will be call many times.
#         # Note : self.records.current_page() already caches records
#         return self.records.current_page()
#
#     def get_chart_rec_color(self, rec):
#         idx = rec.get_index()
#         dlst_settings = settings.django_listing_settings
#         gradient = dlst_settings.CHARTS_DEFAULT_GRADIENT
#         gradient_default = dlst_settings.CHARTS_DEFAULT_GRADIENT_OVERFLOW
#         color = gradient[idx] if idx < len(gradient) else gradient_default
#         return color
#
#     def get_chart_rec_values(self, rec):
#         val = rec.get(self.chart_values_rec_key)
#         if isinstance(val, Decimal):
#             val = float(val)
#         return val
#
#     def get_chart_rec_label(self, rec):
#         return rec.get(self.chart_labels_rec_key, "-")
#
#     def chart_data(self):
#         colors = []
#         values = []
#         labels = []
#         for rec in self.get_chart_records():
#             colors.append(self.get_chart_rec_color(rec))
#             values.append(self.get_chart_rec_values(rec))
#             labels.append(self.get_chart_rec_label(rec))
#         return dict(
#             json_id=f"{self.css_id}-salescopes-chart-pie",
#             colors=colors,
#             values=values,
#             labels=labels,
#         )


# class PieChartMixin(BaseChartMixin):
#     listing_template_name = ThemeTemplate("chart_pie.html")
#
#
# class TrendBarChartMixin(BaseChartMixin):
#     listing_template_name = ThemeTemplate("chart_trend_bar.html")
#
#     def get_chart_rec_color(self, rec):
#         return settings.django_listing_settings.CHARTS_DEFAULT_TREND_BAR_COLOR
#
#     def get_chart_rec_label(self, rec):
#         return None
#
#     def get_chart_rec_values(self, rec):
#         val = rec.get(self.chart_values_rec_key)
#         timestamp = rec.get(self.chart_timestamps_rec_key)
#         if isinstance(val, Decimal):
#             val = float(val)
#         return [timestamp, val]


class BaseChartMixin:
    listing_template_name = ThemeTemplate("chart.html")

    def get_chart_records(self):
        # If you derive this method, you need to cache results as this method
        # will be call many times.
        # Note : self.records.current_page() already caches records
        return self.records.current_page()

    def get_chart_rec_color(self, rec):
        idx = rec.get_index()
        dlst_settings = settings.django_listing_settings
        gradient = dlst_settings.CHARTS_DEFAULT_GRADIENT
        gradient_default = dlst_settings.CHARTS_DEFAULT_GRADIENT_OVERFLOW
        color = gradient[idx] if idx < len(gradient) else gradient_default
        return color

    def get_chart_rec_values(self, rec):
        val = rec.get(self.chart_values_rec_key)
        if isinstance(val, Decimal):
            val = float(val)
        return val

    def get_chart_rec_label(self, rec):
        if self.chart_labels_rec_key is None:
            return None
        return rec.get(self.chart_labels_rec_key, "-")

    def get_apex_options(self):
        raise NotImplemented

    def get_chart_json_id(self):
        return f"{self.css_id}-chart-json-id"

    def chart_data(self):
        return dict(
            json_id=self.get_chart_json_id(),
            apexcharts_options=self.get_apex_options(),
        )

    def get_chart_series(self):
        colors = []
        values = []
        labels = []
        for rec in self.get_chart_records():
            colors.append(self.get_chart_rec_color(rec))
            values.append(self.get_chart_rec_values(rec))
            labels.append(self.get_chart_rec_label(rec))
        return values, labels, colors


class PieChartMixin(BaseChartMixin):
    listing_template_name = ThemeTemplate("chart_pie.html")

    def get_apex_options(self):
        values, labels, colors = self.get_chart_series()

        options = {
            "series": values,
            "chart": {
                "width": 900,
                "type": "pie",
            },
            "colors": colors,
            "labels": labels,
            "dataLabels": {"style": {"fontSize": "16px"}},
        }
        return options


class TrendBarChartMixin(BaseChartMixin):
    listing_template_name = ThemeTemplate("chart_trend_bar.html")
    chart_labels_rec_key = None

    def get_chart_rec_color(self, rec):
        return settings.django_listing_settings.CHARTS_DEFAULT_TREND_BAR_COLOR

    def get_chart_rec_values(self, rec):
        val = rec.get(self.chart_values_rec_key)
        timestamp = rec.get(self.chart_timestamps_rec_key)
        if isinstance(val, Decimal):
            val = float(val)
        return [timestamp, val]

    def get_apex_options(self):
        values, labels, colors = self.get_chart_series()

        options = {
            "colors": colors,
            "series": [
                {
                    "name": "Active values (Sum)",
                    "data": values,
                }
            ],
            "chart": {
                "id": "chart",
                "type": "bar",
                "height": 350,
                "zoom": {
                    "autoScaleYaxis": True,
                },
            },
            "plotOptions": {
                "bar": {
                    "columnWidth": "85%",
                }
            },
            "dataLabels": {
                "enabled": False,
            },
            "markers": {
                "size": 0,
                "style": "hollow",
            },
            "xaxis": {
                "type": "datetime",
                "tickAmount": 6,
            },
            "tooltip": {
                "x": {
                    "format": "dd MMM yyyy",
                }
            },
        }
        return options
