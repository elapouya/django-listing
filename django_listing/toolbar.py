#
# Created : 2018-02-09
#
# @author: Eric Lapouyade
#
import copy
import re
from itertools import count
from types import GeneratorType

from django.utils.translation import gettext_lazy as _

from django_listing import EXPORT_FORMATS

from .context import RenderContext
from .exceptions import *
from .html_attributes import HTMLAttributes
from .theme_config import ThemeAttribute, ThemeTemplate
from .utils import normalize_choices, normalize_list

__all__ = [
    "ExportDropdownToolbarItem",
    "ExportSelectToolbarItem",
    "PerPageDropdownToolbarItem",
    "PerPageSelectToolbarItem",
    "SortDropdownToolbarItem",
    "SortSelectToolbarItem",
    "TOOLBAR_PARAMS_KEYS",
    "Toolbar",
    "ToolbarItem",
    "UpdateToolbarItem",
    "VariationsToolbarItem",
    "GroupByToolbarItem",
]

TOOLBAR_PARAMS_KEYS = {
    "attrs",
    "button_label",
    "choices",
    "icon",
    "label",
    "name",
    "template_name",
    "theme_button_class",
}


class Toolbar(list):
    template_name = ThemeTemplate("toolbar.html")

    def __init__(self, *items, params=None, listing=None):
        if params is None:
            params = {}
        self._params = params
        self.name2item = {}
        if items:
            if isinstance(items[0], str):
                items_name = map(str.strip, items[0].split(","))
                items = []
                for name in items_name:
                    slug = re.sub(r"[_\d]+$", "", name)
                    cls = ToolbarItemMeta.get_class(slug)
                    item = cls(name)
                    item.set_listing(listing)
                    items.append(cls(name))
            elif isinstance(items[0], (list, tuple)):
                items = items[0]
            elif isinstance(items[0], GeneratorType):
                items = list(items[0])
        super().__init__(items)

    def get(self, name, default=None):
        return self.name2item.get(name, default)

    def names(self):
        return self.name2item.keys()

    def get_params(self):
        return self._params

    def bind_to_listing(self, listing):
        items = Toolbar(params=self._params)
        for item in self:
            # ensure there is one toolbarItem instance per listing
            if not item.listing:
                item = copy.copy(item)
            item.bind_to_listing(listing)
            items.append(item)
        items.name2item = {i.name: i for i in items if isinstance(i, ToolbarItem)}
        items.listing = listing
        return items

    def get_context(self):
        # aggregate all items context
        return RenderContext(*[i.get_context() for i in self])


class ToolbarItemMeta(type):
    slug2class = {}

    def __new__(mcs, name, bases, attrs):
        cls = super(ToolbarItemMeta, mcs).__new__(mcs, name, bases, attrs)
        ToolbarItemMeta.slug2class[ToolbarItemMeta.get_slug(cls)] = cls
        params_keys = cls.params_keys
        if isinstance(params_keys, str):
            params_keys = set(map(str.strip, params_keys.split(",")))
        TOOLBAR_PARAMS_KEYS.update(params_keys)
        TOOLBAR_PARAMS_KEYS.discard("")
        return cls

    @classmethod
    def get_slug(cls, mcs):
        return mcs.__name__.replace("ToolbarItem", "").lower()

    @classmethod
    def get_class(cls, slug):
        return cls.slug2class.get(slug)


class ToolbarItem(metaclass=ToolbarItemMeta):
    name = None
    params_keys = ""
    attrs = {}
    listing = None
    label = None
    icon = None
    theme_button_class = ThemeAttribute("toolbar_theme_button_class")

    _ids = count(0)

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.id = next(self._ids)

    def bind_to_listing(self, listing):
        self.init(listing, *self.init_args, **self.init_kwargs)

    def set_listing(self, listing):
        self.listing = listing

    def init(self, listing, name=None, **kwargs):
        self.set_listing(listing)
        if name:
            self.name = re.sub(r"\W", "", name)
        if not self.name:
            self.name = ToolbarItemMeta.get_slug(self.__class__)
        self.set_kwargs(**kwargs)
        self.apply_template_kwargs()
        if not isinstance(self.attrs, HTMLAttributes):
            self.attrs = HTMLAttributes(self.attrs)
        self.css_class = self.__class__.__name__.lower()

    def set_kwargs(self, **kwargs):
        # If toolbar_<toolbarItemclass>_<params> exists in listing attributes :
        # take is as a default value
        for k in TOOLBAR_PARAMS_KEYS:
            listing_key = "toolbar_{}".format(k)
            if hasattr(self.listing, listing_key):
                setattr(self, k, getattr(self.listing, listing_key))
        for k, v in kwargs.items():
            if k in TOOLBAR_PARAMS_KEYS:
                setattr(self, k, v)
        # if parameters given in toolbar : apply them
        for k, v in self.listing.toolbar.get_params().get(self.name, {}).items():
            if k in TOOLBAR_PARAMS_KEYS:
                setattr(self, k, v)
        # if parameters given in listing apply them to specified toolbarItem
        for k in TOOLBAR_PARAMS_KEYS:
            key = "toolbar_{}__{}".format(self.name, k)
            v = getattr(self.listing, key, None)
            if v is not None:
                setattr(self, k, v)

    def apply_template_kwargs(self):
        kwargs = self.listing.get_toolbar_item_kwargs(self.name)
        if kwargs:
            for k, v in kwargs.items():
                if k in TOOLBAR_PARAMS_KEYS:
                    if isinstance(v, dict):
                        prev_value = getattr(self, k, None)
                        if isinstance(prev_value, dict):
                            prev_value.update(v)
                            continue
                    setattr(self, k, v)

    def get_context(self):
        return {}


class SortSelectToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_select.html")
    params_keys = "up_arrow,down_arrow,has_submit_button"
    choices = None
    up_arrow = " &#xF106;"
    down_arrow = " &#xF107;"
    has_submit_button = False
    label = _("Sort by")
    button_label = _("OK")
    select_name = "sort"

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        self.choices = normalize_choices(self.choices)
        if not self.choices:
            self.choices = []
            for c in self.listing.columns:
                self.choices.append((c.name, c.get_header_value() + self.up_arrow))
                self.choices.append(
                    ("-" + c.name, c.get_header_value() + self.down_arrow)
                )

    def get_context(self):
        # get_context is called at rendering time :
        # this is the way to get the asked value for self.listing.sort
        sorting = self.listing.sort
        self.selected_choices = [
            (sort_key, label, sort_key == sorting) for sort_key, label in self.choices
        ]
        # do not need to return a context


class SortDropdownToolbarItem(SortSelectToolbarItem):
    template_name = ThemeTemplate("tbi_dropdown.html")
    label = _("Sort by...")


class VariationsToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_variations.html")
    params_keys = ["show_labels", "show_icons", "labels", "icons"]
    labels = ""
    icons = ""
    show_labels = False
    show_icons = True
    buttons = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        if not hasattr(self.listing, "variations_classes"):
            raise InvalidToolbarItem(
                "Variation toolbar item is only for variations listings "
                "(subclass of ListingVariations)"
            )
        nb_variations = len(self.listing.variations_classes)
        labels = normalize_list(self.labels, force_length=nb_variations)
        icons = normalize_list(self.icons, force_length=nb_variations)
        urls = [
            self.listing.get_url(variation=i, without="gb_cols,gb_annotate_cols")
            for i in range(nb_variations)
        ]
        self.buttons = list(
            zip(
                urls,
                labels,
                icons,
            )
        )


class PerPageSelectToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_select.html")
    params_keys = "choices"
    choices = "10,25,50,100,-1:All"
    has_submit_button = False
    label = _("Per page")
    button_label = _("OK")
    select_name = "per_page"

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        self.choices = normalize_choices(self.choices, int_keys=True)

    def get_context(self):
        # get_context is called at rendering time :
        # this is the way to get the asked value for self.listing.per_page
        # if per_pages is not in choices : add that choice dynamically
        per_pages = [c[0] for c in self.choices]
        per_page = self.listing.per_page
        if per_pages and per_page not in per_pages:
            for i, p in enumerate(per_pages):
                if per_page < p or p == -1:
                    self.choices.insert(i, [per_page, per_page])
                    break
            else:
                self.choices.append([per_page, per_page])

        self.selected_choices = [
            (pp, label, per_page == pp) for pp, label in self.choices
        ]
        # do not need to return a context


class PerPageDropdownToolbarItem(PerPageSelectToolbarItem):
    template_name = ThemeTemplate("tbi_dropdown.html")
    label = _("Per page...")


class ExportSelectToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_export.html")
    choices = [("", _("Choose..."))] + EXPORT_FORMATS
    has_submit_button = True
    label = _("Export to...")
    button_label = _("OK")
    select_name = "export"

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        self.choices = normalize_choices(self.choices)
        self.selected_choices = [(key, label, False) for key, label in self.choices]


class ExportDropdownToolbarItem(ExportSelectToolbarItem):
    template_name = ThemeTemplate("tbi_export_dropdown.html")
    label = _("Export to...")
    choices = EXPORT_FORMATS


class UpdateToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_update.html")
    label = _("Update")


class SelectAllToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_select_all.html")
    label = _("Select all")


class UnselectAllToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_unselect_all.html")
    label = _("Unselect all")


class InvertSelectionToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_invert_selection.html")
    label = _("Invert selection")


class GroupByToolbarItem(ToolbarItem):
    template_name = ThemeTemplate("tbi_group_by.html")
    label = _("Group by...")

    def init(self, listing, name=None, **kwargs):
        super().init(listing, name, **kwargs)
        self.listing.need_media_for("dual_listbox")
