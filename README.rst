==============
django-listing
==============

.. image:: https://raw.githubusercontent.com/elapouya/django-listing/master/docs/_static/readme_intro1.png
.. image:: https://raw.githubusercontent.com/elapouya/django-listing/master/docs/_static/readme_intro2.png

Django app for building HTML listings / tables, it includes many features :

* Any iterable, Django QuerySet or model can be used.
* Most listings can be configured into a template file without touching a python file
* A class-based ListingView is provided if you want to code a listing at python side
* It as an Ajax mode to save requests to the server
* Uses JQuery if ajax is activated
* Customized for Bootstrap by default, but can be easily customized in many way (templates, icons, etc...)
* You can select columns to display, columns title, default sorting etc..
* Pagination is highly customizable (buttons to display, goto page, ellipsis, icons et labels)
* Rows can be <div> instead of <tr>, so it is possible to format data in many ways
* A lot of column types are provided, they are automatically created when a
  QuerySet or a model is provided
* Columns are class-bases and one can create custom ones
* Columns manage One-to-many, Many-to-many and foreign relations
* Provides aggregation columns : sum, avg, min, max values
* Provides page-level and global aggregation : sum, avg, min, max values displayed at listing last row
* Provides columns to make a link to the object, a custom link, checkbox, select box, text input...
* Provides "action column" that comes with many actions : show, edit, delete, move up, move down...
* is able to manage multiple variations to present data in multiple way at the same place
  (text only listing, text+image listing, image only listing for example)
* Uses Django translation framework : one can translate the listing as needed
* Toolbars can be added at the top and/or at the bottom to make actions
* Built-in toolbar action are : sorting, select a listing variation, number of rows per page,
  export data. They are customizable.
* Toolbar items are class-based : one can create a custom one easily
* django-listing can automatically create a filter form (aka search form)
* Listing rows can be selectable in order to apply some actions
* Listings can be editable for mass updates
* django-listing can automatically create a form for inserting data to database
* One can upload files/images into a listing, it uses DropzoneJS (Work in progress)
* ListingView can manage itself database inserting, editing, deleting, filtering, uploads and actions :
  no need to develop any code for that.
* django-listing comes with hundreds of icons as a scalable font
* django-listing is faster than django-table2


Showcase
--------

A demo is included in source code, you will need `poetry <https://python-poetry.org/docs/>`_ to install python environment::

    curl -sSL https://install.python-poetry.org | python3 -

To install the python envionment, go to django-listing source code root directory, then::

    cd showcase
    poetry install

Check you are in ``showcase/`` directory, then start the Django from poetry environment::

    poetry run python manage.py runserver 8123

A sqlite database is already included, you do not have to make any migration,
just open your brower at http://localhost:8123


License
-------
Django-listing is licensed under the GPLv3 license for all open source applications.
A commercial license is required for all commercial applications or non-open applications

See `LICENSE.rst <https://github.com/elapouya/django-listing/blob/master/LICENSE.rst>`_ file for more informations.


Documentation
-------------

Please, `read the doc <http://django-listing.readthedocs.org>`_  (Work in progress)