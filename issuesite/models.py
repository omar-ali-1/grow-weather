from __future__ import unicode_literals

from django.db import models

from google.appengine.ext import ndb

from django.template.defaultfilters import slugify

from sourcebasesite.views import *


# find and implement efficient way to implement relationships between entities


class Issue(ndb.Model):
    """Profile -- User profile object"""
    title = ndb.StringProperty(required=True)
    description = ndb.TextProperty()
    author = ndb.TextProperty(repeated=True)
    slug = ndb.ComputedProperty(lambda self: slugify(self.title))


class Claim(ndb.Model):
    """Profile -- User profile object"""
    title = ndb.StringProperty(required=True)
    description = ndb.TextProperty()
    slug = ndb.ComputedProperty(lambda self: slugify(self.title))

class Argument(ndb.Model):
    """function is either "FOR" or "AGAINST" """
    title = ndb.StringProperty(required=True)
    description = ndb.TextProperty()
    function = ndb.StringProperty()

# Relations
#----------
class ClaimArgumentRel(ndb.Model):
    claim = ndb.KeyProperty(kind=Claim,
                                   required=True)
    argument = ndb.KeyProperty(kind=Argument,
                                   required=True)
    relation = ndb.TextProperty(required=True)

class ClaimTagRel(ndb.Model):
    claim = ndb.KeyProperty(kind=Claim,
                                   required=True)
    tag = ndb.KeyProperty(kind=Tag,
                                   required=True)
    relation = ndb.TextProperty(required=True)

class IssueClaimRel(ndb.Model):
    issue = ndb.KeyProperty(kind=Issue,
                                   required=True)
    claim = ndb.KeyProperty(kind=Claim,
                                   required=True)
    relation = ndb.TextProperty()


class IssueArgumentRel(ndb.Model):
    issue = ndb.KeyProperty(kind=Issue,
                                   required=True)
    argument = ndb.KeyProperty(kind=Argument,
                                   required=True)
    relation = ndb.TextProperty(required=True)

class ArgumentSourceRel(ndb.Model):
    argument = ndb.KeyProperty(kind=Argument,
                                   required=True)
    source = ndb.KeyProperty(kind=Source,
                                   required=True)
    relation = ndb.TextProperty(required=True)

class IssueTagRel(ndb.Model):
    issue = ndb.KeyProperty(kind=Issue,
                                   required=True)
    tag = ndb.KeyProperty(kind=Tag,
                                   required=True)
    relation = ndb.TextProperty()

class ArgumentTagRel(ndb.Model):
    argument = ndb.KeyProperty(kind=Argument,
                                   required=True)
    tag = ndb.KeyProperty(kind=Tag,
                                   required=True)
    relation = ndb.TextProperty()

