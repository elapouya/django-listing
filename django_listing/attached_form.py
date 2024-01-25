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
from .exceptions import InvalidAttachedForm
from .html_attributes import HTMLAttributes
from .theme_config import ThemeTemplate
from .utils import init_dicts_from_class

__all__ = ["ATTACHED_FORM_PARAMS_KEYS", "AttachedForm"]

# Declare keys only for "Filters" object
ATTACHED_FORM_PARAMS_KEYS = {
    "action",
    "attached_form_name",
    "reset_label",
    "reset_icon",
    "submit_label",
    "submit_icon",
    "submit_action",
    "template_name",
    "django_form_class",
    "layout",
    "attrs",
    "buttons",
    "ListingBaseForm",
}


class ListingBaseForm(forms.BaseForm):
    def _clean_fields(self):
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
                    method_name = f"{self.form_name}_clean_{name}"
                    method = getattr(self.listing, method_name, None)
                if method:
                    value = method(self)
                    self.cleaned_data[name] = value
            except ValidationError as e:
                self.add_error(name, e)

    def _clean_form(self):
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
                method_name = f"{self.form_name}_clean"
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
    form_base_class = ListingBaseForm
    django_form_class = None
    reset_label = pgettext_lazy("Attached form", "Reset")
    reset_icon = None
    submit_label = pgettext_lazy("Attached form", "Add")
    submit_icon = None
    submit_action = "insert"
    template_name = ThemeTemplate("attached_form.html")
    layout = None
    listing = None
    buttons = "reset,submit"
    name = "attached_form"
    attrs = {"class": "listing-form"}

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
            self.listing.form_serialize_labels = []
            for row in self.layout:
                for field_name in row:
                    field_name = field_name.strip()
                    col = self.listing.columns.get(field_name)
                    if not col:
                        raise InvalidAttachedForm(
                            _(
                                "In the {form_name} layout you specified the field "
                                '"{field_name}" but there is no existing listing '
                                "column with that name"
                            ).format(form_name=self.name, field_name=field_name)
                        )
                    self.listing.form_model_fields.append(col.model_field.name)
                    if col.form_field_serialize_label:
                        self.listing.form_serialize_labels.append(col.model_field.name)
            layout_str = ";".join(map(lambda l: ",".join(l), self.layout))
            self.listing.add_form_input_hiddens(
                attached_form_layout=layout_str,
                attached_form_name=self.name,
                action=self.action,
            )
        buttons = self.buttons
        if isinstance(buttons, str):
            buttons = list(map(str.strip, buttons.split(",")))
        self.buttons = []
        for button in buttons:
            if isinstance(button, str):
                # must be defined has (action, label, icon css class)
                if button == "reset":
                    button = ("reset", self.reset_label, self.reset_icon)
                elif button == "submit":
                    button = (self.submit_action, self.submit_label, self.submit_icon)
                else:
                    button = (button, button.capitalize(), None)
            self.buttons.append(button)

    def datetimepicker_init(self):
        if self.listing.use_datetimepicker:
            self.listing.need_media_for("datetimepicker")
            self.listing.add_footer_dict_list(
                "datetimepickers", dict(listing=self.listing, div_id=self.id)
            )

    def create_form_from_layout(self):
        fields = {}
        if not self.layout:
            raise InvalidAttachedForm(
                _("You must specify a list of columns names in the form layout")
            )
        for row in self.layout:
            for field_name in row:
                field_name = field_name.strip()
                col = self.listing.columns.get(field_name)
                fields[field_name] = col.create_form_field(have_empty_choice=True)
        form_class = type(
            "{}{}".format(self.name, self.listing.suffix),
            (self.form_base_class,),
            {"base_fields": fields},
        )
        return form_class

    def get_form(self):
        if not self._form:
            form_class = self.create_form_from_layout()
            data = None
            if self.listing.request.POST.get("attached_form_name") == self.name:
                data = self.listing.request.POST
            self._form = form_class(data)
            self._form.listing = self.listing
            self._form.form_name = self.name
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
        return ctx
