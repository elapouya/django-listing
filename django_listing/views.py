#
# Created : 2018-02-09
#
# @author: Eric Lapouyade
#
from django.db.models import QuerySet
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView
from django.http import HttpResponse, HttpResponseServerError, \
    HttpResponseRedirect, QueryDict
from django.template import RequestContext
from django.db import models
from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ugettext
from django.template import loader
from .listing import Listing, logger
from .listing_form import ListingForm
from .exceptions import *
from urllib.parse import parse_qs


__all__ = [
    'ListingView', 'ListingViewMixin','INSTANCE_METHOD_PREFIX',
    'LISTING_REDIRECT_NONE', 'LISTING_REDIRECT_SAME_PAGE',
    'LISTING_REDIRECT_NO_EDIT',
]

INSTANCE_METHOD_PREFIX = 'get_listing_instance_'
LISTING_REDIRECT_NONE = None
LISTING_REDIRECT_SAME_PAGE = 1
LISTING_REDIRECT_NO_EDIT = 2

class ListingViewMixin:
    listing_class = None
    listing_data = None
    context_classes = ()
    listing_context_name = 'listing'
    listing_instance = None
    listing = None
    update_success_redirect_url = LISTING_REDIRECT_NONE
    insert_success_msg = _('<b>{object}</b> has been successfully added.')
    insert_success_msg_no_save = _(
        'The form is valid but nothing has been added to database '
        'as <tt>save_to_database=False</tt>.')
    update_success_msg = _('<b>{nb_updates} {model_verbose}</b> '
                           'has been successfully updated.')
    update_success_msg_no_save = _(
        'The form is valid but nothing has been updated to database '
        'as <tt>save_to_database=False</tt>.')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._listing_instances = {}

    def post(self, request, *args, **kwargs):
        try:
            if request.is_ajax():
                if 'serialized_data' in request.POST:
                    post = request.POST.copy()
                    serialized_data = post.pop('serialized_data')
                    if isinstance(serialized_data, list):
                        serialized_data = serialized_data[0]
                    data = parse_qs(serialized_data)
                    for k,v in data.items():
                        if k != 'csrfmiddlewaretoken':
                            if len(v) == 1:
                                post[k] = v[0]
                            else:
                                post[k] = v
                    request.POST = post
                return self.manage_listing_ajax_request(request, *args, **kwargs)
            response = self.manage_listing_post(request, *args, **kwargs)
            if response:
                return response
            return self.get(request, *args, **kwargs)
        except ListingException as e:
            return HttpResponseServerError(e)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # need to force rendering here to know whether a listing created
        # in a template has requested a data export
        response.render()
        if hasattr(request,'export_data'):
            data = request.export_data
            filename = getattr(request,'export_filename','listing')
            response = HttpResponse(data)
            response['Content-Disposition'] = (
                'attachment; filename="{}"'.format(filename) )
            return response
        return response

    def get_listing_from_post(self, request):
        listing_id = request.POST.get('listing_id', '')[:-3]  # remove '-id' suffix
        listing_suffix = request.POST.get('listing_suffix', '')
        listing = self.get_listing_id(listing_id)
        if not listing:
            raise ListingException(
                '{}-id is a bad listing ID : django-listing library misconf'
                'iguration. Contact the webmaster !'.format(listing_id))
        Listing.set_suffix(request, listing, listing_suffix)
        listing.action = request.POST.get('action')
        listing.action_col = request.POST.get('action_col')
        return listing

    def manage_listing_ajax_request(self, request, *args, **kwargs):
        listing = self.get_listing_from_post(request)
        self.listing = listing
        response = None
        if listing:
            listing_part = request.POST.get('listing_part', 'all')
            listing.set_attr('ajax_request', True)
            listing.set_attr('ajax_part', listing_part)
            if isinstance(listing.action, str) and listing.action:
                listing.render_init(RequestContext(request))
                method = getattr(self,'manage_listing_%s' % listing.action, None)
                if callable(method):
                    response = method(listing, *args, **kwargs)
        if response:
            return response
        return HttpResponse(listing.render(RequestContext(request)))

    def get_listing_class(self):
        return self.listing_class

    def get_listing_data(self):
        return self.listing_data

    def get_listing_context_name(self):
        return self.listing_context_name

    def get_listing_params(self):
        keys = ( list(Listing.get_params_keys()) +
                 [ k for k in self.__class__.__dict__
                   if '__' in k and not k.startswith('__') ] )  # add listing columns custimization keys (colname__attribute)
        return { k:getattr(self,k) for k in keys if hasattr(self,k) }

    def get_listing_instance(self):
        data = self.get_listing_data()
        if isinstance(data, QuerySet) or data:
            listing_class = self.get_listing_class() or Listing
            return listing_class(data,**self.get_listing_params())

    def get_default_listing_instance(self):
        context_name = self.get_listing_context_name()
        instance = self._listing_instances.get(context_name)
        if not instance:
            instance = self.get_listing_instance()
            if instance:
                instance.id = context_name + '-id'  # Ensure id is set according to method name + '-id'
                self._listing_instances[context_name] = instance
        return instance

    def get_listing_update_success_redirect_url(self, listing = None):
        url = self.update_success_redirect_url
        if listing:
            if url == LISTING_REDIRECT_SAME_PAGE:
                url = listing.get_url()
            elif url == LISTING_REDIRECT_NO_EDIT:
                url = listing.get_url(
                    without='editing,editing_columns,editing_row_pk')
        # if url = None will do a LISTING_REDIRECT_NONE : the post() will call get()
        # at the end on the same request.
        return url

    def get_listing_insert_success_redirect_url(self, listing = None):
        url = self.insert_success_redirect_url
        if listing:
            if url == LISTING_REDIRECT_SAME_PAGE:
                url = listing.get_url()
            elif url == LISTING_REDIRECT_NONE :
                # post() will call get() on-the-fly
                # to avoid a new request to the server.
                # That requires to reset insert form by removing Post data
                listing.request.POST = QueryDict()
        return url

    def manage_listing_post(self, request, *args, **kwargs):
        if 'action' in request.POST:
            listing = self.get_listing_from_post(request)
            listing.set_view(self)
            self.listing = listing
            response = None
            if listing:
                listing.render_init(RequestContext(request))
                if isinstance(listing.action, str) and listing.action:
                    method = getattr(self,'manage_listing_%s' % listing.action, None)
                    if callable(method):
                        response = method(listing, *args, **kwargs)
                # elif listing.can_edit:
                #     response = self.manage_listing_update(listing, *args, **kwargs)
                # elif listing.can_select:
                #     response = self.manage_listing_select(listing, *args, **kwargs)
            return response

    def manage_listing_update(self, listing, *args, **kwargs):
        if listing.editable and listing.editing:
            formset = listing.get_formset()
            if formset.is_valid():
                return self.manage_listing_update_valid(listing, formset)

    def get_form_instance(self, listing):
        if listing.form:
            if isinstance(listing.form, ListingForm):
                django_form = listing.form.get_form()
            elif isinstance(listing.form, forms.Form):
                django_form = listing.form
            else:
                if isinstance(listing.form, str):
                    form_class = import_string(listing.form)
                else:
                    form_class = listing.form
                django_form = form_class(listing.request.POST,
                                         listing.request.FILES)
        else:
            layout = listing.request.POST.get('listing_form_layout')
            name = listing.request.POST.get('listing_form_name')
            if not layout or not name:
                raise InvalidListingForm(ugettext(
                    'At least a form layout and name are mandatory in POST data '
                    'to build a relevant form instance'))
            listing_form = ListingForm(listing.action, name=name, layout=layout)
            listing_form.bind_to_listing(listing)
            django_form = listing_form.get_form()
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

    # def manage_listing_select(self, listing, *args, **kwargs):
    #     if listing.selectable and listing.selecting:
    #         return self.manage_listing_selected_rows(listing)
    #
    # def manage_listing_selected_rows(self, listing):
    #     # to be overriden if needed by the developper by subclassing
    #     # use listing.get_selected_rows() to get selected_rows
    #     pass

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
            msg = ( self.insert_success_msg
                .format(listing=listing, form=form, object=object) )
            if msg:
                messages.add_message(listing.request, messages.SUCCESS,
                    mark_safe(msg))
        else:
            msg = ( self.insert_success_msg_no_save
                .format(listing=listing, form=form, object=object) )
            if msg:
                messages.add_message(listing.request, messages.INFO,
                    mark_safe(msg))

    def send_listing_update_success_message(self, listing, updated_rows_pk):
        nb_updates = len(updated_rows_pk)
        meta = listing.model._meta
        model_verbose = ( meta.verbose_name_plural if nb_updates > 0
                          else meta.verbose_name_plural )
        if listing.save_to_database:
            msg = ( self.update_success_msg
                .format(listing=listing, nb_updates=nb_updates,
                        model_verbose=model_verbose) )
            if msg:
                messages.add_message(listing.request, messages.SUCCESS,
                    mark_safe(msg))
        else:
            msg = ( self.update_success_msg_no_save
                .format(listing=listing, nb_updates=nb_updates,
                        model_verbose=model_verbose) )
            if msg:
                messages.add_message(listing.request, messages.INFO,
                    mark_safe(msg))

    def get_listing_id(self, listing_id):
        """ For AJAX purposes : when using multiple listings on the same page
        and having one AJAX request : we need only ONE listing instance :
        the one from the given ID in the request. This avoids to create
        all listing instances when not necessary """
        if isinstance(listing_id,str):
            instance = self._listing_instances.get(listing_id)
            if instance is None:
                method = getattr(
                    self, INSTANCE_METHOD_PREFIX + listing_id, None)
                if callable(method):
                    instance = method()
                    self._listing_instances[listing_id] = instance
                else:
                    instance = self.get_default_listing_instance()
            if instance:
                instance.id = listing_id + '-id'
            return instance
        return None

    def get_listings_instances(self):
        prefix_length = len(INSTANCE_METHOD_PREFIX)
        # find all get_listing_instance_xxx
        for method_name in dir(self.__class__):
            if method_name.startswith(INSTANCE_METHOD_PREFIX):
                method = getattr(self,method_name)
                if callable(method):
                    listing_id = method_name[prefix_length:]
                    if listing_id not in self._listing_instances:
                        instance = method()
                        instance.id = listing_id + '-id' # Ensure id is set according to method name + '-id'
                        self._listing_instances[listing_id] = instance
        self.get_default_listing_instance()  # will update self._listing_instances
        for listing in self._listing_instances.values():
            if listing.is_initialized() and not listing.is_render_initialized():
                listing.render_init(RequestContext(self.request))

        return self._listing_instances

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request'] = self.request  # no need to add request context processor
        context['posted_listing'] = self.listing
        for cls in self.context_classes:
            context[cls.__name__] = cls
        if self.listing_class:
            context[self.listing_class.__name__] = self.listing_class
        context.update(self.get_listings_instances())
        return context

    def add_listing_header_snippet(self, snippet):
        if not hasattr(self.request,'django_listing_header_snippets'):
            self.request.django_listing_header_snippets = []
        self.request.django_listing_header_snippets.append(snippet)

class ListingView(ListingViewMixin, TemplateView):
    pass
