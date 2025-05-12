from django_listing.theme_config import ThemeTemplate
from decimal import Decimal
from django.conf import settings
from .utils import to_js_timestamp, FastAttrDict

__all__ = [
    "BaseChartMixin",
    "PieChartMixin",
    "BarChartMixin",
    "TimestampedBarChartMixin",
    "TimestampedLineChartMixin",
]


class ApexChartsMixin:
    """This is to be included in every listing where a chart need to be rendered.
    IMPORTANT : this includes ALL charts that do not display chart
                but have a variation that does display one.
    """

    def render_init(self, *args, **kwargs):
        self.need_media_for("apexcharts")
        super().render_init(*args, **kwargs)


class BaseChartMixin:
    listing_template_name = ThemeTemplate("chart.html")
    chart_height = 600
    chart_width = 800
    chart_series_name = "series name TO BE DEFINED"
    chart_stroke_curve = "straight"  # could be "straight", "smooth", "stepline"
    chart_has_grid = True
    chart_has_dropshadow = True
    chart_grid_border_color = "#aaaaaa"
    chart_grid_colors = ["#ffffff", "#e8e8e8"]

    def get_chart_records(self):
        # If you derive this method, you need to cache results as this method
        # will be called many times.
        # Note : self.records.current_page() already caches records
        return self.records.current_page()

    def get_chart_rec_color(self, rec):
        idx = rec.get_index()
        dlst_settings = settings.django_listing_settings
        gradient = dlst_settings.CHARTS_DEFAULT_GRADIENT
        gradient_default = dlst_settings.CHARTS_DEFAULT_GRADIENT_OVERFLOW
        color = gradient[idx] if idx < len(gradient) else gradient_default
        return color

    def get_chart_series_colors(self, series):
        colors = []
        for i, s in enumerate(series):
            idx = i * 2  # otherwise colors are too near
            dlst_settings = settings.django_listing_settings
            gradient = dlst_settings.CHARTS_DEFAULT_GRADIENT
            gradient_default = dlst_settings.CHARTS_DEFAULT_GRADIENT_OVERFLOW
            color = gradient[idx] if idx < len(gradient) else gradient_default
            colors.append(color)
        return colors

    def get_chart_rec_values(self, rec):
        val = rec.get(self.chart_values_rec_key)
        if isinstance(val, Decimal):
            val = float(val)
        return val

    def get_chart_rec_label(self, rec):
        if self.chart_labels_rec_key is None:
            return None
        return rec.get(self.chart_labels_rec_key, "-")

    def get_chart_height(self):
        return self.chart_height

    def get_chart_width(self):
        return self.chart_width

    def get_apex_options(self):
        raise NotImplementedError("Please define get_apex_options() method")

    def get_chart_json_id(self):
        return f"{self.css_id}-chart-json-id"

    def get_chart_div_id(self):
        return f"{self.css_id}-chart-id"

    def get_chart_series_name(self):
        return self.chart_series_name

    def get_chart_series(self, context):
        return [
            {
                "name": context.series_name,
                "data": context.values,
            },
        ]

    def get_chart_xaxis(self, context):
        raise NotImplementedError("Please define get_chart_xaxis() method")

    def chart_data(self):
        return dict(
            chart_div_id=self.get_chart_div_id(),
            json_id=self.get_chart_json_id(),
            apexcharts_options=self.get_chart_options(),
        )

    def get_chart_options(self, records):
        raise NotImplementedError("Please define get_chart_options() method")

    def get_chart_context(self):
        colors = []
        values = []
        labels = []
        for rec in self.get_chart_records():
            colors.append(self.get_chart_rec_color(rec))
            values.append(self.get_chart_rec_values(rec))
            labels.append(self.get_chart_rec_label(rec))
        context = FastAttrDict(
            values=values,
            labels=labels,
            colors=colors,
            width=self.get_chart_width(),
            height=self.get_chart_height(),
            chart_div_id=self.get_chart_div_id(),
            series_name=self.get_chart_series_name(),
            stroke_curve=self.chart_stroke_curve,
            has_grid=self.chart_has_grid,
            grid_border_color=self.chart_grid_border_color,
            grid_colors=self.chart_grid_colors,
            has_dropshadow=self.chart_has_dropshadow,
        )
        context.series = self.get_chart_series(context)
        return context


class PieChartMixin(BaseChartMixin):
    listing_template_name = ThemeTemplate("chart_pie.html")

    def get_chart_options(self):
        context = self.get_chart_context()
        options = {
            "series": context.values,
            "chart": {
                "id": context.chart_div_id,
                "width": context.width,
                "height": context.height,
                "type": "pie",
            },
            "colors": context.colors,
            "labels": context.labels,
            "dataLabels": {"style": {"fontSize": "16px"}},
        }
        return options


