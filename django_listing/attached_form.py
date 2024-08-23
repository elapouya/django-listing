#
# Created : 2018-04-04
#
# @author: Eric Lapouyade
#
import copy

from django import forms
from django.core.exceptions import ValidationError
from django.forms.fields import FileField
from django.template import loader
from django.utils.translation import gettext as _
from django.utils.translation import pgettext_lazy

from .context import RenderContext
from .exceptions import (
    InvalidAttachedForm,
    ListingException,
    InvalidListingConfiguration,
)
from .html_attributes import HTMLAttributes
from .theme_config import ThemeTemplate, ThemeAttribute
from .utils import init_dicts_from_class

__all__ = ["ATTACHED_FORM_PARAMS_KEYS", "AttachedForm"]

# Declare keys only for "Filters" object
ATTACHED_FORM_PARAMS_KEYS = {
    "action",
    "attached_form_name",
    "display_errors",
    "reset_button_label",
    "submit_button_label",
    "delete_all_button_label",
    "delete_button_label",
    "clear_button_label",
    "insert_button_label",
    "duplicate_button_label",
    "update_button_label",
    "update_all_button_label",
    "submit_action",
    "template_name",
    "django_form_class",
    "layout",
    "attrs",
    "buttons",
    "ListingBaseForm",
    "theme_reset_button_class",
    "theme_submit_button_class",
    "theme_delete_all_button_class",
    "theme_delete_button_class",
    "theme_clear_button_class",
    "theme_insert_button_class",
    "theme_duplicate_button_class",
    "theme_update_button_class",
    "theme_update_all_button_class",
    "theme_reset_button_icon",
    "theme_submit_button_icon",
    "theme_delete_all_button_icon",
    "theme_delete_button_icon",
    "theme_clear_button_icon",
    "theme_insert_button_icon",
    "theme_duplicate_button_icon",
    "theme_update_button_icon",
    "theme_update_all_button_icon",
}


class ListingBaseForm(forms.BaseForm):
    do_not_clean = False

    def _clean_fields(self):
        if self.do_not_clean:
            return
        for name, field in self.fields.items():
            if field.disabled:
                value = self.get_initial_for_field(field, name)
            else:
                value = field.widget.value_from_datadict(
                    self.data, self.files, self.add_prefix(name)
                )
            try:
                if isinstance(field, FileField):
                    initial = self.get_initial_for_field(field, name)
                    value = field.clean(value, initial)
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value

                method = None
                view = self.listing.get_view()
                if view:
                    method_name = f"manage_listing_{view.listing.id[:-3]}_{self.form_name}_clean_{name}"
                    method = getattr(view, method_name, None)
                    if not method:
                        method_name = f"manage_listing_{self.form_name}_clean_{name}"
                        method = getattr(view, method_name, None)
                    if not method:
                        method_name = f"manage_listing_attached_form_clean_{name}"
                        method = getattr(view, method_name, None)
                if not method:
                    method_name = f"{self.form_name}_clean_{name}"
                    method = getattr(self.listing, method_name, None)
                if not method:
                    method_name = f"manage_listing_attached_form_clean_{name}"
                    method = getattr(self.listing, method_name, None)
                if method:
                    value = method(self)
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)

    def _clean_form(self):
        if self.do_not_clean:
            return
        try:
            method = None
            view = self.listing.get_view()
            if view:
                method_name = (
                    f"manage_listing_{view.listing.id[:-3]}_{self.form_name}_clean"
                )
                method = getattr(view, method_name, None)
                if not method:
                    method_name = f"manage_listing_{self.form_name}_clean"
                    method = getattr(view, method_name, None)
                if not method:
                    method_name = f"manage_listing_attached_form_clean"
                    method = getattr(view, method_name, None)
            if not method:
                method_name = f"{self.form_name}_clean"
                method = getattr(self.listing, method_name, None)
            if not method:
                method_name = f"attached_form_clean"
                method = getattr(self.listing, method_name, None)
            if method:
                cleaned_data = method(self)
            else:
                cleaned_data = self.cleaned_data
        except ValidationError as e:
            self.add_error(None, e)
        else:
            if cleaned_data is not None:
                self.cleaned_data = cleaned_data


