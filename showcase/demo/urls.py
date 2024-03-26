#
# Created : 2018-02-16
#
# @author: Eric Lapouyade
#

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django_robohash.views import robohash

from .views import *


# fmt: off
urlpatterns = i18n_patterns(
    path("", IndexView.as_view(), name="index"),
    path("admin/", admin.site.urls),
    path("readme_first/", ReadMeFirstView.as_view(), name="readme_first"),
    path("readme/1/", ReadMe1View.as_view(), name="readme1"),
    path("readme/2/", ReadMe2View.as_view(), name="readme2"),
    path("basic_usage/", BasicUsageListingView.as_view(), name="basic_usage"),
    path("many_ways/", ManyWaysView.as_view(), name="many_ways"),
    path("many_ways/1/", ManyWays1View.as_view(), name="many_ways1"),
    path("many_ways/2/", ManyWays2View.as_view(), name="many_ways2"),
    path("many_ways/3/", ManyWays3View.as_view(), name="many_ways3"),
    path("advanced_usage/", AdvancedUsageListingView.as_view(), name="advanced_usage"),
    path("pagination/", PaginationListingView.as_view(), name="pagination"),
    path("div_rows/", DivRowsListingView.as_view(), name="div_rows"),
    path("columns/", ColumnsListingIndexView.as_view(), name="columns"),
    path("columns/1/", ColumnsListing1View.as_view(), name="columns1"),
    path("columns/2/", ColumnsListing2View.as_view(), name="columns2"),
    path("columns/3/", ColumnsListing3View.as_view(), name="columns3"),
    path("columns/4/", ColumnsListing4View.as_view(), name="columns4"),
    path("columns/5/", ColumnsListing5View.as_view(), name="columns5"),
    path("aggregation/", AggregationListingView.as_view(), name="aggregation"),
    path("variations/", VariationsListingView.as_view(), name="variations"),
    path(r"translation/", TranslationListingView.as_view(), name="translation"),
    path("ajax/", AjaxListingView.as_view(), name="ajax"),
    path("toolbar/", ToolbarListingView.as_view(), name="toolbar"),
    path("speed_test/", SpeedTestListingView.as_view(), name="speed_test"),
    path("speed_test/1/", SpeedTest1ListingView.as_view(), name="speed_test_1"),
    path("speed_test/2/", SpeedTest2ListingView.as_view(), name="speed_test_2"),
    path("filters/", FiltersListingIndexView.as_view(), name="filters"),
    path("filters/1/", FiltersListing1View.as_view(), name="filters_1"),
    path("filters/2/", FiltersListing2View.as_view(), name="filters_2"),
    path("filters/3/", FiltersListing3View.as_view(), name="filters_3"),
    path("editable/", EditableListingIndexView.as_view(), name="editable"),
    path("editable/1/", EditableListing1View.as_view(), name="editable1"),
    path("editable/2/", EditableListing2View.as_view(), name="editable2"),
    path("editable/3/", EditableListing3View.as_view(), name="editable3"),
    path("editable/4/", EditableListing4View.as_view(), name="editable4"),
    path("ref_guide/", RefGuideView.as_view(), name="ref_guide"),
    path("ref_guide/1/", RefGuide1View.as_view(), name="ref_guide1"),
    path("ref_guide/2/", RefGuide2View.as_view(), name="ref_guide2"),
    path("ref_guide/3/", RefGuide3View.as_view(), name="ref_guide3"),
    path("ref_guide/4/", RefGuide4View.as_view(), name="ref_guide4"),
    path("ref_guide/5/", RefGuide5View.as_view(), name="ref_guide5"),
    path("ref_guide/6/", RefGuide6View.as_view(), name="ref_guide6"),
    path("ref_guide/7/", RefGuide7View.as_view(), name="ref_guide7"),
    path("ref_guide/8/", RefGuide8View.as_view(), name="ref_guide8"),
    path("ref_guide/9/", RefGuide9View.as_view(), name="ref_guide9"),
    path("selectable/", SelectableListingIndexView.as_view(), name="selectable"),
    path("selectable/1/", SelectableListing1View.as_view(), name="selectable1"),
    path("selectable/2/", SelectableListing2View.as_view(), name="selectable2"),
    path("selectable/3/", SelectableListing3View.as_view(), name="selectable3"),
    path("selectable/4/", SelectableListing4View.as_view(), name="selectable4"),
    path("selectable/5/", SelectableListing5View.as_view(), name="selectable5"),
    path("group_by/", GroupByListingView.as_view(), name="group_by"),
    path("insertable/", InsertableListingIndexView.as_view(), name="insertable"),
    path("insertable1/", InsertableListing1View.as_view(), name="insertable1"),
    path("insertable2/", InsertableListing2View.as_view(), name="insertable2"),
    path("upload/", UploadListingView.as_view(), name="upload"),
    path("fonticons/", FonticonsView.as_view(), name="fonticons"),
    path(
        "show_employee/<int:pk>/", EmployeeDetailView.as_view(), name="employee_detail"
    ),
    path("show_company/<int:pk>/", CompanyDetailView.as_view(), name="company_detail"),
    # from django-robohash-svg django app
    path("robohash/<string>/", robohash, name="robohash"),
    path("company-autocomplete/", CompanyAutocomplete.as_view(), name="company-autocomplete"),
    path("interest-autocomplete/", InterestAutocomplete.as_view(), name="interest-autocomplete"),
)
# fmt: on


if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
