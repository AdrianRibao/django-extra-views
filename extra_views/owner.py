# -*- coding: utf-8 -*-
from django.views.generic.base import TemplateResponseMixin, View
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory, inlineformset_factory
from django.views.generic.detail import SingleObjectMixin, SingleObjectTemplateResponseMixin
from django.views.generic.list import MultipleObjectMixin, MultipleObjectTemplateResponseMixin
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.edit import ModelFormMixin, ProcessFormView
import logging

logger = logging.getLogger(__name__)

class OwnerMixin(SingleObjectTemplateResponseMixin):
    parent_pk_url_kwarg = 'parent_pk'

    def get_lookup(self):
        """
        Returns the name of the field that contains the user who owns the object.
        """
        return self.lookup

    def _get_parent_model(self, parent_model_name):

        # If is updating, the paret_object should be an instance
        # otherwise it shoud me a model
        if not self.object:
            parent_model = getattr(self.model, parent_model_name, None)
            is_instance = False
        else:
            parent_model = getattr(self.object, parent_model_name, None)
            is_instance = True

        print "The parent model is:"
        print parent_model

        if not parent_model:
            raise LookupError('The model has not the field: %s' % (parent_model_name,))

        if is_instance:
            return parent_model
        else:
            return parent_model.field.rel.to

    def _get_owner_model(self, lookup_array):
        owner_model = self.model
        for path in lookup_array:
            owner_model = getattr(owner_model, path, None)
            if not owner_model:
                raise LookupError('The model has not the field: %s' % (path,))
            owner_model = owner_model.field.rel.to

        #print owner_model
        #import pdb
        #pdb.set_trace()
        return owner_model


    def parse_lookup(self):
        lookup = self.get_lookup()
        lookup_array = lookup.split('.')

        # The name of the field
        self.field = lookup_array.pop()

        # The parent model
        parent_model_name = lookup_array[0]
        self.parent_model_name = parent_model_name
        self.parent_model = self._get_parent_model(parent_model_name)

        # The name of the owner model
        self.owner_model = self._get_owner_model(lookup_array)

        return None

    def _get_user_owner(self):
        self.parse_lookup()
        #self._get_parent_object()
        print "Parent model"
        print self.parent_model
        print "the field is"
        print self.field
        user = getattr(self.parent_model, self.field, None)
        return user

    def check_owner(self):
        user = self._get_user_owner()
        print "The owner is:"
        print user
        print "you are:"
        print self.request.user
        if user == self.request.user:
            return True
        return False

class OwnerModelFormMixin(ModelFormMixin, OwnerMixin):
    parent_queryset = None

    def form_valid(self, form):
        self.object = form.save(commit=False)
        setattr(self.object, self.parent_model_name, self.parent_object)
        self.object.save()
        return super(OwnerModelFormMixin, self).form_valid(form)


class BaseOwnerView(OwnerModelFormMixin, View):
    """
    A base view for displaying a modelformset for a queryset belonging to a parent model.
    Checks the owner of the object before procesing anything.
    """

    def not_owner_actions(self):
        """
        Actions to be taken when the user attempts to access another user object.
        Must return a HttpResponse Object.
        """
        logger.warning(u'SECURITY WARNING: The user %s has attempted to access the CV with ID: %s' % (self.request.user.username, self.parent_model.id))
        return HttpResponseForbidden(u'You are not allowed to see other users CVs. This action will be reported.')

    def get(self, request, *args, **kwargs):
        is_the_owner = self.check_owner()
        if not is_the_owner:
            return self.not_owner_actions()
        return super(BaseOwnerView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        is_the_owner = self.check_owner()
        if not is_the_owner:
            return self.not_owner_actions()
        return super(BaseOwnerView, self).post(request, *args, **kwargs)    

class BaseOwnerCreateView(BaseOwnerView, OwnerModelFormMixin, ProcessFormView):
    def get(self, request, *args, **kwargs):
        self.object = None
        return super(BaseOwnerCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        return super(BaseOwnerCreateView, self).post(request, *args, **kwargs)

class CreateOwnerView(BaseOwnerCreateView):
    template_name_suffix = '_form'


class BaseOwnerUpdateView(BaseOwnerView, OwnerModelFormMixin, ProcessFormView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(BaseOwnerUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(BaseOwnerUpdateView, self).post(request, *args, **kwargs)

class UpdateOwnerView(BaseOwnerUpdateView):
    template_name_suffix = '_form'
