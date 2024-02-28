#
# Created : 2020-05-04
#
# @author: Eric Lapouyade
#
import re

from django.db import models
from django.http import HttpResponse
from django.middleware.csrf import get_token as get_csrf_token
from django.template import loader
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from django_listing import Column, ListingException, ModelColumns, InvalidColumn

from .theme_config import ThemeTemplate

__all__ = [
    "ActionsButtonsColumn",
]


class ActionsButtonsColumn(Column):
    params_keys = (
        "buttons",
        "buttons_has_icon",
        "buttons_has_text",
        "buttons_icon",
        "buttons_template",
        "buttons_text",
        "buttons_theme_button_class",
        "buttons_theme_li_class",
        "buttons_method",
        "buttons_url_func",
    )
    params_keys_suffixes = (
        "has_icon",
        "has_text",
        "icon",
        "text",
        "theme_button_class",
        "theme_li_class",
        "title",
        "method",
        "url_func",
    )
    buttons = "move_up,move_down,view_object,edit_object,delete_object"
    buttons_template = ThemeTemplate("actions_buttons.html")
    buttons_text = ""
    buttons_icon = ""
    buttons_title = ""
    buttons_has_icon = True
    buttons_has_text = True
    buttons_theme_li_class = "action-item"
    buttons_theme_button_class = "btn btn-primary"
    buttons_method = None
    buttons_url_func = None
    actions_query_string_keys = {
        "action_col",
        "action_button",
        "action_pk",
    }
    action_col = None
    action_button = None
    action_pk = None
    actions_query_string_int_keys = {
        "action_pk",
    }
    sortable = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buttons_description = {}

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        # if not isinstance(self.listing.data, QuerySet):
        #     raise InvalidData('Actions buttons work only with QuerySet as listing data.')

    def render_init_context(self, context):
        self.extract_action_params()

    def set_kwargs(self, **kwargs):
        super().set_kwargs(**kwargs)
        buttons = self.buttons
        if isinstance(buttons, str):
            buttons = set(map(str.strip, buttons.split(",")))
        suffixes = self.params_keys_suffixes
        if isinstance(suffixes, str):
            suffixes = map(str.strip, suffixes.split(","))
        for k, v in kwargs.items():
            b, *_ = k.split("__")
            if b in buttons:
                setattr(self, k, v)
        for b in buttons:
            description = {}
            for s in suffixes:
                k = f"{b}__{s}"
                if hasattr(self, k):
                    description[s] = getattr(self, k)
                else:
                    description[s] = getattr(self, f"buttons_{s}")
            description["name"] = b
            self.buttons_description[b] = description

    def extract_action_params(self):
        if not self.listing.request:
            return
        get_dict = self.listing.request.GET
        post_dict = self.listing.request.POST
        for qs_key in self.actions_query_string_keys:
            v = None
            if qs_key in post_dict:
                v = post_dict.get(qs_key)
            elif qs_key in get_dict:
                v = get_dict.get(qs_key)
            if v is not None and qs_key in self.actions_query_string_int_keys:
                try:
                    v = int(v)
                except ValueError:
                    pass
            setattr(self, qs_key, v)

    def get_buttons_template(self, rec):
        if not hasattr(self, "_value_template"):
            self._value_template = loader.get_template(self.buttons_template)
        return self._value_template

    def get_buttons_context(self, rec):
        buttons = self.buttons
        if isinstance(buttons, str):
            buttons = map(str.strip, buttons.split(","))
        buttons_context = []
        for b in buttons:
            meth_name = f"get_button_{b}_context"
            context = {}
            context_method = getattr(self.listing, meth_name, None)
            if context_method is not None:
                context = context_method(
                    self, b, rec
                )  # give col objet to listing method
            else:
                context_method = getattr(self, meth_name, None)
                if context_method is not None:
                    context = context_method(b, rec)
            context.update(
                self.buttons_description[b],
                name=b,
                name_css_class=b.replace("_", "-"),
            )
            buttons_context.append(context)
        return dict(
            listing=self.listing,
            buttons=buttons_context,
            rec=rec,
            action_col=self.name,
            csrf_token=get_csrf_token(self.listing.request),
        )

    def get_cell_value(self, rec):
        context = self.get_buttons_context(rec)
        template = self.get_buttons_template(rec)
        return template.render(context)

    def get_button_context(self, name, rec):
        return dict(
            name=name,
            type="submit",
        )

    def manage_button_action(self, *args, **kwargs):
        meth_name = f"manage_button_{self.action_button}_action"
        # Search method in listing object first
        action_method = getattr(self.listing, meth_name, None)
        if action_method is not None:
            return action_method(
                self, *args, **kwargs
            )  # give col objet to listing method
        # Search method in column object otherwise
        action_method = getattr(self, meth_name, None)
        if action_method is None:
            raise ListingException(f'Unknown "{self.action_button}" action.')
        return action_method(*args, **kwargs)

    def build_url_func_params(self, rec):
        listing = self.listing
        if not listing.request:
            raise ListingException("Listing requires Request object")
        rm = listing.request.resolver_match
        return [
            listing,
            rec.get_object(),
            rm.url_name,
            rm.args,
            rm.kwargs,
        ]

    # ---------------- MOVE UP --------------------------------------------------
    move_up__icon = "listing-icon-up-open"
    move_up__text = _("Move up")
    move_up__title = _("Change order up")
    move_up__field = "order"

    def get_button_move_up_context(self, name, rec):
        first = self.listing.records.get_first_obj()
        is_first = rec.pk == first.pk
        return dict(
            type="button" if is_first else "submit",
            disabled=is_first,
        )

    def manage_button_move_up_action(self, *args, **kwargs):
        if not isinstance(self.action_pk, int):
            raise ListingException(
                f"Bad object Id ({self.action_pk}) "
                f'for action "{self.action_button}"'
            )
        first = self.listing.records.get_first_obj()
        obj = self.listing.records.get_obj(pk=self.action_pk)
        if first and obj:
            field = self.move_up__field
            first_order = getattr(first, field)
            obj_order = getattr(obj, field)
            if first_order < obj_order:
                self.listing.records.move_obj_order(obj, field, -1)
            elif first_order > obj_order:
                self.listing.records.move_obj_order(obj, field, 1)

    # ---------------- MOVE DOWN ------------------------------------------------
    move_down__icon = "listing-icon-down-open"
    move_down__text = _("Move down")
    move_down__title = _("Change order down")
    move_down__field = "order"

    def get_button_move_down_context(self, name, rec):
        last = self.listing.records.get_last_obj()
        is_last = rec.pk == last.pk
        return dict(
            type="button" if is_last else "submit",
            disabled=is_last,
        )

    def manage_button_move_down_action(self, *args, **kwargs):
        if not isinstance(self.action_pk, int):
            raise ListingException(
                f"Bad object Id ({self.action_pk}) "
                f'for action "{self.action_button}"'
            )
        last = self.listing.records.get_last_obj()
        obj = self.listing.records.get_obj(pk=self.action_pk)
        if last and obj:
            field = self.move_down__field
            last_order = getattr(last, field)
            obj_order = getattr(obj, field)
            if last_order < obj_order:
                self.listing.records.move_obj_order(obj, field, -1)
            elif last_order > obj_order:
                self.listing.records.move_obj_order(obj, field, 1)

    # ---------------- VIEW OBJECT ----------------------------------------------
    view_object__icon = "listing-icon-magnifier"
    view_object__text = _("Details")
    view_object__title = _("See details")
    view_object__url_func = None

    def get_button_view_object_context(self, name, rec):
        if self.view_object__url_func:
            return dict(
                type="extlink",
                url=self.view_object__url_func(*self.build_url_func_params(rec)),
            )
        return dict(type="extlink", url=rec.get_href())

    # ---------------- EDIT OBJECT ----------------------------------------------
    edit_object__icon = "listing-icon-pencil"
    edit_object__text = _("Edit")
    edit_object__title = _("Edit")
    edit_object__url_func = None
    edit_object__method = "get_edit_absolute_url"

    def get_button_edit_object_context(self, name, rec):
        if self.edit_object__url_func:
            return dict(
                type="extlink",
                url=self.edit_object__url_func(*self.build_url_func_params(rec)),
            )
        method = getattr(rec.get_object(), self.edit_object__method, None)
        if method is None:
            raise InvalidColumn(
                f"Please define the method {self.edit_object__method}() "
                f"in class {rec.get_object().__class__.__name__}"
            )
        return dict(type="extlink", url=method())

    # ---------------- DELETE OBJECT ----------------------------------------------
    delete_object__icon = "listing-icon-trash-empty"
    delete_object__text = _("Delete")
    delete_object__title = _("Delete")
    delete_object__url_func = None
    delete_object__method = "get_delete_absolute_url"

    def get_button_delete_object_context(self, name, rec):
        if self.delete_object__url_func:
            return dict(
                type="extlink",
                url=self.delete_object__url_func(*self.build_url_func_params(rec)),
            )
        method = getattr(rec.get_object(), self.delete_object__method, None)
        if method is None:
            raise InvalidColumn(
                f"Please define the method {self.delete_object__method}() "
                f"in class {rec.get_object().__class__.__name__}"
            )
        return dict(type="extlink", url=method())

    # ---------------- VIEW OBJECT POPUP ----------------------------------------
    view_object_popup__icon = "listing-icon-magnifier"
    view_object_popup__text = _("Details")
    view_object_popup__title = _("See details")
    view_object_popup__template_name = ThemeTemplate("view_object_popup.html")
    view_object_popup__layout = ""
    view_object_popup__label_ending = " :"
    view_object_popup__display_empty = True
    view_object_popup__empty_msg = _("Not set")

    def get_button_view_object_popup_context(self, name, rec):
        return dict(type="link", url="#")  # use jquery

    def get_view_object_popup_template(self):
        return self.view_object_popup__template_name

    def get_view_object_popup_layout(self):
        return str(self.view_object_popup__layout)  # str() is important here

    def manage_button_view_object_popup_action(self, *args, **kwargs):
        layout = self.get_view_object_popup_layout()
        if (not layout or layout.startswith("-")) and self.listing.model:
            exclude = layout[1:].split(",")
            layout = ";".join(
                [
                    f.name
                    for f in self.listing.model._meta.get_fields()
                    if (
                        not isinstance(f, (models.ManyToManyRel, models.ManyToOneRel))
                        and f.name not in exclude
                    )
                ]
            )
        if isinstance(layout, str):
            # transform layout string into list of lists of list
            layout = list(map(lambda s: s.split(","), layout.split(";")))
        else:
            raise ListingException(
                gettext("You must specify a layout in " "view_object_popup__layout")
            )
        if self.action_pk is None:
            raise ListingException(gettext("Object id not specified !"))
        rec = self.listing.records.get_rec(pk=self.action_pk)
        rows = []
        max_col = 1
        for layout_row in layout:
            cols = []
            for layout_col in layout_row:
                layout_col, *colspan = layout_col.rsplit("*", 1)
                layout_col = layout_col.strip()
                try:
                    # field*2 mean span field onto 2 x (field label + value cell)
                    # So the HTML "colspan" applied on value field needs some calculations
                    colspan = int(colspan[0].strip()) * 2 - 1
                except (ValueError, IndexError):
                    # no colspan attribute
                    colspan = 0
                if not layout_col:
                    label = ""
                    value = ""
                elif layout_col.startswith("=="):
                    label = "== section =="
                    value = re.sub(r"=+\s*(\S.*?\S)\s*=+$", r"\1", layout_col)
                else:
                    # layout_col could be 'field' or 'A forced label:field'
                    if ":" in layout_col:
                        forced_label, field = layout_col.rsplit(":", 1)
                    else:
                        forced_label, field = None, layout_col
                    col = self.listing.columns.get(field)
                    # if column not defined in listing because not displayed,
                    # create it on-the-fly :
                    if not col and self.listing.model:
                        col = ModelColumns.create_column_name(self.listing, field)
                    if col:
                        label = forced_label or col.get_header_value()
                        value = col.render_cell(rec)
                    else:
                        label = forced_label or field
                        value = gettext("*** Not a valid column name ***")
                if colspan:
                    value = re.sub(
                        r"(<td[^>]*)", rf'\1 colspan="{colspan}"', value, re.I
                    )
                cols.append((label, value))

            rows.append(cols)
            max_col = max(max_col, len(cols))

        context = dict(
            object=rec.get_object(),
            rows=rows,
            full_colspan=max_col * 2,
            action_column=self,
            label_ending=self.view_object_popup__label_ending,
            display_empty=self.view_object_popup__display_empty,
            empty_msg=self.view_object_popup__empty_msg,
        )
        template_name = self.get_view_object_popup_template()
        template = loader.get_template(template_name)
        return HttpResponse(template.render(context))