class AttachedForm:
    id = None
    action = "attached_form"
    display_errors = True
    form_base_class = ListingBaseForm
    django_form_class = None
    reset_button_label = pgettext_lazy("Attached form", "Reset")
    submit_button_label = pgettext_lazy("Attached form", "Add")
    submit_action = "insert"
    delete_all_button_label = pgettext_lazy("Attached form", "Delete ALL")
    delete_button_label = pgettext_lazy("Attached form", "Delete selected")
    clear_button_label = pgettext_lazy("Attached form", "Clear the form")
    insert_button_label = pgettext_lazy("Attached form", "Insert")
    duplicate_button_label = pgettext_lazy("Attached form", "Duplicate")
    update_button_label = pgettext_lazy("Attached form", "Update selected")
    update_all_button_label = pgettext_lazy("Attached form", "Update ALL")
    template_name = ThemeTemplate("attached_form.html")
    layout = None
    listing = None
    buttons = "reset,submit"
    name = "attached_form"
    attrs = {"class": "listing-form"}
    # fmt: off
    theme_reset_button_class = ThemeAttribute("attached_form_reset_button_class")
    theme_submit_button_class = ThemeAttribute("attached_form_submit_button_class")
    theme_delete_all_button_class = ThemeAttribute("attached_form_delete_all_button_class")
    theme_delete_button_class = ThemeAttribute("attached_form_delete_button_class")
    theme_clear_button_class = ThemeAttribute("attached_form_clear_button_class")
    theme_insert_button_class = ThemeAttribute("attached_form_insert_button_class")
    theme_duplicate_button_class = ThemeAttribute("attached_form_duplicate_button_class")
    theme_update_button_class = ThemeAttribute("attached_form_update_button_class")
    theme_update_all_button_class = ThemeAttribute("attached_form_update_all_button_class")
    theme_reset_button_icon = ThemeAttribute("attached_form_reset_button_icon")
    theme_submit_button_icon = ThemeAttribute("attached_form_submit_button_icon")
    theme_delete_all_button_icon = ThemeAttribute("attached_form_delete_all_button_icon")
    theme_delete_button_icon = ThemeAttribute("attached_form_delete_button_icon")
    theme_clear_button_icon = ThemeAttribute("attached_form_clear_button_icon")
    theme_insert_button_icon = ThemeAttribute("attached_form_insert_button_icon")
    theme_duplicate_button_icon = ThemeAttribute("attached_form_duplicate_button_icon")
    theme_update_button_icon = ThemeAttribute("attached_form_update_button_icon")
    theme_update_all_button_icon = ThemeAttribute("attached_form_update_all_button_icon")
    # fmt: on

    def __init__(self, name=None, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.name = name or "attached_form"
        self._form = None
        self._render_initialized = False
        init_dicts_from_class(
            self,
            [
                "attrs",
            ],
        )

    def is_render_initialized(self):
        return self._render_initialized

    def bind_to_listing(self, listing):
        form = self
        if form.listing != listing:
            form = copy.deepcopy(self)  # important
        form.init(listing, *self.init_args, **self.init_kwargs)
        return form

    def set_listing(self, listing):
        self.listing = listing

    def set_kwargs(self, **kwargs):
        for k in ATTACHED_FORM_PARAMS_KEYS:
            listing_key = "{}_{}".format(self.name, k)
            if k in kwargs:
                setattr(self, k, kwargs[k])
            elif hasattr(self.listing, listing_key):
                setattr(self, k, getattr(self.listing, listing_key))

    def init(self, listing, *args, **kwargs):
        self.set_listing(listing)
        self.set_kwargs(**kwargs)
        if isinstance(self.layout, str):
            # transform layout string into list of lists
            self.layout = list(map(lambda s: s.split(","), self.layout.split(";")))
        if self.layout:
            self.listing.form_model_fields = []
            self.listing.form_serialize_cols = []
            self.listing.form_no_autofill_cols = []
            for row in self.layout:
                for field_name in row:
                    field_name = field_name.strip()
                    col = self.listing.columns.get(field_name)
                    if col:
                        if col.model_field:
                            self.listing.form_model_fields.append(col.model_field.name)
                        if col.form_field_serialize:
                            self.listing.form_serialize_cols.append(col)
                        if col.form_no_autofill:
                            self.listing.form_no_autofill_cols.append(col.name)
            layout_str = ";".join(map(lambda l: ",".join(l), self.layout))
            self.listing.add_form_input_hiddens(
                attached_form_layout=layout_str,
                attached_form_name=self.name,
                action=self.action,
                **self.get_form_hiddens(),
            )
        self.init_buttons()

    def init_buttons(self):
        if isinstance(self.buttons, str):
            self.buttons = list(map(lambda s: s.split(","), self.buttons.split(";")))
        else:
            self.buttons = copy.deepcopy(self.buttons)
        for buttons_line in self.buttons:
            for i, button in enumerate(buttons_line):
                if isinstance(button, str):
                    # Will try to replace with a relevant tuple
                    # must be defined has (action, label, icon css class, button css class)
                    if button == "reset":
                        button = (
                            "reset",
                            self.reset_button_label,
                            self.theme_reset_button_icon,
                            self.theme_reset_button_class,
                        )
                    elif button == "submit":
                        button = (
                            self.submit_action,
                            self.submit_button_label,
                            self.theme_submit_button_icon,
                            self.theme_submit_button_class,
                        )
                    elif hasattr(self, f"{button}_button_label"):
                        button = (
                            button,
                            getattr(self, f"{button}_button_label"),
                            getattr(self, f"theme_{button}_button_icon", ""),
                            getattr(self, f"theme_{button}_button_class", ""),
                        )
                    else:
                        button = (button, button.capitalize(), None, None)
                    buttons_line[i] = button
                if len(button) != 4:
                    raise InvalidListingConfiguration(
                        _(
                            "In attached form, button tuple description must have 4 items : "
                            "(action, label, icon css class, button css class)."
                        )
                    )
        return

    def datetimepicker_init(self):
        if self.listing.use_datetimepicker:
            self.listing.need_media_for("datetimepicker")
            self.listing.add_footer_dict_list(
                "datetimepickers", dict(listing=self.listing, div_id=self.id)
            )

    def get_form_field_from_layout_field(self, field_name, **kwargs):
        field_name = field_name.strip()
        key = f"form_field_{field_name}"
        form_field = self.init_kwargs.get(key)
        if not form_field:
            attrname = f"attached_form_field_{field_name}"
            form_field = getattr(self.listing, attrname, None)
        if not form_field:
            col = self.listing.columns.get(field_name)
            if col:
                form_field = col.create_form_field(**kwargs)
        if not form_field:
            raise InvalidAttachedForm(
                _(
                    "In the {form_name} layout you specified the field "
                    '"{field_name}" but there is no existing listing '
                    'column with that name nor listing method "{attrname}"'
                    'nor attached_form param "{key}"'
                ).format(
                    form_name=self.name,
                    field_name=field_name,
                    attrname=attrname,
                    key=key,
                )
            )
        widget = form_field.widget
        patch_help_text_method = getattr(widget, "patch_help_text", None)
        if callable(patch_help_text_method):
            form_field.help_text = patch_help_text_method(form_field.help_text)

        return form_field

    def create_form_from_layout(self, **kwargs):
        fields = {}
        if not self.layout:
            raise InvalidAttachedForm(
                _("You must specify a list of columns names in the form layout")
            )
        for row in self.layout:
            for field_name in row:
                field = self.get_form_field_from_layout_field(field_name, **kwargs)
                fields[field_name] = field
        form_class = type(
            "{}{}".format(self.name, self.listing.suffix),
            (self.form_base_class,),
            {"base_fields": fields},
        )
        return form_class

    def get_form_initial(self):
        methods_names = [
            f"manage_attached_form_get_initial",
        ]
        action = getattr(self.listing, "action_button", None)
        if action:
            methods_names.insert(0, f"manage_attached_form_{action}_get_initial")
        for method_name in methods_names:
            # Look in listing then in view whether a specific method exists
            method = getattr(self.listing, method_name, None)
            if method:
                return method()
            else:
                view = self.listing.get_view()
                method = getattr(view, method_name, None)
                if method:
                    return method(self.listing)
        return None

    def get_form_hiddens(self):
        # Look in listing then in view whether a specific method exists
        method_name = f"manage_attached_form_get_hiddens"
        # Search method in view object first
        method = getattr(self.listing, method_name, None)
        if method:
            return method()
        else:
            view = self.listing.get_view()
            method = getattr(view, method_name, None)
            if method:
                return method(self.listing)
        return {}

    def customize_form(self, form):
        method_name = f"manage_attached_form_customize"
        method = getattr(self.listing, method_name, None)
        if not method:
            view = self.listing.get_view()
            method = getattr(view, method_name, None)
        if method:
            method(form)

    def get_form(self, do_not_clean=False, **kwargs):
        if not self._form:
            kwargs.setdefault("have_empty_choice", True)
            kwargs.setdefault("force_select", True)
            form_class = self.create_form_from_layout(**kwargs)
            data = None
            if self.listing.request.POST.get("attached_form_name") == self.name:
                data = self.listing.request.POST
            initial = self.get_form_initial()
            self._form = form_class(data, initial=initial)
            self._form.instance = None
            self._form.do_not_clean = do_not_clean
            self._form.listing = self.listing
            self._form.form_name = self.name
            self.customize_form(self._form)
        return self._form

    def render_init(self, context):
        if not self._render_initialized:
            self.listing.manage_page_context(context)
            self.datetimepicker_init()
            if not isinstance(self.attrs, HTMLAttributes):
                self.attrs = HTMLAttributes(self.attrs)
            form_css_class = "listing-" + self.name.replace("_", "-")
            self.attrs.add("class", form_css_class)
            self.attrs.add("class", f"attached-form")
            if self.listing.accept_ajax:
                self.attrs.add("class", f"django-listing-ajax")
            if "id" not in self.attrs:
                css_id = f"{form_css_class}{self.listing.suffix}".replace("_", "-")
                self.attrs.add("id", css_id)
            self.listing.attached_form_css_id = self.id = css_id
            self.attrs.add("related-listing", self.listing.css_id)
            self._render_initialized = True

    def render(self, request_context):
        self.render_init(request_context)
        ctx = self.get_context(request_context)
        template = loader.get_template(self.template_name)
        out = template.render(ctx)
        return out

    def get_context(self, request_context):
        ctx = RenderContext(
            self.listing.global_context,
            self.listing.page_context.flatten(),
            listing=self.listing,
            attached_form=self,
            get=self.listing.request.GET,
        )
        # needed when using ajax :
        csrf_token = request_context.request.POST.get("csrfmiddlewaretoken")
        if csrf_token:
            ctx["csrf_token"] = csrf_token
        object_pk = request_context.request.POST.get("object_pk", "")
        self.listing.add_form_input_hiddens(object_pk=object_pk)
        return ctx
