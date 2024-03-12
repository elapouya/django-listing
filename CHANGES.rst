0.7.14 (2024-03-12)
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
