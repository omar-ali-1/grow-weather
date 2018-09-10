from sourcebasesite.views import *
from django.conf.urls import url
from views import *

# app_name = 'sourcebasesite'
# TODO: redirect urls that don't match anything to home (/source/)
urlpatterns = [
    url(r'^$', source, name='source'),
    url(r'^(?P<sourceID>[a-zA-Z0-9-_]+)/$', sourceDetail, name='sourceDetail'),
    url(r'^(?P<sourceID>[a-zA-Z0-9-_]+)/edit/$', editSource, name='editSource'),
    url(r'^(?P<sourceID>[a-zA-Z0-9-_]+)/save/$', saveSource, name='saveSource'),
    url(r'^/new/$', newSource, name='newSource')
    #url(r'^source/', source, name='source')
]

#r'^(?P<sourceKey>\d+)/$'