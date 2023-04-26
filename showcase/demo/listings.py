#
# Created : 2018-02-16
#
# @author: Eric Lapouyade
#

from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_listing import *
from django.core.exceptions import ValidationError
from datetime import datetime
from .models import *
from .data import *


# I tried to make different syntax of listing classes so you will be able
# to choose the one you prefer...

class EmployeeListing(Listing):
    columns = Columns(
        Column('first_name'),
        Column('last_name'),
        Column('address'),
        Column('age'),
    )
    per_page = 5
    paginator_hide_disabled_buttons=True


class EmployeeModelListing(Listing):
    columns = ModelColumns(Employee)
    per_page = 5
    exclude_columns = 'id,interests'
    #theme = 'red-theme'  # the top div container will have this class
    attrs = {'class':'table'}  # Only 'table' (no table-bordered)
    #paginator_template_name = 'demo/paginator_bootstrap.html'


class PaginationListing(Listing):
    columns = Columns(
        Column('first_name'),
        Column('last_name'),
        Column('address'),
        Column('age'),
    )
    per_page = 5


class NoTextButtonPaginationListing(PaginationListing):
    paginator_class = NoTextButtonPaginator
    paginator_has_first_last = True
    paginator_fast_page_step = 5


class NoIconButtonPaginationListing(PaginationListing):
    paginator_class = NoIconButtonPaginator
    paginator_has_first_last = True
    paginator_fast_page_step = 5


class CustomButtonsPaginationListing(PaginationListing):
    # go to http://localhost:8000/fonticons/ to see icons name
    paginator_has_first_last = True
    paginator_fast_page_prev_tpl = 'Previous {step} pages'
    paginator_fast_page_next_tpl = 'Next {step} pages'
    paginator_fast_page_step = 10
    paginator_theme_fast_page_has_icon = False
    paginator_theme_next_icon = 'listing-icon-right'
    paginator_theme_prev_icon = 'listing-icon-left'
    paginator_prev_text = 'Previous page'
    paginator_next_text = 'Next page'
    paginator_theme_first_icon = 'listing-icon-to-start-alt'
    paginator_theme_last_icon = 'listing-icon-to-end-alt'
    paginator_first_text = 'First page'
    paginator_last_text = 'Last page'


class EllipsisPaginationListing(PaginationListing):
    paginator_has_prev_next = False
    paginator_page_scale_size = 5
    paginator_page_scale_ellipsis = 3
    paginator_has_page_info = False
    page = 33


class SimpleListing(Listing):
    # If no columns are specified, django_listing will auto-detect them
    # based on data provided (list of dicts, list of lists, model, query set etc...
    per_page = 10


class EmployeeDivListing(DivListing):
    # Only these columns will be listed in the table header
    # Nevertheless, the full record information will be available
    # in the div_row_template
    columns = Columns(
        Column('first_name'),
        Column('last_name'),
        Column('address'),
        Column('age'),
    )
    per_page = 10
    div_template_name = 'demo/div_row.html'
    attrs = {'class': 'div-striped div-hover div-bordered'}


class EmployeeThumbnailsListing(DivListing):
    div_template_name = 'demo/thumbnails.html'
    attrs = {'class':''}
    # will add the 'thumbnail' class to the container
    # means that one have to set 'div.row-container.thumbnail'
    # in .css to modify the look
    theme_div_row_container_class = 'thumbnail'
    per_page = 16


class EmployeeVariationsListing(ListingVariations):
    variations_classes = (SimpleListing,
                      EmployeeDivListing,
                      EmployeeThumbnailsListing)


class BoolColumnsListing(Listing):
    columns = ModelColumns(BooleanModel)
    exclude_columns = 'id'


class BoolChoicesImgColumnsListing(Listing):
    select_columns = 'first_name,last_name,age,have_car,gender'
    have_car__true_tpl = ( '<img src="{STATIC_URL}demo/images/car.png"'
                           'title="Have a car">')
    have_car__false_tpl = ('<img src="{STATIC_URL}demo/images/pedestrian.png" '
                           'title="Do not own a car">')
    have_car__theme_cell_class = 'text-center'
    gender__choices = (
        ('Male', '<img src="{STATIC_URL}demo/images/male.png" '
                 'title="{value}">'),
        ('Female', '<img src="{STATIC_URL}demo/images/female.png" '
                   'title="{value}">'),
    )
    gender__theme_cell_class = 'text-center'


