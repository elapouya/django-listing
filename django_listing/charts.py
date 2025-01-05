from django_listing.theme_config import ThemeTemplate
from decimal import Decimal
from django.conf import settings

__all__ = [
    "BaseChartMixin",
    "PieChartMixin",
    "TrendBarChartMixin",
]


class BaseChartMixin:
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
        return rec.get(self.chart_labels_rec_key, "-")

    def chart_data(self):
        colors = []
        values = []
        labels = []
        for rec in self.get_chart_records():
            colors.append(self.get_chart_rec_color(rec))
            values.append(self.get_chart_rec_values(rec))
            labels.append(self.get_chart_rec_label(rec))
        return dict(
            json_id=f"{self.css_id}-salescopes-chart-pie",
            colors=colors,
            values=values,
            labels=labels,
        )


class PieChartMixin(BaseChartMixin):
    listing_template_name = ThemeTemplate("chart_pie.html")


class TrendBarChartMixin(BaseChartMixin):
    listing_template_name = ThemeTemplate("chart_trend_bar.html")

    def get_chart_rec_color(self, rec):
        return settings.django_listing_settings.CHARTS_DEFAULT_TREND_BAR_COLOR

    def get_chart_rec_label(self, rec):
        return None

    def get_chart_rec_values(self, rec):
        val = rec.get(self.chart_values_rec_key)
        timestamp = rec.get(self.chart_timestamps_rec_key)
        if isinstance(val, Decimal):
            val = float(val)
        return [timestamp, val]
