#
# Created : 2018-02-16
#
# @author: Eric Lapouyade
#

from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from .views import *
from django_robohash.views import robohash

urlpatterns = i18n_patterns(
    path('', IndexView.as_view(),
         name='index'),
    path('admin/', admin.site.urls),
    path('readme_first/', ReadMeFirstView.as_view(),
         name='readme_first'),
    path('basic_usage/', BasicUsageListingView.as_view(),
         name='basic_usage'),
    path('many_ways/', ManyWaysListingView.as_view(),
         name='many_ways'),
    path('advanced_usage/', AdvancedUsageListingView.as_view(),
         name='advanced_usage'),
    path('pagination/', PaginationListingView.as_view(),
         name='pagination'),
    path('div_rows/', DivRowsListingView.as_view(),
         name='div_rows'),
    path('columns/', ColumnsListingIndexView.as_view(),
         name='columns'),
    path('columns/1/', ColumnsListing1View.as_view(),
         name='columns1'),
    path('columns/2/', ColumnsListing2View.as_view(),
         name='columns2'),
    path('columns/3/', ColumnsListing3View.as_view(),
         name='columns3'),
    path('columns/4/', ColumnsListing4View.as_view(),
         name='columns4'),
    path('columns/5/', ColumnsListing5View.as_view(),
         name='columns5'),
    path('aggregation/', AggregationListingView.as_view(),
         name='aggregation'),
    path('variations/', VariationsListingView.as_view(),
         name='variations'),
    path(r'translation/', TranslationListingView.as_view(),
         name='translation'),
    path('ajax/', AjaxListingView.as_view(),
         name='ajax'),
    path('toolbar/', ToolbarListingView.as_view(),
         name='toolbar'),
    path('speed_test/', SpeedTestListingView.as_view(),
         name='speed_test'),
    path('speed_test/1/', SpeedTest1ListingView.as_view(),
         name='speed_test_1'),
    path('speed_test/2/', SpeedTest2ListingView.as_view(),
         name='speed_test_2'),
    path('filters/', FiltersListingIndexView.as_view(),
         name='filters'),
    path('filters/1/', FiltersListing1View.as_view(),
         name='filters_1'),
    path('filters/2/', FiltersListing2View.as_view(),
         name='filters_2'),
    path('editable/', EditableListingIndexView.as_view(),
         name='editable'),
    path('editable/1/', EditableListing1View.as_view(),
         name='editable1'),
    path('editable/2/', EditableListing2View.as_view(),
         name='editable2'),
    path('editable/3/', EditableListing3View.as_view(),
         name='editable3'),
    path('editable/4/', EditableListing4View.as_view(),
         name='editable4'),
    path('selectable/', SelectableListingIndexView.as_view(),
         name='selectable'),
    path('selectable/1/', SelectableListing1View.as_view(),
         name='selectable1'),
    path('selectable/2/', SelectableListing2View.as_view(),
         name='selectable2'),
    path('selectable/3/', SelectableListing3View.as_view(),
         name='selectable3'),
    path('selectable/4/', SelectableListing4View.as_view(),
         name='selectable4'),
    path('selectable/5/', SelectableListing5View.as_view(),
         name='selectable5'),
    path('insertable/', InsertableListingView.as_view(),
         name='insertable'),
    path('upload/', UploadListingView.as_view(),
         name='upload'),
    path('fonticons/', FonticonsView.as_view(),
         name='fonticons'),
    path('show_employee/<int:pk>/', EmployeeDetailView.as_view(),
         name='employee_detail'),
    path('show_company/<int:pk>/', CompanyDetailView.as_view(),
         name='company_detail'),
    # from django-robohash-svg django app
    path('robohash/<string>/', robohash,
         name='robohash'),
)


if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)