class OneToManyListing(Listing):
    columns = Columns(
        Column('company', data_key='name', header="Company's name"),
        ManyColumn('employees',
                   data_key='employee_set',  # with django, to get the reverse of a foreign key (= one to many), you use the model in lower case + '_set'
                   cell_filter=lambda x:x.all()[:10],  # only the 10 first employees (The .all() is a Django syntax to get all items from a queryset)
                   cell_map=lambda x:force_str(x).title(),  # item by item : transform in text and put uppercase on first letter
                   cell_reduce=lambda x:' and '.join(x) + '...'),  # turn the items into a single string by putting ' and ' between items and finally add '...'
    )


class ManyToManyListing(Listing):
    columns = Columns(
        Column('employee', data_key='__str__', header="Employee's name"),  # See Employee.__str__() : Method got get object's verbose name for Django
        ManyColumn('interests'),  # use default cell_filter, cell_map and cell_reduce ( join list with ', ' )
    )


class DatetimeListing(Listing):
    columns = Columns(
        Column('first_name'),
        Column('last_name'),
        Column('address'),
        DateColumn('joined_date', data_key='joined',header='Joined (date)'),
        DateTimeColumn('Now',
                       cell_value=lambda col,rec:datetime.now(),
                       header='Now (datetime)'),
        TimeColumn('joined_time',
                   cell_value=lambda col,rec:datetime.now(),
                   time_format='H:i:s',
                   header='Now (time with sec)'),
    )


class LinkObjectListing(Listing):
    select_columns = 'first_name,last_name,age,address'
    columns = ModelColumns(Employee,
        # force first_name and last_name column to view Employee
        LinkObjectColumn('first_name'),
        LinkObjectColumn('last_name'),
    )


class LinksListing(Listing):
    columns = ModelColumns(Employee,
        # The 'address' column is a normal column, if you want to transform it
        # you just have to redeclare it after the model : it will be replaced.
        # Here, I have chosen to turn it into a link to google map.
        # Note the syntax in the href_tpl : {rec[address|urlencode]} means :
        # from rec take address and urlencode the value.
        LinkColumn('address',href_tpl=(
            'https://www.google.com/maps/search/'
            '?api=1&query={rec[address|urlencode]}')),
        params=dict(
           company={'link_attrs': {'target': '_blank'}}
        )
    )


class ForeignKeyListing(Listing):
    model = Employee
    exclude_columns = 'id'
    # here I specified href_tpl for company column
    # to override calling get_absolute_url()
    # in string template do not use dotted notation directly
    # ie : {the.dotted.notation} instead use {rec[the.dotted.notation]}
    company__href_tpl = 'https://www.bing.com/search?q={rec[company.name]}'
    company__link_attrs = {'target': '_blank'}


class TotalListing(Listing):
    columns = SequenceColumns(numbers_matrix)
    columns += [ TotalColumn(),
                 AvgColumn(precision=1),
                 MaxColumn(),
                 MinColumn() ]
    paginator_hide_single_page = True  # for single page listings, better remove paginator.


class ModalListing(Listing):
    paginator_has_first_last = True
    columns = Columns(
        Column('first_name'),
        Column('last_name'),
        Column('address'),
        ButtonColumn(
            'button',
            label='Select',
            header='Click to select',
            widget_attrs={'data-bs-dismiss': 'modal'},
        ),
    )
    # One can specify a little jquery snippet to be executed
    # when the document will be ready :
    onready_snippet = """
        $('body').on('click', '#listing4-id .col-button button', function() {
            let employee = $(this).closest('tr').find('td.col-first_name ').text()
            + ' ' + $(this).closest('tr').find('td.col-last_name ').text()
            + ' (' + $(this).closest('tr').find('td.col-address ').text() + ')';
            $('#employee-selected').val(employee);
            $('#employee-selected-pk').val($(this).closest('tr').attr('data-pk'));
        });
    """


