#
# Created : 2018-02-16
#
# @author: Eric Lapouyade
#

import os
import pprint
import re

from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.db.models import Count
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView

import django_listing
from django_listing import *
from django_listing.utils import pretty_format_querydict

from .listings import *
from .models import *

pp = pprint.PrettyPrinter(indent=4)


class IndexView(TemplateView):
    template_name = "demo/index.html"


class ReadMeFirstView(TemplateView):
    template_name = "demo/readme_first.html"


class ManyWaysListingView(TemplateView):
    template_name = "demo/many_ways.html"


class FonticonsView(TemplateView):
    template_name = "demo/fonticons.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # read static/django_listing/css/django_listing.css
        # to extract built-in icons names
        css_path = os.path.join(
            os.path.dirname(django_listing.__file__),
            "static",
            "django_listing",
            settings.DJANGO_LISTING["THEME"],
            "css",
            "django_listing.css",
        )
        icons = []
        with open(css_path, "r", encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"\.(listing-icon-[^:]+):before \{", line)
                if m:
                    icons.append(m.group(1))
        context["icons"] = icons
        return context


class BasicUsageListingView(TemplateView):
    template_name = "demo/basic_usage.html"
    extra_context = dict(employees_as_model=Employee)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            employees_as_list_of_dicts=employees,
            employees_as_query_set=Employee.objects.all(),
            employees_as_list_of_lists=employees_as_list_of_lists,
            employees_as_simple_list_of_strings=[
                "{first_name} {last_name}".format(**e) for e in employees
            ],
        )
        return context


