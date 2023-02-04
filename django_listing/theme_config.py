#
# Created : 2023-02-03
#
# @author: Eric Lapouyade
#
import os
from .exceptions import InvalidListingConfiguration
from django.conf import settings

class ThemeConfigMeta(type):
    themes_name_to_class = {}

    def __new__(mcs, name, bases, attrs):
        cls = super(ThemeConfigMeta, mcs).__new__(mcs, name, bases, attrs)
        ThemeConfigMeta.themes_name_to_class[cls.theme_name] = cls
        return cls

    @classmethod
    def get_class(mcs, theme_name):
        config = mcs.themes_name_to_class.get(theme_name)
        if config is None:
            themes = ', '.join(mcs.themes_name_to_class.keys())
            raise InvalidListingConfiguration(
                f'Theme "{theme_name}" does not exist. Possible values : {themes}'
            )
        return config

class ThemeConfigBase(metaclass=ThemeConfigMeta):
    theme_name = 'default'

    theme_listing_class = 'django-listing'
    theme_action_button_class = 'btn btn-primary'
    theme_action_button_cancel_icon = ''
    theme_action_button_edit_icon = ''
    theme_action_button_update_icon = ''
    theme_action_button_upload_icon = ''
    theme_container_class = 'django-listing-container'
    theme_sort_asc_icon = 'listing-icon-angle-up'
    theme_sort_desc_icon = 'listing-icon-angle-down'
    theme_sort_none_icon = ''
    theme_spinner_icon = 'animate-spin listing-icon-spin2'
    theme_sortable_class = 'sortable'
    theme_sort_asc_class = 'asc'
    theme_sort_desc_class = 'desc'
    theme_button_class = 'btn btn-primary'
    theme_button_disabled_class = 'disabled'
    theme_button_active_class = 'active'
    theme_div_row_container_class = ''

    column_theme_header_class = ''
    column_theme_cell_class = ''
    column_theme_footer_class = ''
    column_theme_form_widget_class = 'form-control form-control-sm'
    column_theme_button_class = 'btn btn-primary btn-sm'

    paginator_theme_first_last_has_icon = True
    paginator_theme_first_last_has_text = True
    paginator_theme_first_icon = 'listing-icon-to-start-1'
    paginator_theme_last_icon = 'listing-icon-to-end-1'
    paginator_theme_fast_page_has_icon = True
    paginator_theme_fast_page_has_text = True
    paginator_theme_fast_prev_icon = 'listing-icon-fast-backward'
    paginator_theme_fast_next_icon = 'listing-icon-fast-forward'
    paginator_theme_prev_next_has_icon = True
    paginator_theme_prev_next_has_text = True
    paginator_theme_prev_icon = 'listing-icon-left-dir'
    paginator_theme_next_icon = 'listing-icon-right-dir'
    paginator_theme_button_a_class = 'page-link'
    paginator_theme_button_li_class = 'page-item'
    paginator_theme_button_text_class = 'button-text'

    toolbar_theme_button_class = 'btn btn-secondary'


class ThemeAttribute:
    def __init__(self, attrname):
        self.attrname = attrname

    def __get__(self, obj, objtype):
        config = settings.django_listing_settings.theme_config
        try:
            return getattr(config, self.attrname)
        except AttributeError as e:
            raise InvalidListingConfiguration(
                f'{self.attrname} does not exist in {config.__module__}.{config.__qualname__}'
            )


class ThemeTemplate(str):
    def __init__(self, template_name):
        self.template_name = template_name

    def __get__(self, obj, objtype):
        return self.__str__()

    def __str__(self):
        return os.path.join(
            'django_listing',
            settings.django_listing_settings.theme_config.theme_name,
            self.template_name
        )


class ThemeConfigBoostrap4(ThemeConfigBase):
    theme_name = 'bootstrap4'
