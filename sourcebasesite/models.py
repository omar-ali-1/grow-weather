from __future__ import unicode_literals

from django.db import models

from google.appengine.ext import ndb

from django.template.defaultfilters import slugify


class Report(ndb.Model):
    """weather report model"""
    temperature = ndb.IntegerProperty(repeated=True)
    rain = ndb.BooleanProperty()

class User(ndb.Model):
    # User Info
    userID = ndb.StringProperty(required=True)
    name = ndb.StringProperty()
    email = ndb.StringProperty()
    phone = ndb.StringProperty()
    zipcode = ndb.StringProperty()
    timezone = ndb.StringProperty()
    # User Settings
    receive_email = ndb.StringProperty()
    receive_sms = ndb.StringProperty()
    receive_rain = ndb.StringProperty()
    receive_reports = ndb.StringProperty()
    send_time = ndb.TimeProperty()
    # User History
    reports = ndb.KeyProperty(kind=Report, repeated=True)







        

class Source(ndb.Model):
    """Profile -- User profile object"""
    title = ndb.StringProperty(required=True)
    description = ndb.TextProperty()
    author = ndb.TextProperty(repeated=True)
    slug = ndb.ComputedProperty(lambda self: slugify(self.title))
    #id = ndb.ComputedProperty(lambda self: self.slug)
# Create your models here.
class Tag(ndb.Model):
    """Profile -- User profile object"""
    title = ndb.StringProperty(required=True)
    description = ndb.StringProperty()
    slug = ndb.ComputedProperty(lambda self: slugify(self.title))

class SourceTagRel(ndb.Model):
    source = ndb.KeyProperty(kind=Source,
                                   required=True)
    tag = ndb.KeyProperty(kind=Tag,
                                   required=True)
    relation = ndb.TextProperty()