class WidgetsColumnsListing(Listing):
    id = 'widget-listing'
    columns = Columns(
        Column('first_name'),
        Column('last_name'),
        CheckboxColumn('have_car'),
        SelectColumn('SelectBox',choices=(
            ('','Please choose...'),
            ('good', 'The good'),
            ('bad', 'The bad'),
            ('ugly', 'The ugly'),
        )),
        ButtonColumn('button', label='Copy here -->'),  # will have css class 'col-button'
        InputColumn('some_input_text',widget_attrs={
            'type':'text',
            'style':'width:120px'}),
        Column('custom1', # will call self.render_custom1() automatically if it exists
               sortable=False,
               header=mark_safe('Custom<br>column 1')),
        Column('custom2',
               sortable=False,
               header=mark_safe('Custom<br>column 2'),
               # custom cell value (lambda function) :
               cell_value=lambda col,rec: rec.format_str('{first_name} {last_name}'))
    )
    # One can specify a little jquery snippet to be executed
    # when the document will be ready :
    onready_snippet = """
        $('#widget-listing .col-button button').on('click',function() {
            var selected=$(this).closest('tr').find('select option:selected').text();
            $(this).closest('tr').find('input[type="text"]').val(selected);
        });
    """
    # define a custom rendering for column 'custom1'
    def render_custom1(self, rec):
        odd = bool(rec.get_index() % 2)
        if odd:
            return '<td class="text-success">Odd line</td>'
        else:
            return '<td class="text-danger">Even line</td>'


class ActionsColumnListing(Listing):
    id = 'employee-rank'
    sort = 'rank'
    paginator_has_first_last = True
    paginator_page_scale_size = 9
    paginator_has_page_info = False
    actions__move_down__key = 'rank'
    columns = Columns(
        Column('first_name'),
        Column('last_name'),
        Column('rank', header='Employee of the month rank'),
        ActionsButtonsColumn('actions',
            buttons='move_up,move_down,view_object,view_object_popup',
            buttons_has_text=False,
            move_up__field='rank',
            move_down__field='rank',
            view_object__title='See details (simple link to object.get_absolute_url())',
            view_object_popup__icon='listing-icon-zoom-in',
            view_object_popup__title='See details (Popup)',
            view_object_popup__layout = (
                '== Main informations ==;'
                'first_name,last_name;'
                '== Other informations ==;'
                'age,have_car;'
                'Rank:rank*2;'
                'company*2'
            ),

        ),
    )

class Aggregation1Listing(Listing):
    columns = SequenceColumns(numbers_matrix, aggregation='sum')
    has_footer = True


class Aggregation2Listing(Listing):
    columns = Columns(
        Column('col1', data_key=0),
        Column('col2', data_key=1, aggregation='sum'),
        Column('col3', data_key=2, aggregation='avg', footer_precision=1),  # 1 digit after the dot
        Column('col4', data_key=3, aggregation='min'),
        Column('col5', data_key=4, aggregation='max'),
        Column('col6', data_key=5),
    )
    has_footer = True


class Aggregation5Listing(Listing):
    columns = Columns(
        Column('col1', data_key=0),
        Column('col2', data_key=1, aggregation='global_sum'),
        Column('col3', data_key=2, aggregation='global_avg', footer_precision=1),  # 1 digit after the dot
        Column('col4', data_key=3, aggregation='global_min'),
        Column('col5', data_key=4, aggregation='global_max'),
        Column('col6', data_key=5),
    )
    has_footer = True

class Aggregation3Listing(Listing):
    columns = SequenceColumns(numbers_matrix)
    columns += [ TotalColumn(),
                 AvgColumn(precision=1),
                 MaxColumn(),
                 MinColumn() ]
    has_footer = True

class ToolbarSimpleListing(SimpleListing):
    per_page = 8


class ToolbarEmployeeDivListing(DivListing):
    div_template_name = 'demo/div_row.html'
    # override sorting choices (with tuples syntax)
    toolbar_sortselect__choices=(('first_name','First name A-Z'),
                                 ('-first_name','First name Z-A'),
                                 ('age','Youngest first'),
                                 ('-age','Oldest first'))
    attrs = {'class':'div-striped div-hover div-bordered'}
    per_page = 8


class ToolbarEmployeeThumbnailsListing(EmployeeThumbnailsListing):
    per_page = 16
    # override sorting choices (with one big string syntax)
    toolbar_sortselect__choices=('first_name:First name A-Z,'
                                 '-first_name:First name Z-A,'
                                 'age:Youngest first,'
                                 '-age:Oldest first')


