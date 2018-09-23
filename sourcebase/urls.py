"""sourcebase URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from sourcebasesite.views import *
#from django.views.generic import RedirectView
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# TODO: redirect urls that don't match anything to home (/source/)
# TODO: for new source, or issue, or anything, new should not come after the thing in url. eg /source/new/, because 
# for some reason the matcher does not match to newThing view, but rather to detail view with "new" as the id of requested
# thing. When action="{% url 'issuesite:newIssue' %}" is used, the url looks the same, but routs properly for some reason.
# look into it and see, but change to something like /new/source/ anyway.
urlpatterns = [
    # url(r'^$', RedirectView.as_view(url='/source/')), # change to source/
    url(r'^$', home, name='home'),
    url(r'^tokensignin/', signIn, name='signIn'),
    url(r'^fetchProfile/', fetchProfile, name='fetchProfile'),
    url(r'^users/(?P<userID>[a-zA-Z0-9-_]+)/$', userProfile, name='userProfile'),
    url(r'^verifyOrCreateUser/$', verifyOrCreateUser, name='verifyOrCreateUser'),
    # Serve text file used by scheduling server to verify this server
    url(r'^ATriggerVerify.txt$', ATriggerVerify, name='ATriggerVerify'),
    url(r'^endpoints/updateUser/$', updateUser, name='updateUser'),
    url(r'^endpoints/sendReport/$', sendReport, name='sendReport'),
    url(r'^endpoints/resendReport/$', resendReport, name='resendReport'),
    url(r'^endpoints/prepopulateFields/$', prepopulateFields, name='prepopulateFields'),
    url(r'^endpoints/checkRainAndAlertUsers/$', checkRainAndAlertUsers, name='checkRainAndAlertUsers'),
    url(r'^endpoints/getAlertHistory/$', getAlertHistory, name='getAlertHistory')

    #url(r'^(?P<path>.*)$', 'django.views.static.serve', {
    #    'document_root': BASE_DIR,}),
]

