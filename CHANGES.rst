0.7.40 (2024-08-26)
-------------------
- Improve BooleanColumn to manage not nullable booleans in attached forms

0.7.39 (2024-08-26)
-------------------
- Fix column form field parameters retrieval

0.7.38 (2024-08-08)
-------------------
- Auto show advanced filters if one or more are used
- Update translation

0.7.37 (2024-07-23)
-------------------
- Add form_layout_advanced, and advanced button for filters form

0.7.36 (2024-07-17)
-------------------
- Add object-link css class on cells in link_object_columns

0.7.35 (2024-07-09)
-------------------
- Add extra spans in attached form buttons for better customization

0.7.34 (2024-07-08)
-------------------
- Add title in attached form buttons

0.7.33 (2024-07-05)
-------------------
- Better autocomplete filters management

0.7.32 (2024-07-03)
-------------------
- Attached form buttons can now be on several lines

0.7.31 (2024-07-02)
-------------------
- Initialize some dicts/lists in __init__

0.7.30 (2024-06-21)
-------------------
- Give the possibility to patch json response data via
  listing_patch_json_response_data(data) method to be put in view
- Better ajax request context management

0.7.29 (2024-06-20)
-------------------
- Re-compute the current page records after processing attached form actions

0.7.28 (2024-06-14)
-------------------
- Add view context data on ajax rendering

0.7.27 (2024-05-24)
-------------------
- Sort SortSelectToolbarItem choices
- Improve checkbox selection
- Fix selection column to avoid duplicates
- New empty msg management + some little fixes

0.7.26 (2024-05-14)
-------------------
- Add MultipleForeignKeyFilter
- Fix filter reset button
- Update showcase poetry env

0.7.25 (2024-04-29)
-------------------
- Add some manage_listing_attached_form_clean* methods

0.7.24 (2024-04-18)
-------------------
- Fix up & down icons in SortSelectToolbarItem to be displayed on Firefox
- Add some documentions

0.7.23 (2024-04-18)
-------------------
- Add icons on buttons for filter form and attached form

0.7.21 (2024-04-16)
-------------------
- Update showcase poetry.lock
- Update showcase installation documentation

0.7.20 (2024-04-15)
-------------------
- Many little fixes
- Add a lot of documentation in the showcase

0.7.18 (2024-03-29)
-------------------
- Fix django_listing.js for autocomplete multi-select
- Add some documentation

0.7.17 (2024-03-13)
-------------------
- Fix to get context processors executed during POST rendering

0.7.16 (2024-03-13)
-------------------
- Add widget_class and widget_params for Filter
- Fix widget creation
- Fix attached form reset button

0.7.15 (2024-03-12)
-------------------
- Add per-action attached form initial data
- Trigger JS event on selection change

0.7.12 (2024-03-11)
-------------------
- Add qs-first & qs-last css class on relevant rows.
- Add AutoCompleteColumn
- Add attached_form customize method

0.7.11 (2024-03-01)
-------------------
- De-serialize data into UTF-8 in attached form.

0.7.10 (2024-02-29)
-------------------
- Fix #19
- Fix action column

0.7.9 (2024-02-26)
------------------
- Add export toolbar button permission

0.7.8 (2024-02-21)
------------------
- Add spinner while exporting listing to file
- Check export select file format to not be empty
- Better default listing name
- Exported file name has now a timestamp

0.7.7 (2024-02-20)
------------------
- Sanitize strings for Excel export
- Columns to be exported are now customizable

0.7.5 (2024-02-19)
------------------
- Use base64 for attached form serialization encoding

0.7.4 (2024-02-16)
------------------
- Fix attached_form auto-fill

0.7.3 (2024-02-08)
------------------
- Add animation on attached_form insert
- Fix pagination

0.7.2 (2024-02-08)
------------------
- Improve insert button management in attached_form

0.7.1 (2024-02-07)
------------------
- Fix group by
- Add ModelMethodRef and RelatedModelMethodRef

0.7.0 (2024-02-02)
------------------
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
