0.9.15 (2024-12-10)
-------------------
- Add default_value_func attribute to Filter object
- Better Filter.required value handling

0.9.14 (2024-12-09)
-------------------
- Add has_cell_filter_single column attribute

0.9.12 (2024-12-06)
-------------------
- Improve ActionsButtonsColumn

0.9.11 (2024-11-26)
-------------------
- Add offset_max param to avoid display lines with too high offset

0.9.10 (2024-10-31)
-------------------
- Fix export toolbar item

0.9.9 (2024-10-16)
------------------
- Do not override widget attribute data-related-model in forms

0.9.8 (2024-10-16)
------------------
- Better filters form POST request data handling
- Add has_nb_unfiltered_rows listing attribute

0.9.7 (2024-10-14)
------------------
- Accept listings with filters.form_attrs = {"method": "POST"}

0.9.6 (2024-10-11)
------------------
- Bottom action buttons now works with accept_ajax=True

0.9.5 (2024-09-25)
------------------
- Better mass-update management

0.9.4 (2024-09-23)
------------------
- No form clean on mass delete in attached form
- Add data-related-model in form fields html attributes if relevant

0.9.1 (2024-09-13)
------------------
- Better mass update management : now dynamic checkboxes are displayed
  to choose fields to update

0.8.5 (2024-09-10)
------------------
- If using django-modeltranslation, do not consider localized fields
- Raise exception when trying to add form errors in attached form proccessing
- Attached form can be sticky : add class "stick" to .attached-form-container
- Remove attached form validation errors on row selection
- Better css for attached form

0.7.40 (2024-08-26)
-------------------
- Improve BooleanColumn to manage not nullable booleans in attached forms
- Fix column form field parameters retrieval
- Auto show advanced filters if one or more are used
- Update translation
- Add form_layout_advanced, and advanced button for filters form
- Add object-link css class on cells in link_object_columns
- Add extra spans in attached form buttons for better customization
- Add title in attached form buttons
- Better autocomplete filters management
- Attached form buttons can now be on several lines
- Initialize some dicts/lists in __init__
- Give the possibility to patch json response data via
  listing_patch_json_response_data(data) method to be put in view
- Better ajax request context management
- Re-compute the current page records after processing attached form actions
- Add view context data on ajax rendering
- Sort SortSelectToolbarItem choices
- Improve checkbox selection
- Fix selection column to avoid duplicates
- New empty msg management + some little fixes
- Add MultipleForeignKeyFilter
- Fix filter reset button
- Update showcase poetry env
- Add some manage_listing_attached_form_clean* methods
- Fix up & down icons in SortSelectToolbarItem to be displayed on Firefox
- Add some documentions
- Add icons on buttons for filter form and attached form
- Update showcase poetry.lock
- Update showcase installation documentation
- Many little fixes
- Add a lot of documentation in the showcase
- Fix django_listing.js for autocomplete multi-select
- Add some documentation
- Fix to get context processors executed during POST rendering
- Add widget_class and widget_params for Filter
- Fix widget creation
- Fix attached form reset button
- Add per-action attached form initial data
- Trigger JS event on selection change
- Add qs-first & qs-last css class on relevant rows.
- Add AutoCompleteColumn
- Add attached_form customize method
- De-serialize data into UTF-8 in attached form.
- Fix #19
- Fix action column
- Add export toolbar button permission
- Add spinner while exporting listing to file
- Check export select file format to not be empty
- Better default listing name
- Exported file name has now a timestamp
- Sanitize strings for Excel export
- Columns to be exported are now customizable
- Use base64 for attached form serialization encoding
- Fix attached_form auto-fill
- Add animation on attached_form insert
- Fix pagination
- Improve insert button management in attached_form
- Fix group by
- Add ModelMethodRef and RelatedModelMethodRef
- Add AttachedForm feature with ajax autofill and actions processing

0.6.4 (2024-01-18)
------------------
- Improve listing insert form
- add no_foreignkey_link to ManyColumn class
- add range selection (press shift on second selection)
- fix FloatColumn
- fix gettext
- fix group-by buttons
- Many fixes when accept_ajax = True
- Add "Group By" and annotations feature

0.5.17 (2023-11-28)
-------------------
- Add FloatFilter
- Fix XSS issues on ForeignKeyColumns and LinkColumn
- Improve get_absolute_url() usage
- Improve default_value on Filter()
- Add default_value on Filter()
- Improve foreign key column title
- Fix word search with filter_queryset_method
- Fix listing export for Excel
- Better focus when using Select2 widget
- Strip HTML tags on data exports
- Fix exception management for Django 4
- Add add_one_day option on DateFilter
- Fix unexpected SQL query with ListingVariations
- Data Export works with active filters and ajax=True
- Add filter_queryset_method filter attribute
- Update fr translations
- Add links in ManyColumn if get_absolute_url() exists on related objects
- Add __url_func parameter for edit/delete/view action buttons

0.0.28 (2023-06-27)
-------------------
- Add AutocompleteMultipleForeignKeyFilter
- Add ForeignKeyFilter and AutocompleteForeignKeyFilter
- Added edit and delete action buttons
- Fixed action button "see details" modal
- Improved CSS for small device
- Auto-detect many-to-many model fields if present in select_columns
- Fixed choices widgets
- Improved radio and checkbox in filter form
- Fixed ModelColumns
- Added LineNumberColumn()
- Use scss to generate css files
- Added showcase with many demo pages see showcase/README.rst
- Fixed bad form closing
- Fixed ListingVariation with Ajax
- Added django-like filter syntax for sequences
- Added JsonDateTimeColumn class
- Added support for python 3.10
- Added possibility to create custom action button linked with listing method

0.0.7 (2020-07-14)
------------------
- First running version

0.0.1 (2018-02-03)
------------------
- Skeleton commit