class ToolbarEmployeeBigThumbnailsListing(ToolbarEmployeeThumbnailsListing):
    div_template_name = 'demo/big_thumbnails.html'
    per_page = 9
    toolbar_perpageselect__choices = '9,18,27,-1:All' #overrides ToolbarListing.toolbar PerPageSelectToolbarItem choices attribute
    theme_div_row_container_class = 'big-thumbnail'


class ToolbarListing(ListingVariations):
    variations_classes = (
        ToolbarSimpleListing,
        ToolbarEmployeeDivListing,
        ToolbarEmployeeThumbnailsListing,
        ToolbarEmployeeBigThumbnailsListing,
    )
    toolbar = Toolbar(
        ExportSelectToolbarItem(),
        SortSelectToolbarItem(),
        VariationsToolbarItem(
            labels=('Listing', 'Detailed', 'Thumbnails', 'Big thumbnails'),
            icons=('listing-icon-menu-2', 'listing-icon-th-list-4',
                   'listing-icon-th-3', 'listing-icon-th-large-2')),
        PerPageSelectToolbarItem(choices='8,16,32,64,-1:All'),
    )
    toolbar_placement = 'both'
    per_page = 8
    paginator_has_first_last = True
    exclude_columns = 'interests'


class ToolbarUpdateListing(Listing):
    toolbar = Toolbar(
        ExportSelectToolbarItem(),
        SortSelectToolbarItem(),
        PerPageSelectToolbarItem(choices='8,16,32,64,-1:All'),
        UpdateToolbarItem(),
    )
    toolbar_placement = 'both'
    per_page = 8
    paginator_has_first_last = True
    exclude_columns = 'id,company,interests'
    editable = True
    editable_columns = 'all'


class NoToolbarListing(ListingVariations):
    variations_classes = (
        ToolbarSimpleListing,
        ToolbarEmployeeDivListing,
        ToolbarEmployeeThumbnailsListing,
        ToolbarEmployeeBigThumbnailsListing,
    )

class FilterListing(Listing):
    filters = Filters(
        IntegerFilter('age1', filter_key='age__gte', label='Age from'),
        IntegerFilter('age2', filter_key='age__lte', label='to'),
        IntegerFilter('salary1', filter_key='salary__gte',
                                 label='Salary between'),
        IntegerFilter('salary2', filter_key='salary__lte', label='and'),
        DateFilter('joined1', filter_key='joined__gte',
                                 label='Joined between'),
        DateFilter('joined2', filter_key='joined__lte', label='and'),
        Filter('first_name', filter_key='first_name__icontains',
                             help_text='Case insensitive'),
        Filter('last_name', filter_key='last_name__icontains'),
        ChoiceFilter('marital_status', input_type='radio',
                                       no_choice_msg='Indifferent'),
        # Note : By default filter_key = filter name if not specified
        MultipleChoiceFilter('gender', input_type='checkbox',
                                       label='Gender')
        # For MultipleChoiceFilter '__in' will be added to filter_key if missing
    )
    filters.form_layout = ('age1,age2,salary1,salary2,joined1,joined2;'
                           'first_name,last_name;'
                           'marital_status,gender')
    filters.form_buttons = 'submit,reset'
    # remove default behaviour when there no row to display (remove the listing
    # and display the template 'empty_listing_template_name' )
    empty_listing_template_name = None
    # instead, display a string into the empty table itself.
    empty_table_msg = 'There is no employee corresponding to your criteria'
    per_page = 5
    exclude_columns = "interests"


class InsertableListing(Listing):
    per_page = 5
    sort = '-id'
    gender__input_type = 'radio'
    salary__min_value = 0
    columns_no_choice_msg = 'Please choose...'
    columns_label_suffix = ''
    save_to_database = True
    exclude_columns = "interests"


class UploadListing(DivListing):
    toolbar = Toolbar(
        PerPageSelectToolbarItem(choices='8,16,32,64,-1:All'),
    )
    toolbar_placement = 'both'
    has_upload = True
    per_page = 8
    paginator_has_first_last = True
    paginator_theme_button_text_class = 'd-none d-sm-inline' # hide paginator button text on small screen
    record_label = 'product image'
    div_template_name = 'demo/upload_thumbnails.html'
    attrs = {'class':''}
    # will add the 'thumbnail' class to the container
    # means that one have to set 'div.row-container.thumbnail'
    # in .css to modify the look
    theme_div_row_container_class = 'upload-thumbnail'