class AdvancedUsageListingView(ListingView):
    template_name = "demo/advanced_usage.html"
    context_classes = (EmployeeListing, EmployeeModelListing)
    extra_context = dict(
        females_as_list_of_dicts=list(
            filter(lambda rec: rec["gender"] == "Female", employees)
        ),
        males_as_query_set=Employee.objects.filter(gender="Male"),
        all_employees=Employee.objects.all(),
        employees_as_list_of_lists=employees_as_list_of_lists,
        # IMPORTANT : Do not put listing instance here
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Here is a good place to create a listing instance
        context["listing_instance"] = EmployeeListing(employees)
        return context


class PaginationListingView(ListingView):
    template_name = "demo/pagination.html"
    context_classes = (
        PaginationListing,
        NoTextButtonPaginationListing,
        NoIconButtonPaginationListing,
        CustomButtonsPaginationListing,
        EllipsisPaginationListing,
    )
    extra_context = dict(employees=employees)


class DivRowsListingView(ListingView):
    template_name = "demo/div_rows_listing.html"
    context_classes = (EmployeeDivListing, EmployeeThumbnailsListing, Employee)


class VariationsListingView(ListingView):
    template_name = "demo/variations.html"

    # alternative solution : re-declare get_listing_instance() method.
    def get_listing_instance(self):
        return EmployeeVariationsListing(Employee)


class ColumnsListingIndexView(TemplateView):
    template_name = "demo/columns.html"


class ColumnsListing1View(ListingView):
    template_name = "demo/columns1.html"
    context_classes = (
        BoolColumnsListing,
        BoolChoicesImgColumnsListing,
        DatetimeListing,
        LineNumberListing,
        BooleanModel,
        LinkObjectListing,
        Employee,
        Company,
    )


class ColumnsListing2View(ListingView):
    template_name = "demo/columns2.html"
    context_classes = (
        OneToManyListing,
        ManyToManyListing,
        ForeignKeyListing,
        Employee,
        Company,
    )


class ColumnsListing3View(ListingView):
    template_name = "demo/columns3.html"
    context_classes = (TotalListing,)
    extra_context = dict(
        numbers_matrix=numbers_matrix,
        matrix_with_sum_avg_max_min=[
            i + [sum(i), sum(i) / len(i), max(i), min(i)] for i in numbers_matrix
        ],
    )


class ColumnsListing4View(ListingView):
    template_name = "demo/columns4.html"
    context_classes = (
        LinksListing,
        WidgetsColumnsListing,
        Employee,
    )


class ColumnsListing5View(ListingView):
    template_name = "demo/columns5.html"
    listing_class = ActionsColumnListing
    listing_data = Employee


class AggregationListingView(ListingView):
    template_name = "demo/aggregation.html"
    context_classes = (
        Aggregation1Listing,
        Aggregation2Listing,
        Aggregation3Listing,
        Aggregation5Listing,
        Employee,
    )
    extra_context = dict(numbers_matrix=numbers_matrix)


class AjaxListingView(ListingView):
    template_name = "demo/ajax.html"

    # Important note :
    # ListingView will detect all get_listing_instance_xxx() method
    # and will put returned instance in the template context under the name 'xxx'.
    # Below, 'listing1', 'listing2', 'listing3' will be
    # automatically accessible from template : no need to define a
    # get_context_data() method.
    # If you have only one listing, you can just define get_listing_instance() :
    # 'listing' will be automatically available at template side.
    def get_listing_instance_listing1(self):
        return EmployeeVariationsListing(
            Employee, per_page=5, exclude_columns="id", accept_ajax=True
        )

    def get_listing_instance_listing2(self):
        return Listing(
            Company,
            theme_spinner_icon="animate-spin listing-icon-spin3",
            per_page=5,
            exclude_columns="id",
            accept_ajax=True,
            toolbar="sortdropdown,perpagedropdown",
        )

    def get_listing_instance_listing_with_toolbars_and_variations(self):
        return ToolbarListing(Employee, accept_ajax=True)

    def get_listing_instance_listing4(self):
        return ModalListing(Employee, per_page=10, accept_ajax=True)


class TranslationListingView(ListingView):
    template_name = "demo/translation.html"
    listing_data = Employee
    columns_many_separator = _(" and ")
    exclude_columns = "id"


class SpeedTestListingView(TemplateView):
    template_name = "demo/speed_test.html"


class SpeedTest1ListingView(ListingView):
    template_name = "demo/speed_test1.html"
    listing_data = Employee
    per_page = 25
    select_columns = (
        "first_name,last_name,address,age,designation,"
        "salary,joined,gender,marital_status,have_car"
    )


# ---- django-tables2 speedtest ----------------
import django_tables2 as tables


class SpeedTest2Table(tables.Table):
    class Meta:
        model = Employee
        fields = (
            "first_name",
            "last_name",
            "address",
            "age",
            "designation",
            "salary",
            "joined",
            "gender",
            "marital_status",
            "have_car",
        )


class SpeedTest2ListingView(tables.SingleTableView):
    template_name = "demo/speed_test2.html"
    queryset = Employee.objects.all()
    table_class = SpeedTest2Table


# ----------------------------------------------


class ToolbarListingView(ListingView):
    template_name = "demo/toolbar.html"
    context_classes = (
        ToolbarListing,
        NoToolbarListing,
        Employee,
    )


class UploadListingView(ListingView):
    template_name = "demo/upload.html"
    listing_class = UploadListing
    listing_data = ProductImage


class FiltersListingIndexView(TemplateView):
    template_name = "demo/filters.html"


class FiltersListing1View(ListingView):
    template_name = "demo/filters1.html"

    def get_listing_instance(self):
        return FilterListing(Employee)


class FiltersListing2View(ListingView):
    template_name = "demo/filters2.html"
    context_classes = (Employee,)


class FiltersListing3View(ListingView):
    template_name = "demo/filters3.html"

    def get_listing_instance(self):
        return CellFilterListing(Employee)


class EditableListingIndexView(TemplateView):
    template_name = "demo/editable.html"


class EditableListing1View(ListingView):
    template_name = "demo/editable1.html"
    listing_data = Employee
    # You can also customize your listing directly in the view
    # So you do not need to create a specific listing class :
    exclude_columns = "id,company,interests"
    editable = True
    editable_columns = "all"
    per_page = 5
    gender__input_type = "radio"
    save_to_database = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["post_data"] = pp.pformat(self.request.POST)
        return context


class EditableListing2View(ListingView):
    template_name = "demo/editable2.html"

    def get_listing_instance_employees_listing(self):
        return Listing(
            Employee,
            exclude_columns="id,company,interests",
            editable=True,
            editable_columns="all",
            per_page=5,
            gender__input_type="radio",
            save_to_database=True,
        )

    def get_listing_instance_companies_listing(self):
        return Listing(
            Company,
            exclude_columns="id,logo",
            editable=True,
            editable_columns="all",
            per_page=5,
            save_to_database=True,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["post_data"] = pp.pformat(self.request.POST)
        return context

    def manage_listing_companies_listing_row_form_clean(self, form):
        if form.cleaned_data.get("name") == "Twiyo":
            raise ValidationError(
                gettext(
                    "Just to test the method "
                    "<tt>manage_listing_companies_listing_row_form_clean()</tt> "
                    ': do not use "Twiyo" in column "Name"'
                )
            )
        return form.cleaned_data


class EditableListing3View(EditableListing2View):
    template_name = "demo/editable3.html"
    update_success_redirect_url = LISTING_REDIRECT_NO_EDIT

    def get_listing_instance_employees_listing(self):
        listing = super().get_listing_instance_employees_listing()
        listing.editing = False
        listing.edit_on_demand = True
        return listing

    def get_listing_instance_companies_listing(self):
        listing = super().get_listing_instance_employees_listing()
        listing.editing = False
        listing.edit_on_demand = True
        listing.edit_on_demand_options = {"has_paginator": False}
        listing.editing_columns = "address,age"
        listing.action_button_edit_label = "Edit only addresses & ages"
        listing.action_button_update_label = "Save"
        return listing


class EditableListing4View(ToolbarListingView):
    template_name = "demo/editable4.html"
    update_success_redirect_url = LISTING_REDIRECT_NO_EDIT
    save_to_database = True

    def get_listing_instance_update_listing(self):
        return ToolbarUpdateListing(
            Employee,
            exclude_columns="id,company,interests",
            editable=True,
            editable_columns="all",
            per_page=5,
            gender__input_type="radio",
            save_to_database=True,
        )


class SelectableListingIndexView(ListingView):
    template_name = "demo/selectable.html"


class SelectableListing1View(ListingView):
    template_name = "demo/selectable1.html"
    listing_data = Employee
    exclude_columns = "id,company,interests"
    per_page = 5
    selectable = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["post_data"] = pp.pformat(self.request.POST)
        return context

    def manage_listing_selected_rows(self, listing):
        selected = listing.get_selected_rows()
        selected_str = gettext(" and ").join(selected)
        action_str = self.request.POST.get("action", "-")
        if not selected:
            messages.add_message(
                self.request,
                messages.INFO,
                gettext("You didn't select any row, action : {}".format(action_str)),
            )
        else:
            messages.add_message(
                self.request,
                messages.INFO,
                gettext(
                    "You selected row {}, action : {}".format(selected_str, action_str)
                ),
            )
        # here the place to make a HttpRedirect if you want


class SelectableListing2View(SelectableListing1View):
    template_name = "demo/selectable2.html"
    selectable = True
    selection_multiple = True


class SelectableListing3View(ListingView):
    template_name = "demo/selectable3.html"

    def get_listing_instance_employees_listing(self):
        return Listing(
            Employee,
            name="Employees",
            exclude_columns="id,company,interests",
            selectable=True,
            selection_position="left",
            selection_initial=2,
            per_page=5,
        )

    def get_listing_instance_companies_listing(self):
        return Listing(
            Company,
            name="Companies",
            exclude_columns="id",
            selectable=True,
            selection_position="right",
            selection_multiple=True,
            selection_initial=[3, 4],
            per_page=5,
        )

    def get_context_data(self, **kwargs):
        # employees_listing and companies_listing are already in the context
        # (get_listing_instance_xxx => xxx automatically put in the context)
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["post_data"] = pretty_format_querydict(self.request.POST)
        return context

    def manage_listing_selected_rows(self, listing):
        selected = listing.get_selected_rows()
        selected_str = gettext(" and ").join(selected)
        action_str = self.request.POST.get("action", "-")
        if not selected:
            messages.add_message(
                self.request,
                messages.INFO,
                gettext(
                    "Listing {} : You didn't select any row, action : {}".format(
                        listing.name, action_str
                    )
                ),
            )
        else:
            messages.add_message(
                self.request,
                messages.INFO,
                gettext(
                    "Listing {} : You selected row {}, action : {}".format(
                        listing.name, selected_str, action_str
                    )
                ),
            )
        # here the place to make a HttpRedirect if you want


class SelectableListing4View(ListingView):
    template_name = "demo/selectable4.html"

    def get_listing_instance_divrows_listing(self):
        return EmployeeDivListing(
            Employee,
            exclude_columns="id,company,interests",
            selectable=True,
            selection_mode="overlay",
            per_page=5,
        )

    def get_listing_instance_thumbnails_listing(self):
        return EmployeeThumbnailsListing(
            Employee,
            exclude_columns="id",
            selectable=True,
            selection_multiple=True,
            selection_mode="overlay",
            per_page=16,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["post_data"] = pretty_format_querydict(self.request.POST)
        return context


class SelectableListing5View(ListingView):
    template_name = "demo/selectable5.html"

    def get_listing_instance_divrows_listing(self):
        return EmployeeDivListing(
            Employee,
            name="Employees detailed listing",
            exclude_columns="id,company,interests",
            selectable=True,
            selection_mode="hover",
            per_page=5,
        )

    def get_listing_instance_thumbnails_listing(self):
        return EmployeeThumbnailsListing(
            Employee,
            name="Just employees thumbnails",
            exclude_columns="id",
            selectable=True,
            selection_multiple=True,
            selection_mode="hover",
            per_page=16,
        )

    def manage_listing_selected_rows(self, listing):
        selected = listing.get_selected_rows()
        selected_str = ", ".join(selected)
        action_str = self.request.POST.get("action", "-")
        if not selected:
            messages.add_message(
                self.request,
                messages.INFO,
                mark_safe(
                    gettext(
                        'Listing : "{}", action : {}, '
                        "You didn't select any row".format(listing.name, action_str)
                    )
                ),
            )
        else:
            messages.add_message(
                self.request,
                messages.INFO,
                mark_safe(
                    gettext(
                        '<b>Listing :</b> "{}", <b>action :</b> {}, '
                        "<b>rows :</b> {}".format(
                            listing.name, action_str, selected_str
                        )
                    )
                ),
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["post_data"] = pretty_format_querydict(self.request.POST)
        return context


class InsertableListingView(ListingView):
    template_name = "demo/insertable.html"
    listing_class = InsertableListing
    listing_data = Employee

    def manage_listing_insert_form_clean(self, form):
        cd = form.cleaned_data
        first_name = cd.get("first_name")
        last_name = cd.get("last_name")
        if first_name and last_name:
            if Employee.objects.filter(
                first_name=first_name, last_name=last_name
            ).exists():
                raise ValidationError(
                    mark_safe(
                        _("<b>{first_name} {last_name}</b> already exists").format(
                            first_name=first_name, last_name=last_name
                        )
                    )
                )

    def manage_listing_insert_form_clean_age(self, form):
        age = form.cleaned_data.get("age")
        if age is None or age < 0 or age > 130:
            raise ValidationError(_("Age must be between 0 and 130."))
        return age


class GroupByListingView(ListingView):
    template_name = "demo/group_by.html"

    def get_listing_instance(self):
        return GroupByListing(
            Employee.objects.values("have_car").annotate(count=Count("have_car")),
            sort="have_car",
        )


class EmployeeDetailView(DetailView):
    model = Employee
    template_name = "demo/employee_detail.html"


class CompanyDetailView(DetailView):
    model = Company
    template_name = "demo/company_detail.html"


class CompanyAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # # Don't forget to filter out results depending on the visitor !
        # if not self.request.user.is_authenticated:
        #     return Company.objects.none()

        qs = Company.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

    def get_result_label(self, result):
        return format_html("<b>{}</b><i>({})</i>", result.name, result.city)


class InterestAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # # Don't forget to filter out results depending on the visitor !
        # if not self.request.user.is_authenticated:
        #     return Company.objects.none()

        qs = Interest.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

    def get_result_label(self, result):
        return result.name
