'''
Création : 12 janv. 2010

@author: Eric Lapouyade
'''
from django import template
from django.utils.safestring import mark_safe
from ..listing import Listing, ListingVariations
from ..listing_form import ListingForm
from itertools import count

register = template.Library()
_uniq_counter = count(0)


def initialize_listing(context, listing, data=None, *args, **kwargs):
    if isinstance(listing,str) or listing is None:
        return None
    if not isinstance(listing,(Listing,ListingVariations)):
        data = listing
        listing = Listing()
    # if there is data or a model is specified in columns (if exsiting)
    if (data or listing.get_model()) and not listing.is_initialized():
        listing.init(data, context=context, **kwargs)
    else:
        listing.set_kwargs(**kwargs)
    return listing


@register.simple_tag(takes_context=True)
def create_listing_begin(context, listing=None, *args, **kwargs):
    # developper will specify a Listing class,
    # but Django will automatically instanciate it with no argument
    if not isinstance(listing,(Listing,ListingVariations)):
        listing = Listing()
    listing.store_kwargs(**kwargs)
    return listing


@register.simple_tag(takes_context=True)
def create_listing_end(context, listing, data=None, *args, **kwargs):
    initialize_listing(context, listing, data, *args, **kwargs)
    return ''


@register.simple_tag(takes_context=True)
def create_listing(context, listing, data=None, *args, **kwargs):
    return initialize_listing(context, listing, data, *args, **kwargs)


@register.simple_tag()
def setopt_listing(listing, **kwargs):
    if isinstance(listing,(Listing,ListingVariations)):
        listing.store_kwargs(**kwargs)
    return ''


@register.simple_tag()
def setopt_listing_html_attr(listing, listing_attr, html_attr, value):
    if isinstance(listing,(Listing,ListingVariations)):
        listing.store_html_attr(listing_attr, html_attr, value)
    return ''


@register.simple_tag()
def setopt_column(listing, name, **kwargs):
    if isinstance(listing,(Listing,ListingVariations)):
        listing.store_column_kwargs(name, **kwargs)
    return ''


@register.simple_tag()
def setopt_column_html_attr(listing, name, col_attr, html_attr, value):
    if isinstance(listing,(Listing,ListingVariations)):
        listing.store_column_html_attr(name, col_attr, html_attr, value)
    return ''


@register.simple_tag()
def setopt_toolbar_item(listing, name, **kwargs):
    if isinstance(listing,(Listing,ListingVariations)):
        listing.store_toolbar_item_kwargs(name, **kwargs)
    return ''


@register.simple_tag()
def setopt_toolbar_item_html_attr(listing, name, col_attr, html_attr, value):
    if isinstance(listing,(Listing,ListingVariations)):
        listing.store_toolbar_item_html_attr(name, col_attr, html_attr, value)
    return ''


@register.simple_tag(takes_context=True)
def render_listing(context, listing=None, data=None, *args, **kwargs):
    if listing is None:
        listing = context.get('listing')
    listing = initialize_listing(context, listing, data, *args, **kwargs)
    if listing is None:
        return mark_safe(
                '<b>ERROR :</b> The listing/class/data you specified is '
                'empty : do you have set the corresponding variable '
                'in view context ?')
    if isinstance(listing.data,str) or listing.data is None:
        return mark_safe(
                '<b>ERROR :</b> The listing has no data or model specified : '
                'May be you passed a listing class and forgot to specify data '
                'or model or you passed only a listing instance but without any'
                ' bound data. Please check you have '
                '<tt>{% render_listing your_listing_class_or_instance your_data'
                ' %}</tt> or specify data or a django model when creating '
                'the listing class or instance in your python code.')
    return mark_safe(listing.render(context))


@register.simple_tag(takes_context=True)
def geturl_listing(context, listing, **kwargs):
    return mark_safe(listing.get_url(context, **kwargs))


@register.simple_tag(takes_context=True)
def geturl_listing_key(context, listing, key, value, **kwargs):
    return mark_safe(listing.get_url(context, **{key:value}, **kwargs))


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
        listing = context.get('listing')
    listing = initialize_listing(context, listing)
    if not listing or not listing.is_initialized():
        return mark_safe(
            '<b>ERROR :</b> The listing must be initialized before rendering the'
            ' filter form. You should use <tt>{% create_listing a_listing_class '
            'your_data as listing %}</tt> tag before in '
            'the template or provide in the context a listing instance bound '
            'to some data.<br><br>')
    if not isinstance(listing,(Listing,ListingVariations)):
        return mark_safe(
            '<b>ERROR :</b> You specified an invalid listing instance. '
            'Do you have set the corresponding variable in view context ?')
    if not listing.filters:
        return mark_safe(
            '<b>ERROR :</b> The listing has no filters defined. '
            'Please define the ".filters" attribute to your listing'
            )
    return mark_safe(listing.filters.render_form(context))


@register.simple_tag()
def setopt_filter(listing, name, **kwargs):
    if isinstance(listing,(Listing,ListingVariations)):
        listing.store_filter_kwargs(name, **kwargs)
    return ''


@register.simple_tag()
def setopt_filter_html_attr(listing, name, col_attr, html_attr, value):
    if isinstance(listing,(Listing,ListingVariations)):
        listing.store_filter_html_attr(name, col_attr, html_attr, value)
    return ''


@register.simple_tag()
def filters_form_field(listing, name):
    return listing.filters.get_form_field(name)


@register.simple_tag()
def filters_add_row(listing, row):
    if listing.filters is None:
        listing.filters = row
    elif isinstance(listing.filters,str):
        if listing.filters:
            listing.filters += ';'
        listing.filters += row
    return ''


@register.simple_tag()
def get_form_field(form, name):
    return form[name]


@register.simple_tag(takes_context=True)
def render_listing_form(context, listing, *args,
                        action=None, layout=None, name=None, **kwargs):
    if not listing:
        listing = context.get('listing')
    if not isinstance(listing,(Listing,ListingVariations)):
        return mark_safe(
            '<b>ERROR :</b> You specified an invalid listing instance. '
            'Do you have set the corresponding variable in view context ?')
    if listing.form:
        if not isinstance(listing.form, ListingForm):
            return mark_safe(
                '<b>ERROR :</b> when using {% render_listing_form listing %}'
                'listing.form must be an instance of ListingForm')
        if layout:
            if listing.form.layout:
                return mark_safe(
                    '<b>ERROR :</b> Do not specify a layout in '
                    '{% render_listing_form %} when a layout has already been  '
                    'defined at python side.<br><br>')
            else:
                listing.form.layout = layout
        if action:
            if listing.form.action:
                return mark_safe(
                    '<b>ERROR :</b> Do not specify an action in '
                    '{% render_listing_form %} when an action has already been  '
                    'defined at python side.<br><br>')
            else:
                listing.form.action = action
    if not listing.form:
        listing.form = ListingForm(action, name=name,
                                   layout=layout, *args, **kwargs)
    listing.form.bind_to_listing(listing)
    return mark_safe(listing.form.render(context))
