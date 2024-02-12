"""
Création : 12 janv. 2010

@author: Eric Lapouyade
"""
import json
from itertools import count

from django import template
from django.conf import settings
from django.utils.safestring import SafeString, mark_safe

from ..listing import Listing, ListingVariations
from ..attached_form import AttachedForm
from ..theme_config import ThemeTemplate

register = template.Library()
_uniq_counter = count(0)


@register.filter(name="json_options")
def json_options(dct):
    out = "{\n"
    options = []
    for k, v in sorted(dct.items()):
        if isinstance(v, SafeString):
            options.append(f"{k}:{v}")
        else:
            options.append(f"{k}:{json.dumps(v, indent=4)}")
    out += ",\n".join(options)
    out += "\n}"
    return mark_safe(out)


@register.filter()
def underscore_to_dash(s):
    return s.replace("_", "-")


@register.filter()
def theme_template(s):
    return ThemeTemplate.get(s)


class ListingHeaderNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        remaining_output = self.nodelist.render(context)
        template_name = ThemeTemplate.get("header.html")
        tpl = template.loader.get_template(template_name)
        request = context.request
        context = context.flatten()
        context.update(
            settings.django_listing_settings.context,
            need_media_for=getattr(context["request"], "need_media_for", {}),
        )
        tpl_output = tpl.render(context, request)
        return f"{tpl_output}\n{remaining_output}"


@register.tag(name="render_listing_header")
def do_listing_header(parser, token):
    nodelist = parser.parse()
    return ListingHeaderNode(nodelist)


@register.simple_tag(takes_context=True)
def render_listing_footer(context):
    template_name = ThemeTemplate.get("footer.html")
    tpl = template.loader.get_template(template_name)
    request = context.request
    context = context.flatten()
    context.update(
        settings.django_listing_settings.context,
        need_media_for=getattr(context["request"], "need_media_for", {}),
    )
    tpl_output = tpl.render(context, request)
    return tpl_output


def initialize_listing(context, listing, data=None, *args, **kwargs):
    if isinstance(listing, str) or listing is None:
        return None
    if not isinstance(listing, (Listing, ListingVariations)):
        data = listing
        listing = Listing()
    # if there is data or a model is specified in columns (if exsiting)
    if (data is not None or listing.get_model()) and not listing.is_initialized():
        listing.init(data, context=context, **kwargs)
    else:
        listing.set_kwargs(**kwargs)
    view = context.get("view")
    if view:
        listing.set_view(view)
    return listing


@register.simple_tag(takes_context=True)
def create_listing_begin(context, listing=None, *args, **kwargs):
    # developper will specify a Listing class,
    # but Django will automatically instanciate it with no argument
    if not isinstance(listing, (Listing, ListingVariations)):
        listing = Listing()
    listing.store_kwargs(**kwargs)
    return listing


@register.simple_tag(takes_context=True)
def create_listing_end(context, listing, data=None, *args, **kwargs):
    initialize_listing(context, listing, data, *args, **kwargs)
    return ""


@register.simple_tag(takes_context=True)
def create_listing(context, listing, data=None, *args, **kwargs):
    return initialize_listing(context, listing, data, *args, **kwargs)


@register.simple_tag()
def setopt_listing(listing, **kwargs):
    if isinstance(listing, (Listing, ListingVariations)):
        listing.store_kwargs(**kwargs)
    return ""


@register.simple_tag()
def setopt_listing_html_attr(listing, listing_attr, html_attr, value):
    if isinstance(listing, (Listing, ListingVariations)):
        listing.store_html_attr(listing_attr, html_attr, value)
    return ""


@register.simple_tag()
def setopt_column(listing, name, **kwargs):
    if isinstance(listing, (Listing, ListingVariations)):
        listing.store_column_kwargs(name, **kwargs)
    return ""


@register.simple_tag()
def setopt_column_html_attr(listing, name, col_attr, html_attr, value):
    if isinstance(listing, (Listing, ListingVariations)):
        listing.store_column_html_attr(name, col_attr, html_attr, value)
    return ""


@register.simple_tag()
def setopt_toolbar_item(listing, name, **kwargs):
    if isinstance(listing, (Listing, ListingVariations)):
        listing.store_toolbar_item_kwargs(name, **kwargs)
    return ""


@register.simple_tag()
def setopt_toolbar_item_html_attr(listing, name, col_attr, html_attr, value):
    if isinstance(listing, (Listing, ListingVariations)):
        listing.store_toolbar_item_html_attr(name, col_attr, html_attr, value)
    return ""


@register.simple_tag(takes_context=True)
def render_listing(context, listing=None, data=None, *args, **kwargs):
    if listing is None:
        listing = context.get("listing")
    listing = initialize_listing(context, listing, data, *args, **kwargs)
    if listing is None:
        return mark_safe(
            "<b>ERROR :</b> The listing/class/data you specified is "
            "empty : do you have set the corresponding variable "
            "in view context ?"
        )
    if isinstance(listing.data, str) or listing.data is None:
        return mark_safe(
            "<b>ERROR :</b> The listing has no data or model specified : "
            "May be you passed a listing class and forgot to specify data "
            "or model or you passed only a listing instance but without any"
            " bound data. Please check you have "
            "<tt>{% render_listing your_listing_class_or_instance your_data"
            " %}</tt> or specify data or a django model when creating "
            "the listing class or instance in your python code."
        )
    return mark_safe(listing.render(context))


@register.simple_tag(takes_context=True)
def geturl_listing(context, listing, **kwargs):
    return mark_safe(listing.get_url(context, **kwargs))


