from __future__ import unicode_literals

from django.db import models

from google.appengine.ext import ndb

from django.template.defaultfilters import slugify




class User(ndb.Model):
    # User Info
    userID = ndb.StringProperty(required=True)
    name = ndb.StringProperty()
    email = ndb.StringProperty()
    phone = ndb.StringProperty()
    zipcode = ndb.StringProperty()
    timezone = ndb.StringProperty()
    geoString = ndb.StringProperty()
    # User Settings
    receive_email = ndb.StringProperty()
    receive_sms = ndb.StringProperty()
    receive_rain = ndb.StringProperty()
    receive_reports = ndb.StringProperty()


class Report(ndb.Model):
    """weather report model"""
    user = ndb.KeyProperty(kind=User)
    datetime = ndb.DateTimeProperty()
    dailyLow = ndb.IntegerProperty()
    dailyHigh = ndb.IntegerProperty()
    precipitation = ndb.IntegerProperty()
    summary = ndb.StringProperty()

class Alert(ndb.Model):
    """weather report model"""
    user = ndb.KeyProperty(kind=User)
    datetime = ndb.DateTimeProperty()
    precipitation = ndb.IntegerProperty()




        

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