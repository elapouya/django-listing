#
# Created : 2018-02-09
#
# @author: Eric Lapouyade
#
import json
import traceback
from urllib.parse import parse_qs

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from django.db import models
from django.db.models import QuerySet
from django.forms.models import construct_instance
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseServerError,
    QueryDict,
    JsonResponse,
)
from django.template import RequestContext, loader
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from .exceptions import *
from .listing import Listing, logger
from .attached_form import AttachedForm

__all__ = [
    "INSTANCE_METHOD_PREFIX",
    "LISTING_REDIRECT_NONE",
    "LISTING_REDIRECT_NO_EDIT",
    "LISTING_REDIRECT_SAME_PAGE",
    "ListingView",
    "ListingViewMixin",
]

from .utils import is_ajax

INSTANCE_METHOD_PREFIX = "get_listing_instance_"
LISTING_REDIRECT_NONE = None
LISTING_REDIRECT_SAME_PAGE = 1
LISTING_REDIRECT_NO_EDIT = 2


class ListingViewMixin:
    listing_class = None
    listing_data = None
    upload_field = "image"
    context_classes = ()
    listing_context_name = "listing"
    listing_instance = None
    listing = None
    insert_success_redirect_url = LISTING_REDIRECT_NONE
    insert_success_msg = _("<b>{object}</b> has been successfully added.")
    insert_success_msg_no_save = _(
        "The form is valid but nothing has been added to database "
        "as <tt>save_to_database=False</tt>."
    )
    update_success_redirect_url = LISTING_REDIRECT_NONE
    update_success_msg = _(
        "<b>{nb_updates} {model_verbose}</b> " "has been successfully updated."
    )
    update_success_msg_no_save = _(
        "The form is valid but nothing has been updated to database "
        "as <tt>save_to_database=False</tt>."
    )
    is_ajax = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._listing_instances = {}
        self._formset_errors = {}
        self.ajax_request_context = None

    def post(self, request, *args, **kwargs):
        # make POST data mutable
        request.POST = request.POST.copy()
        if hasattr(self, "get_object"):  # for DetailView that works only on GET
            self.object = self.get_object()
        try:
            self.is_ajax = is_ajax(request)
            if self.is_ajax:
                try:
                    if "serialized_data" in request.POST:
                        serialized_data = request.POST.pop("serialized_data")
                        if isinstance(serialized_data, list):
                            serialized_data = serialized_data[0]
                        data = parse_qs(serialized_data)
                        for k, v in data.items():
                            if k != "csrfmiddlewaretoken":
                                if len(v) == 1:
                                    request.POST[k] = v[0]
                                else:
                                    request.POST[k] = v
                    return self.manage_listing_ajax_request(request, *args, **kwargs)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    stack = traceback.format_exc()
                    logger.error(stack)
                    return HttpResponseServerError(e)
            response = self.manage_listing_post(request, *args, **kwargs)
            if response:
                return response
            return self.get(request, *args, **kwargs)
        except ListingException as e:
            return HttpResponseServerError(str(e))

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # need to force rendering here to know whether a listing created
        # in a template has requested a data export
        response.render()
        if hasattr(request, "export_data"):
            data = request.export_data
            filename = getattr(request, "export_filename", "listing")
            response = HttpResponse(data)
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(
                filename
            )
            response.set_cookie("file_generation", "done")
            return response
        return response

    def json_response(self, data, **kwargs):
        if hasattr(self, "listing_patch_json_response_data"):
            self.listing_patch_json_response_data(data)
        response = JsonResponse(data, **kwargs)
        response["Cache-Control"] = "no-cache"
        return response

    def get_listing_from_post(self, request, refresh=False):
        listing_id = request.POST.get("listing_id", "")[:-3]  # remove '-id' suffix
        listing_suffix = request.POST.get("listing_suffix", "")
        listing = self.get_listing_id(listing_id, refresh)
        if not listing:
            raise ListingException(
                "{}-id is a bad listing ID : django-listing library misconf"
                "iguration. Contact the webmaster !".format(listing_id)
            )
        Listing.set_suffix(request, listing, listing_suffix)
        listing.action = request.POST.get("force_action") or request.POST.get("action")
        listing.action_col = request.POST.get("action_col")
        listing.request = request
        return listing

    def manage_listing_ajax_request(self, request, *args, **kwargs):
        listing = self.get_listing_from_post(request)
        self.ajax_request_context = RequestContext(request)
        self.ajax_request_context.update(self.get_context_data(**kwargs))
        self.listing = listing
        response = None
        if listing:
            listing.set_view(self)
            listing_part = request.POST.get("listing_part", "all")
            listing.ajax_request = True
            listing.ajax_part = listing_part
            if isinstance(listing.action, str) and listing.action:
                listing.render_init_context(self.ajax_request_context)
                method = getattr(self, "manage_listing_%s" % listing.action, None)
                if callable(method):
                    response = method(listing, *args, **kwargs)
        if response:
            return response
        if listing.have_to_refresh():
            listing = self.get_listing_from_post(request, refresh=True)
        return HttpResponse(listing.render(self.ajax_request_context))

    def get_listing_class(self):
        return self.listing_class

    def get_listing_data(self):
        return self.listing_data

    def get_listing_context_name(self):
        return self.listing_context_name

    def get_listing_params(self):
        keys = list(Listing.get_params_keys()) + [
            k for k in self.__class__.__dict__ if "__" in k and not k.startswith("__")
        ]  # add listing columns custimization keys (colname__attribute)
        return {k: getattr(self, k) for k in keys if hasattr(self, k)}

    def get_listing_instance(self):
        data = self.get_listing_data()
        if isinstance(data, (QuerySet, list)) or data:
            listing_class = self.get_listing_class() or Listing
            return listing_class(data, **self.get_listing_params())

    # this set of methods manage a special storage because when using ajax
    # listing name are taken from div id which has been normalized
    # by replacing underscores by dashes
    def get_from_listing_instances(self, name):
        v = self._listing_instances.get(name.replace("_", "-"))
        if v:
            return v[1]
        return None

    def in_listing_instances(self, name):
        return name.replace("_", "-") in self._listing_instances

    def set_to_listing_instances(self, name, instance):
        self._listing_instances[name.replace("_", "-")] = (name, instance)

    def yield_listing_instances(self):
        for v in self._listing_instances.values():
            yield v[1]

    def listing_instances_context(self):
        return dict(self._listing_instances.values())

    def get_default_listing_instance(self):
        context_name = self.get_listing_context_name()
        instance = self.get_from_listing_instances(context_name)
        if not instance:
            instance = self.get_listing_instance()
            if instance:
                # instance.id = (
                #     context_name + "-id"
                # )  # Ensure id is set according to method name + '-id'
                self.set_to_listing_instances(context_name, instance)
        return instance

    def get_listing_update_success_redirect_url(self, listing=None):
        url = self.update_success_redirect_url
        if listing:
            if url == LISTING_REDIRECT_SAME_PAGE:
                url = listing.get_url()
            elif url == LISTING_REDIRECT_NO_EDIT:
                url = listing.get_url(without="editing,editing_columns,editing_row_pk")
        # if url = None will do a LISTING_REDIRECT_NONE : the post() will call get()
        # at the end on the same request.
        return url

    def get_listing_insert_success_redirect_url(self, listing=None):
        url = self.insert_success_redirect_url
        if listing:
            if url == LISTING_REDIRECT_SAME_PAGE:
                url = listing.get_url()
            elif url == LISTING_REDIRECT_NONE:
                # post() will call get() on-the-fly
                # to avoid a new request to the server.
                # That requires to reset insert form by removing Post data
                listing.request.POST = QueryDict()
        return url

    def manage_listing_post(self, request, *args, **kwargs):
        if "action" in request.POST:
            listing = self.get_listing_from_post(request)
            self.listing = listing
            response = None
            if listing:
                listing.render_init(RequestContext(request))
                listing.set_view(self)
                if isinstance(listing.action, str) and listing.action:
                    method = getattr(self, "manage_listing_%s" % listing.action, None)
                    if callable(method):
                        response = method(listing, *args, **kwargs)
                # elif listing.can_edit:
                #     response = self.manage_listing_update(listing, *args, **kwargs)
                # elif listing.can_select:
                #     response = self.manage_listing_select(listing, *args, **kwargs)
            return response

    def manage_listing_upload(self, listing, *args, **kwargs):
        # Work in progress !
        listing.model.objects.create(
            **{self.upload_field: listing.request.FILES["file"]}
        )
        return self.json_response(
            dict(
                message="OK",
            )
        )

    def manage_listing_update(self, listing, *args, **kwargs):
        if listing.editable and listing.editing:
            formset = listing.get_formset()
            if formset.is_valid():
                return self.manage_listing_update_valid(listing, formset)
            else:
                # extract error strings from Django ErrorDict
                listing.row_form_errors = [
                    ", ".join(list(e["__all__"]))
                    for e in formset.errors
                    if "__all__" in e
                ]

    def get_form_instance(self, listing):
        if listing.attached_form:
            if isinstance(listing.attached_form, AttachedForm):
                django_form = listing.attached_form.get_form()
            elif isinstance(listing.attached_form, forms.Form):
                django_form = listing.attached_form
            else:
                if isinstance(listing.attached_form, str):
                    form_class = import_string(listing.attached_form)
                else:
                    form_class = listing.attached_form
                django_form = form_class(listing.request.POST, listing.request.FILES)
        else:
            layout = listing.request.POST.get("attached_form_layout")
            name = listing.request.POST.get("attached_form_name")
            if not layout or not name:
                raise InvalidAttachedForm(
                    "At least a form layout and name are mandatory in POST data "
                    "to build a relevant form instance"
                )
            attached_form = AttachedForm(name=name, layout=layout)
            attached_form = attached_form.bind_to_listing(listing)
            django_form = attached_form.get_form()
        return django_form

    def manage_listing_insert(self, listing, *args, **kwargs):
        form = self.get_form_instance(listing)
        if form.is_valid():
            return self.manage_listing_insert_valid(listing, form)

    def manage_listing_action_button(self, listing, *args, **kwargs):
        col_name = listing.action_col
        if col_name:
            col = listing.columns.get(col_name)
            if col:
                return col.manage_button_action(*args, **kwargs)
        raise ListingException(f'Unknown action column "{col_name}"')

    def manage_listing_attached_form(self, listing, *args, **kwargs):
        """
        To manage a simple action that does not required the form to be instanciated,
        one can define such method:

        in view :
            manage_attached_form_<action>_action(self, listing, *args, **kwargs)
        in listing :
            manage_attached_form_<action>_action(self, *args, **kwargs)

        But for form processing, one can define such method:

        in view :
            manage_attached_form_<action>_process(self, listing, form, instance, *args, **kwargs)
        in listing :
            manage_attached_form_<action>_process(self, form, instance, *args, **kwargs)

        For ajax requests methods must return None or a dict like this :

            {
                "listing": <html code to replace actual listing>,
                "attached_form": <html code to replace actual form>,
            }

            If givent listing or attached_form html code is None, it will be
            automatically calculated.
            If methods returns None instead of a the dict. The dict will be
            automatically calculated.
        """
        # Test permissions
        # Note : action_button is automatically set from POST during listing init
        action = listing.action_button
        if not listing.has_permission_for_action(action):
            raise PermissionDenied(gettext("You do not have the required permission"))

        # Read selected listing rows
        selected_rows = listing.get_selected_rows()

        # if a specific action method is available in view or listing : use it
        action_meth_name = f"manage_attached_form_{action}_action"
        # Search method in view object first
        action_method = getattr(self, action_meth_name, None)
        if action_method:
            return action_method(listing, *args, **kwargs)
        action_method = getattr(listing, action_meth_name, None)
        if action_method:
            return action_method(*args, **kwargs)

        # if a specific get_form() method is available in view or listing : use it
        action_meth_name = f"manage_attached_form_{action}_get_form"
        # Search method in listing object first
        get_form_method = getattr(listing, action_meth_name, None)
        if get_form_method:
            form = get_form_method(*args, **kwargs)
        else:
            get_form_method = getattr(self, action_meth_name, None)
            if get_form_method:
                form = get_form_method(listing, *args, **kwargs)
            else:
                attached_form = listing.attached_form
                form = attached_form.get_form()

        # create instance from database if possible
        instance = None
        object_pk = listing.request.POST.get("object_pk")
        if object_pk:
            instance = listing.model.objects.filter(pk=object_pk).first()
        form.instance = instance
        if form.is_valid():
            # if no instance, build it from form cleaned_data:
            if not instance:
                instance = listing.model()
            form.instance = construct_instance(form, instance)

            process_meth_name = f"manage_attached_form_{action}_process"
            # Search method in listing object first
            process_method = getattr(listing, process_meth_name, None)
            if process_method:
                mixed_response = process_method(form, instance, *args, **kwargs)
            else:
                process_method = getattr(self, process_meth_name, None)
                if not process_method:
                    raise ListingException(
                        f'Do not know how to manage "{action}" action. '
                        f"Please define {action_meth_name}() or {process_meth_name}() "
                        f"in your view or your in your listing."
                    )
                mixed_response = process_method(
                    listing, form, instance, *args, **kwargs
                )
            self.listing.request.POST[instance._meta.pk.attname] = instance.pk
            if listing.processed_flash:
                if len(selected_rows) < 2:
                    if instance.pk:
                        listing.processed_pks = {instance.pk}
                else:
                    listing.processed_pks = set(selected_rows)
            if not self.is_ajax:
                return None
            listing.compute_current_page_records()
            form_html = listing.attached_form.render(self.ajax_request_context)
            if mixed_response is None:
                listing_html = listing.render(self.ajax_request_context)
                mixed_response = {
                    "listing": listing_html,
                    "attached_form": form_html,
                    "object_pk": instance.pk,
                }
            else:
                if "listing" in mixed_response and mixed_response["listing"] is None:
                    listing_html = listing.render(self.ajax_request_context)
                    mixed_response["listing"] = listing_html
                if (
                    "attached_form" in mixed_response
                    and mixed_response["attached_form"] is None
                ):
                    mixed_response["attached_form"] = form_html
            if instance.pk:
                mixed_response["object_pk"] = instance.pk
            return self.json_response(mixed_response)
        else:
            if not self.is_ajax:
                return None
            form_html = listing.attached_form.render(self.ajax_request_context)
            return self.json_response({"attached_form": form_html})

    def manage_attached_form_insert_get_form(self, listing, *args, **kwargs):
        form = listing.attached_form.get_form()
        id_field = form.fields.get("id")
        if id_field:
            id_field.required = False
        return form

    def manage_attached_form_insert_process(
        self, listing, form, instance, *args, **kwargs
    ):
        instance.pk = None  # needed to force insert vs update
        instance.save()
        listing.page = "last"
        listing.sort = "id"

    def manage_attached_form_update_get_form(self, listing, *args, **kwargs):
        # Fields are not required only in mass update (more than one row selected)
        form = listing.attached_form.get_form(
            force_not_required=len(listing.get_selected_rows()) > 1
        )
        # trigger default checks
        form.full_clean()
        # add error if no row selected
        if len(listing.get_selected_rows()) == 0:
            form.add_error(
                None, gettext("Please select at least one item in the listing")
            )
        return form

    def manage_attached_form_update_process(
        self, listing, form, instance, *args, **kwargs
    ):
        selected_rows = listing.get_selected_rows()
        if len(selected_rows) == 1 and instance.pk:
            instance.save()
        else:
            update_fields = {
                k: v for k, v in form.cleaned_data.items() if v and k != "id"
            }
            listing.model.objects.filter(pk__in=selected_rows).update(**update_fields)

    def manage_attached_form_update_all_get_form(self, listing, *args, **kwargs):
        return listing.attached_form.get_form(force_not_required=True)

    def manage_attached_form_update_all_process(
        self, listing, form, instance, *args, **kwargs
    ):
        update_fields = {k: v for k, v in form.cleaned_data.items() if v and k != "id"}
        listing.records.get_filtered_queryset().update(**update_fields)

    def manage_attached_form_duplicate_get_form(self, listing, *args, **kwargs):
        form = listing.attached_form.get_form(force_not_required=True)
        selected_rows = listing.get_selected_rows()
        if len(selected_rows) == 0:
            form.add_error(None, gettext("Please select one item"))
        elif len(selected_rows) > 1:
            form.add_error(
                None, gettext("You can duplicate only one item at the same time")
            )
        return form

    def manage_attached_form_duplicate_process(
        self, listing, form, instance, *args, **kwargs
    ):
        if len(listing.get_selected_rows()) == 1 and instance.pk:
            instance.pk = None
            instance.save()

    def manage_attached_form_delete_get_form(self, listing, *args, **kwargs):
        form = listing.attached_form.get_form(force_not_required=True)
        if len(listing.get_selected_rows()) == 0:
            form.add_error(None, gettext("Please select at least one item"))
        return form

    def manage_attached_form_delete_process(
        self, listing, form, instance, *args, **kwargs
    ):
        selected_rows = listing.get_selected_rows()
        if len(selected_rows) == 1 and instance.pk:
            instance.delete()
        else:
            listing.model.objects.filter(pk__in=selected_rows).delete()

    def manage_attached_form_delete_all_get_form(self, listing, *args, **kwargs):
        return listing.attached_form.get_form(force_not_required=True)

    def manage_attached_form_delete_all_process(
        self, listing, form, instance, *args, **kwargs
    ):
        listing.records.get_filtered_queryset().delete()

    def manage_attached_form_clear_action(self, listing, *args, **kwargs):
        attached_form = listing.attached_form
        # Purge all post data except csrf token
        self.request.POST = dict(
            csrfmiddlewaretoken=self.request.POST.get("csrfmiddlewaretoken")
        )
        form_html = attached_form.render(self.ajax_request_context)
        return self.json_response({"attached_form": form_html})

    def listing_save_rows_to_database(self, listing, formset):
        updated_rows_pk = []
        if issubclass(listing.model, models.Model):
            for row in formset.cleaned_data:
                pk = row.get(listing.primary_key)
                if pk:
                    listing.model.objects.filter(pk=pk).update(**row)
                    updated_rows_pk.append(pk)
        return updated_rows_pk

    def manage_listing_update_valid(self, listing, formset):
        if listing.save_to_database:
            updated_rows_pk = self.listing_save_rows_to_database(listing, formset)
        self.send_listing_update_success_message(listing, updated_rows_pk)
        redirect_to = self.get_listing_update_success_redirect_url(listing)
        if redirect_to:
            return HttpResponseRedirect(redirect_to)

    def listing_insert_into_database(self, listing, form):
        if issubclass(listing.model, models.Model):
            object = listing.model(**form.cleaned_data)
            object.save()
        return object

    def manage_listing_insert_valid(self, listing, form):
        object = None
        if listing.save_to_database:
            object = self.listing_insert_into_database(listing, form)
        self.send_listing_insert_success_message(listing, form, object)
        redirect_to = self.get_listing_insert_success_redirect_url(listing)
        if redirect_to:
            return HttpResponseRedirect(redirect_to)

    def send_listing_insert_success_message(self, listing, form, object):
        if listing.save_to_database:
            msg = self.insert_success_msg.format(
                listing=listing, form=form, object=object
            )
            if msg:
                messages.add_message(listing.request, messages.SUCCESS, mark_safe(msg))
        else:
            msg = self.insert_success_msg_no_save.format(
                listing=listing, form=form, object=object
            )
            if msg:
                messages.add_message(listing.request, messages.INFO, mark_safe(msg))

    def send_listing_update_success_message(self, listing, updated_rows_pk):
        nb_updates = len(updated_rows_pk)
        meta = listing.model._meta
        model_verbose = (
            meta.verbose_name_plural if nb_updates > 0 else meta.verbose_name_plural
        )
        if listing.save_to_database:
            msg = self.update_success_msg.format(
                listing=listing, nb_updates=nb_updates, model_verbose=model_verbose
            )
            if msg:
                messages.add_message(listing.request, messages.SUCCESS, mark_safe(msg))
        else:
            msg = self.update_success_msg_no_save.format(
                listing=listing, nb_updates=nb_updates, model_verbose=model_verbose
            )
            if msg:
                messages.add_message(listing.request, messages.INFO, mark_safe(msg))

    def get_listing_id(self, listing_id, refresh=False):
        """For AJAX purposes : when using multiple listings on the same page
        and having one AJAX request : we need only ONE listing instance :
        the one from the given ID in the request. This avoids to create
        all listing instances when not necessary"""
        if isinstance(listing_id, str):
            instance = self.get_from_listing_instances(listing_id)
            if instance is None or refresh == True:
                method = getattr(
                    self, INSTANCE_METHOD_PREFIX + listing_id.replace("-", "_"), None
                )
                if callable(method):
                    instance = method()
                    self.set_to_listing_instances(listing_id, instance)
                else:
                    instance = self.get_default_listing_instance()
            if instance:
                instance.id = listing_id + "-id"
            return instance
        return None

    def get_listings_instances(self):
        prefix_length = len(INSTANCE_METHOD_PREFIX)
        # find all get_listing_instance_xxx
        for method_name in dir(self.__class__):
            if method_name.startswith(INSTANCE_METHOD_PREFIX):
                method = getattr(self, method_name)
                if callable(method):
                    listing_id = method_name[prefix_length:]
                    if not self.in_listing_instances(listing_id):
                        instance = method()
                        instance.id = (
                            listing_id + "-id"
                        )  # Ensure id is set according to method name + '-id'
                        self.set_to_listing_instances(listing_id, instance)
        self.get_default_listing_instance()  # will update self._listing_instances
        for listing in self.yield_listing_instances():
            listing.request = self.request
            if listing.is_initialized() and not listing.is_render_initialized():
                listing.render_init(RequestContext(self.request))

        return self.listing_instances_context()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["request"] = self.request  # no need to add request context processor
        context["posted_listing"] = self.listing
        context["view"] = self
        for cls in self.context_classes:
            context[cls.__name__] = cls
        if self.listing_class:
            context[self.listing_class.__name__] = self.listing_class
        context.update(self.get_listings_instances())
        return context


class ListingView(ListingViewMixin, TemplateView):
    pass