@register.simple_tag(takes_context=True)
def geturl_listing_key(context, listing, key, value, **kwargs):
    return mark_safe(listing.get_url(context, **{key: value}, **kwargs))


@register.simple_tag()
def gethiddens_listing(listing, without=None):
    return mark_safe(listing.get_hiddens_html(without))


@register.simple_tag()
def gethiddens_filters_form(listing):
    return mark_safe(listing.filters.get_hiddens_html())


@register.simple_tag()
def get_uniq_id():
    return next(_uniq_counter)


@register.simple_tag(takes_context=True)
def render_filters_form(context, listing):
    if not listing:
        listing = context.get("listing")
    listing = initialize_listing(context, listing)
    if not listing or not listing.is_initialized():
        return mark_safe(
            "<b>ERROR :</b> The listing must be initialized before rendering the"
            " filter form. You should use <tt>{% create_listing a_listing_class "
            "your_data as listing %}</tt> tag before in "
            "the template or provide in the context a listing instance bound "
            "to some data.<br><br>"
        )
    if not isinstance(listing, (Listing, ListingVariations)):
        return mark_safe(
            "<b>ERROR :</b> You specified an invalid listing instance. "
            "Do you have set the corresponding variable in view context ?"
        )
    if not listing.filters:
        return mark_safe(
            "<b>ERROR :</b> The listing has no filters defined. "
            'Please define the ".filters" attribute to your listing'
        )
    return mark_safe(listing.filters.render_form(context))


@register.simple_tag()
def setopt_filter(listing, name, **kwargs):
    if isinstance(listing, (Listing, ListingVariations)):
        listing.store_filter_kwargs(name, **kwargs)
    return ""


@register.simple_tag()
def setopt_filter_html_attr(listing, name, col_attr, html_attr, value):
    if isinstance(listing, (Listing, ListingVariations)):
        listing.store_filter_html_attr(name, col_attr, html_attr, value)
    return ""


@register.simple_tag()
def filters_form_field(listing, name):
    return listing.filters.get_form_field(name)


@register.simple_tag()
def filters_form_field_container_attrs(listing, name):
    return mark_safe(listing.filters.get_form_field_container_attrs(name))


@register.simple_tag()
def filters_add_row(listing, row):
    if listing.filters is None:
        listing.filters = row
    elif isinstance(listing.filters, str):
        if listing.filters:
            listing.filters += ";"
        listing.filters += row
    return ""


@register.simple_tag()
def get_form_field(form, name):
    return form[name]


@register.simple_tag(takes_context=True)
def render_attached_form(context, listing, *args, name=None, layout=None, **kwargs):
    if not listing:
        listing = context.get("listing")
    if not isinstance(listing, (Listing, ListingVariations)):
        return mark_safe(
            "<b>ERROR :</b> You specified an invalid listing instance. "
            "Do you have set the corresponding variable in view context ?"
        )
    if listing.attached_form:
        if not isinstance(listing.attached_form, AttachedForm):
            return mark_safe(
                "<b>ERROR :</b> when using {% render_attached_form listing %}"
                "listing.attached_form must be an instance of AttachedForm"
            )
        if layout:
            if listing.attached_form.layout:
                return mark_safe(
                    "<b>ERROR :</b> Do not specify a layout in "
                    "{% render_attached_form %} when a layout has already been  "
                    "defined at python side.<br><br>"
                )
            else:
                listing.attached_form.layout = layout
    if not listing.attached_form:
        form = AttachedForm(name=name, layout=layout, *args, **kwargs)
        listing.attached_form = form.bind_to_listing(listing)
    return mark_safe(listing.attached_form.render(context))


@register.simple_tag(takes_context=True)
def get_dict_list(context, key):
    request = context.request
    if hasattr(request, "django_listing_footer_dict_list"):
        return request.django_listing_footer_dict_list.get(key, [])
    return []


@register.simple_tag(takes_context=True)
def header_snippets(context):
    request = context.request
    snippets = getattr(request, "django_listing_header_snippets", None)
    if snippets:
        return mark_safe("\n".join(snippets))
    return ""


@register.simple_tag(takes_context=True)
def footer_snippets(context):
    request = context.request
    snippets = getattr(request, "django_listing_footer_snippets", None)
    if snippets:
        return mark_safe("\n".join(snippets))
    return ""


@register.simple_tag(takes_context=True)
def onready_snippets(context):
    request = context.request
    snippets = getattr(request, "django_listing_onready_snippets", None)
    if snippets:
        return mark_safe("\n".join(snippets))
    return ""


@register.simple_tag()
def listing_has_permission_for_action(listing, action):
    return listing.has_permission_for_action(action)


@register.simple_tag()
def listing_confirm_msg_for_action(listing, action):
    return listing.get_confirm_msg_for_action(action)


@register.simple_tag()
def listing_confirm_msg_nb_items_for_action(listing, action):
    return listing.get_confirm_msg_nb_items_for_action(action)


@register.simple_tag()
def listing_responsive_columns_css(listing, format_str=None):
    if not isinstance(listing, (Listing, ListingVariations)):
        return mark_safe(
            "<!-- ERROR : you must provide a valid listing to {% listing_responsive_css %} -->"
        )
    css = []
    if format_str is None:
        format_str = "{} : "
    for i, col in enumerate(listing.selected_columns, start=1):
        title = col.get_header_value()
        content = format_str.format(title, col=col)
        css_class = listing.theme_listing_class.replace(" ", ".")
        css.append(
            f"table.{css_class} td:nth-of-type({i}):before {{content: '{content}';}}"
        )
    return mark_safe("\n".join(css))


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