class BarChartMixin(BaseChartMixin):
    listing_template_name = ThemeTemplate("chart_bar.html")

    def get_chart_xaxis(self, context):
        return {
            "categories": context.labels,
            "labels": {"style": {"colors": context.colors, "fontSize": "12px"}},
        }

    def get_chart_options(self):
        context = self.get_chart_context()
        options = {
            "series": context.series,
            "chart": {
                "id": context.chart_div_id,
                "width": context.width,
                "height": context.height,
                "type": "bar",
            },
            "colors": context.colors,
            "plotOptions": {
                "bar": {
                    "columnWidth": "45%",
                    "distributed": True,
                    "dataLabels": {
                        "position": "top",
                    },
                }
            },
            "dataLabels": {
                "enabled": True,
                "offsetY": -20,
                "style": {"fontSize": "12px", "colors": ["#222222"]},
            },
            "legend": {"show": False},
            "xaxis": self.get_chart_xaxis(context),
        }
        if context.has_dropshadow:
            options["chart"]["dropShadow"] = {
                "enabled": True,
                "color": "#000",
                "top": 18,
                "left": 7,
                "blur": 10,
                "opacity": 0.5,
            }
        if context.has_grid:
            options["grid"] = {
                "borderColor": context.grid_border_color,
                "row": {
                    "colors": context.grid_colors,
                    "opacity": 0.5,
                },
            }
        return options


class TimestampedChartMixin(BaseChartMixin):
    chart_labels_rec_key = None

    def get_chart_rec_color(self, rec):
        return settings.django_listing_settings.CHARTS_DEFAULT_TREND_BAR_COLOR

    def get_chart_rec_values(self, rec):
        val = rec.get(self.chart_values_rec_key)
        timestamp = to_js_timestamp(rec.get(self.chart_timestamps_rec_key))
        if isinstance(val, Decimal):
            val = float(val)
        return [timestamp, val]


class TimestampedBarChartMixin(TimestampedChartMixin):
    listing_template_name = ThemeTemplate("chart_trend_bar.html")

    def get_chart_xaxis(self, context):
        return {
            "type": "datetime",
            "tickAmount": 6,
        }

    def get_chart_options(self):
        context = self.get_chart_context()
        options = {
            "colors": context.colors,
            "series": context.series,
            "chart": {
                "id": context.chart_div_id,
                "type": "bar",
                "width": context.width,
                "height": context.height,
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
            "xaxis": self.get_chart_xaxis(context),
            "tooltip": {
                "x": {
                    "format": "dd MMM yyyy",
                }
            },
        }
        if context.has_dropshadow:
            options["chart"]["dropShadow"] = {
                "enabled": True,
                "color": "#000",
                "top": 18,
                "left": 7,
                "blur": 10,
                "opacity": 0.5,
            }
        if context.has_grid:
            options["grid"] = {
                "borderColor": context.grid_border_color,
                "row": {
                    "colors": context.grid_colors,
                    "opacity": 0.5,
                },
            }
        return options


class LineChartMixin(BaseChartMixin):
    listing_template_name = ThemeTemplate("chart_trend_bar.html")
    chart_labels_rec_key = None
    per_page = 1000

    def get_chart_options(self):
        context = self.get_chart_context()
        series = self.get_chart_series(context)
        colors = self.get_chart_series_colors(series)
        options = {
            "colors": colors,
            "series": series,
            "chart": {
                "id": "chart",
                "type": "line",
                "width": context.width,
                "height": context.height,
                "zoom": {
                    "autoScaleYaxis": True,
                },
            },
            "stroke": {
                "curve": context.stroke_curve,
            },
            "dataLabels": {
                "enabled": False,
            },
            "markers": {
                "size": 0,
                "style": "hollow",
            },
            "xaxis": self.get_chart_xaxis(context),
            "tooltip": {
                "x": {
                    "format": "dd MMM yyyy",
                }
            },
        }
        if context.has_dropshadow:
            options["chart"]["dropShadow"] = {
                "enabled": True,
                "color": "#000",
                "top": 18,
                "left": 7,
                "blur": 10,
                "opacity": 0.5,
            }
        if context.has_grid:
            options["grid"] = {
                "borderColor": context.grid_border_color,
                "row": {
                    "colors": context.grid_colors,
                    "opacity": 0.5,
                },
            }

        return options


class TimestampedLineChartMixin(LineChartMixin):
    listing_template_name = ThemeTemplate("chart_trend_bar.html")
    chart_labels_rec_key = None
    per_page = 1000

    def get_chart_rec_values(self, rec):
        val = rec.get(self.chart_values_rec_key)
        timestamp = rec.get(self.chart_timestamps_rec_key)
        if isinstance(val, Decimal):
            val = float(val)
        return [timestamp, val]

    def get_chart_xaxis(self, context):
        return {
            "type": "datetime",
            "tickAmount": 6,
        }

    def get_chart_options(self):
        context = self.get_chart_context()
        series = self.get_chart_series(context)
        colors = self.get_chart_series_colors(series)
        options = {
            "colors": colors,
            "series": series,
            "chart": {
                "id": "chart",
                "type": "line",
                "width": context.width,
                "height": context.height,
                "zoom": {
                    "autoScaleYaxis": True,
                },
            },
            "stroke": {
                "curve": context.stroke_curve,
            },
            "dataLabels": {
                "enabled": False,
            },
            "markers": {
                "size": 0,
                "style": "hollow",
            },
            "xaxis": self.get_chart_xaxis(context),
            "tooltip": {
                "x": {
                    "format": "dd MMM yyyy",
                }
            },
        }
        if context.has_dropshadow:
            options["chart"]["dropShadow"] = {
                "enabled": True,
                "color": "#000",
                "top": 18,
                "left": 7,
                "blur": 10,
                "opacity": 0.5,
            }
        if context.has_grid:
            options["grid"] = {
                "borderColor": context.grid_border_color,
                "row": {
                    "colors": context.grid_colors,
                    "opacity": 0.5,
                },
            }

        return options
