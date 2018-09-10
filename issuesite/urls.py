from issuesite.views import *
from django.conf.urls import url
from views import *

app_name = 'issuesite'
# TODO: redirect urls that don't match anything to home (/source/)
urlpatterns = [
    url(r'^$', issue, name='issue'),
    url(r'^new/$', newIssue, name='newIssue'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/$', issueDetail, name='issueDetail'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/edit/$', editIssue, name='editIssue'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/save/$', saveIssue, name='saveIssue'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/claim/(?P<claimID>[a-zA-Z0-9-_]+)/$', claimDetail, name='claimDetail'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/new/claim/$', newClaim, name='newClaim'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/claim/(?P<claimID>[a-zA-Z0-9-_]+)/edit/$', editClaim, name='editClaim'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/claim/(?P<claimID>[a-zA-Z0-9-_]+)/save/$', saveClaim, name='saveClaim'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/claim/(?P<claimID>[a-zA-Z0-9-_]+)/argument/(?P<argumentID>[a-zA-Z0-9-_]+)/$', argumentDetail, name='argumentDetail'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/claim/(?P<claimID>[a-zA-Z0-9-_]+)/new/argument/$', newArgument, name='newArgument'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/claim/(?P<claimID>[a-zA-Z0-9-_]+)/argument/(?P<argumentID>[a-zA-Z0-9-_]+)/edit/$', editArgument, name='editArgument'),
    url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/claim/(?P<claimID>[a-zA-Z0-9-_]+)/argument/(?P<argumentID>[a-zA-Z0-9-_]+)/save/$', saveArgument, name='saveArgument'),
    #url(r'^(?P<issueID>[a-zA-Z0-9-_]+)/claim/(?P<claimID>[a-zA-Z0-9-_]+)/save/$', saveClaim, name='saveClaim'),
    #
    #url(r'^(?P<sourceID>[a-zA-Z0-9-_]+)/$', detail, name='detail'),
    #url(r'^(?P<sourceID>[a-zA-Z0-9-_]+)/edit/$', editSource, name='editSource'),
    #url(r'^(?P<sourceID>[a-zA-Z0-9-_]+)/save/$', saveSource, name='saveSource'),
    #url(r'^/new/$', newSource, name='newSource')
    #url(r'^source/', source, name='source')
]

#r'^(?P<sourceKey>\d+)/$'