0.6.2 (2024-01-10)
-------------------
- fix FloatColumn
- fix gettext
- fix group-by buttons

0.6.1 (2024-01-09)
-------------------
- Many fixes when accept_ajax = True

0.6.0 (2024-01-08)
-------------------
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
