#
# Created : 2018-04-04
#
# @author: Eric Lapouyade
#

from django import forms
from django.core.exceptions import ValidationError
from django.forms.fields import FileField
from django.template import loader
from django.utils.translation import gettext as _
from django.utils.translation import pgettext_lazy

from .context import RenderContext
from .exceptions import InvalidListingForm
from .html_attributes import HTMLAttributes
from .theme_config import ThemeTemplate
from .utils import init_dicts_from_class

__all__ = ["LISTING_FORM_PARAMS_KEYS", "ListingForm"]

# Declare keys only for "Filters" object
LISTING_FORM_PARAMS_KEYS = {
    "action",
    "reset_label",
    "submit_label",
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


class ListingForm:
    id = None
    action = None
    form_base_class = ListingBaseForm
    django_form_class = None
    reset_label = pgettext_lazy("Listing form", "Reset")
    submit_label = pgettext_lazy("Listing form", "Add")
    template_name = ThemeTemplate("listing_form.html")
    layout = None
    buttons = "reset,submit"
    name = "listing_form"
    attrs = {"class": "listing-form"}

    def __init__(self, action, name=None, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.name = name or f"{action}_form"
        self.action = action
        self._form = None
        init_dicts_from_class(
            self,
            [
                "attrs",
            ],
        )

    def bind_to_listing(self, listing):
        self.init(listing, *self.init_args, **self.init_kwargs)

    def set_listing(self, listing):
        self.listing = listing

    def set_kwargs(self, **kwargs):
        for k in LISTING_FORM_PARAMS_KEYS:
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
            layout_str = ";".join(map(lambda l: ",".join(l), self.layout))
            self.listing.add_form_input_hiddens(
                listing_form_layout=layout_str, listing_form_name=self.name
            )
        self.listing.add_form_input_hiddens(listing_id=self.listing.id)
        if not isinstance(self.attrs, HTMLAttributes):
            self.attrs = HTMLAttributes(self.attrs)
        form_css_class = "listing-" + self.name.replace("_", "-")
        self.attrs.add("class", form_css_class)
        if self.listing.accept_ajax:
            self.attrs.add("class", f"django-{self.name}-ajax")
        if "id" not in self.attrs:
            self.attrs.add("id", f"{form_css_class}{self.listing.suffix}")
        self.id = self.attrs["id"]
        buttons = self.buttons
        if isinstance(buttons, str):
            self.buttons = list(map(str.strip, buttons.split(",")))

    def datetimepicker_init(self):
        if self.listing.use_datetimepicker:
            self.listing.need_media_for("datetimepicker")
            self.listing.add_footer_dict_list(
                "datetimepickers", dict(listing=self.listing, div_id=self.id)
            )

    def create_form_from_layout(self):
        fields = {}
        if not self.layout:
            raise InvalidListingForm(
                _("You must specify a list of columns " "names in the form layout")
            )
        for row in self.layout:
            for field_name in row:
                col = self.listing.columns.get(field_name)
                if not col:
                    raise InvalidListingForm(
                        _(
                            "In the {form_name} layout you specified the field "
                            '"{field_name}" but there is no existing listing '
                            "column with that name"
                        ).format(form_name=self.name, field_name=field_name)
                    )
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
            self._form = form_class(self.listing.request.POST or None)
            self._form.listing = self.listing
            self._form.form_name = self.name
        return self._form

    def render_init(self, context):
        self.listing.manage_page_context(context)
        self.datetimepicker_init()

    def render(self, context):
        self.render_init(context)
        ctx = self.get_context()
        template = loader.get_template(self.template_name)
        out = template.render(ctx)
        return out

    def get_context(self):
        ctx = RenderContext(
            self.listing.global_context,
            self.listing.page_context.flatten(),
            listing=self.listing,
            listing_form=self,
            get=self.listing.request.GET,
        )
        return ctx
