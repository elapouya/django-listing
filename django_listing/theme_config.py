#
# Created : 2023-02-03
#
# @author: Eric Lapouyade
#
import os

from django.conf import settings

from .exceptions import InvalidListingConfiguration


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
            themes = ", ".join(mcs.themes_name_to_class.keys())
            raise InvalidListingConfiguration(
                f'Theme "{theme_name}" does not exist. Possible values : {themes}'
            )
        return config


class ThemeConfigBase(metaclass=ThemeConfigMeta):
    theme_name = "default"  # to select the right directories for templates and django_listing.css
    theme_fallback_name = "default"  # to compute fallback directory path to search templates if not existing in theme directory

    # css classes
    theme_class = "theme-standard"

    # fmt: off
    theme_action_button_cancel_icon = ""
    theme_action_button_class = "btn btn-primary"
    theme_action_button_edit_icon = ""
    theme_action_button_update_icon = ""
    theme_action_button_upload_icon = ""
    theme_button_active_class = "active"
    theme_button_class = "btn btn-primary"
    theme_button_disabled_class = "disabled"
    theme_container_class = "django-listing-container"
    theme_div_row_container_class = ""
    theme_listing_class = "django-listing"  # do not modify
    theme_row_class = "row-container"
    theme_sort_asc_class = "asc"
    theme_sort_asc_icon = "listing-icon-angle-up"
    theme_sort_desc_class = "desc"
    theme_sort_desc_icon = "listing-icon-angle-down"
    theme_sort_none_icon = ""
    theme_sortable_class = "sortable"
    theme_sorted_class = "sorted"
    theme_spinner_icon = "animate-spin listing-icon-spin2"
    theme_localized_small_device_styles_width = "991px"

    column_theme_button_class = "btn btn-primary btn-sm"
    column_theme_button_link_class = "btn btn-primary btn-sm"
    column_theme_link_class = ""
    column_theme_cell_class = ""
    column_theme_cell_with_filter_icon = "listing-icon-filter"
    column_theme_footer_class = ""
    column_theme_form_checkbox_widget_class = "form-control form-control-sm"
    column_theme_form_radio_widget_class = "form-control form-control-sm"
    column_theme_form_select_widget_class = "form-control form-control-sm"
    column_theme_form_widget_class = "form-control form-control-sm"
    column_theme_header_class = ""

    paginator_theme_button_a_class = "page-link"
    paginator_theme_button_li_class = "page-item"
    paginator_theme_button_text_class = "button-text"
    paginator_theme_fast_next_icon = "listing-icon-fast-forward"
    paginator_theme_fast_page_has_icon = True
    paginator_theme_fast_page_has_text = True
    paginator_theme_fast_prev_icon = "listing-icon-fast-backward"
    paginator_theme_first_icon = "listing-icon-to-start-1"
    paginator_theme_first_last_has_icon = True
    paginator_theme_first_last_has_text = True
    paginator_theme_last_icon = "listing-icon-to-end-1"
    paginator_theme_next_icon = "listing-icon-right-dir"
    paginator_theme_prev_icon = "listing-icon-left-dir"
    paginator_theme_prev_next_has_icon = True
    paginator_theme_prev_next_has_text = True

    toolbar_theme_button_class = "btn btn-secondary"

    filters_theme_form_submit_icon = "listing-icon-filter"
    filters_theme_form_reset_icon = "listing-icon-cancel"
    filters_theme_form_submit_class = "filters-nav btn btn-primary submit-button"
    filters_theme_form_reset_class = "filters-nav btn btn-primary reset-button"
    filters_theme_form_advanced_down_icon = "listing-icon-down-open"
    filters_theme_form_advanced_up_icon = "listing-icon-up-open"
    filters_theme_form_advanced_class = "filters-nav btn btn-secondary advanced-button"

    attached_form_reset_button_class = "attached-form-nav btn btn-primary submit-button"
    attached_form_submit_button_class = "attached-form-nav btn btn-primary submit-button"
    attached_form_delete_all_button_class = "attached-form-nav btn btn-primary submit-button"
    attached_form_delete_button_class = "attached-form-nav btn btn-primary submit-button disabled-if-no-selection"
    attached_form_clear_button_class = "attached-form-nav btn btn-primary submit-button"
    attached_form_insert_button_class = "attached-form-nav btn btn-primary submit-button"
    attached_form_duplicate_button_class = "attached-form-nav btn btn-primary submit-button disabled-if-no-selection"
    attached_form_update_button_class = "attached-form-nav btn btn-primary submit-button disabled-if-no-selection"
    attached_form_update_all_button_class = "attached-form-nav btn btn-primary submit-button"
    attached_form_reset_button_icon = "listing-icon-reset"
    attached_form_submit_button_icon = "listing-icon-right-dir"
    attached_form_delete_all_button_icon = "listing-icon-remove-multiple"
    attached_form_delete_button_icon = " listing-icon-minus-squared"
    attached_form_clear_button_icon = "listing-icon-erase"
    attached_form_insert_button_icon = "listing-icon-plus-1"
    attached_form_duplicate_button_icon = "listing-icon-duplicate"
    attached_form_update_button_icon = "listing-icon-edit-pen-filled"
    attached_form_update_all_button_icon = "listing-icon-update-multiple"
    # fmt: on


class ThemeAttribute:
    # This is a descriptor to dynamically get theme information
    def __init__(self, attrname):
        self.attrname = attrname

    def __get__(self, obj, objtype):
        try:
            # TODO : change this line to get the right theme_config from a theme name given by user
            config = settings.django_listing_settings.theme_config
            return getattr(config, self.attrname)
        except AttributeError as e:
            raise InvalidListingConfiguration(
                f"{self.attrname} does not exist in {config.__module__}.{config.__qualname__}"
            )


class ThemeTemplate(str):
    def __init__(self, template_name):
        self.template_name = template_name

    @classmethod
    def get(cls, template_name):
        path = os.path.join(
            settings.django_listing_settings.name,
            settings.django_listing_settings.theme_config.theme_name,
            template_name,
        )
        full_path = os.path.join(
            settings.django_listing_settings.path,
            "templates",
            path,
        )
        if not os.path.exists(full_path):
            path = os.path.join(
                settings.django_listing_settings.name,
                settings.django_listing_settings.theme_config.theme_fallback_name,
                template_name,
            )
        return path

    def __get__(self, obj, objtype):
        return self.get(self.template_name)

    def __str__(self):
        return self.get(self.template_name)


class ThemeConfigBoostrap4(ThemeConfigBase):
    theme_name = "bootstrap4"
    theme_class = "theme-bootstrap4"


class ThemeConfigBoostrap5(ThemeConfigBase):
    theme_name = "bootstrap5"
    theme_class = "theme-bootstrap5"

    theme_row_class = "row-container d-grid d-lg-table-row"

    column_theme_form_select_widget_class = "form-select form-select-sm"
    column_theme_form_checkbox_widget_class = "form-check-input"
    column_theme_form_radio_widget_class = "form-check-input"
