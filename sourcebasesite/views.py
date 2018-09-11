from django.shortcuts import render
# from hotelsite.models import Review
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
# import mongoengine
# AppEngine Imports
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

# Our App imports
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import ndb
from models import *
from google.appengine.ext.webapp.util import run_wsgi_app

from django.template.defaultfilters import slugify
from ast import literal_eval
import logging

# request urls and get the response, and be able to manipulate it, etc.
import urllib, urllib2

# json.loads() and json.dumps() loads and dumps a json string, taking it from
# valid json string to python dic object, and vice versa, respectively, with
# dumps() doing the appropriate escaping for us.
import json

# google oauth2 verification

from google.oauth2 import id_token
from google.auth.transport import requests as googlerequests
import requests_toolbelt.adapters.appengine

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()
from issuesite.models import *



from google.appengine.ext import ndb
import google.auth.transport.requests
import google.oauth2.id_token
import requests_toolbelt.adapters.appengine

import datetime
import requests
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()






def home(request):
    return render(request, "sourcebasesite/home.html")


def verifyOrCreateUser(request):
    id_token = request.META['HTTP_AUTHORIZATION'].split(' ').pop()
    #print id_token
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401

    user = User.query(User.userID==claims['sub']).fetch()
    #print claims
    if user:
        return HttpResponse(json.dumps({'status':'success'}))
    else:
        #bio = "Your bio goes here."
        try:
            claims['email']
            #TODO: fix first last name issue here
            user = User(name = claims['name'], userID = claims['sub'], email = claims['email'])
        except:
            user = User(nameame = claims['name'], userID = claims['sub'])
        if 'picture' in claims:
            user.picture = claims['picture']
        user.put()
    return HttpResponse(json.dumps({'status':'success'}))

def userProfile(request, userID):
    user = _getUserObject(userID)
    error = None
    if not user:
        error = "Sorry, this user does not exist!"
    return render(request, "sourcebasesite/user_profile.html", {'user': user, 'error':error})

def _getUserObject(userID):
    user = User.query(User.userID==userID).fetch()
    if user:
        return user[0]
    else:
        return None


def fetchProfile(request):
    
    #print "i am here"
    # print request
    id_token = request.META['HTTP_AUTHORIZATION'].split(' ').pop()
    print id_token
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401

    profile = query_database(claims['sub'], claims)


    return HttpResponse(json.dumps(profile))



def signIn(request):
    # Verify Firebase auth.
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return 'Unauthorized', 401
    else:
        return HttpResponse("Welcome, " + claims['sub'] + "!")



def _getTimeZone(request, zipcode):
    #logging.info("get timezone")
    #logging.info(zipcode)
    if zipcode:
        TimeZoneURL = ('https://www.zipcodeapi.com/rest/P2XWrO6FkXTl2yfjS85Wl4kHJT' +
        'XoyizlPOT1A6IjBWzWeFDWSXv3WMbOWrJ4VMMH/info.json/' + zipcode + '/degrees')
        TZResponse = requests.get(TimeZoneURL).json()
        #logging.info(TZResponse)
        if 'error_msg' in TZResponse or len(zipcode) > len(TZResponse['zip_code']):
            logging.info("length error")
            return False
        else:
            return TZResponse['timezone']['timezone_identifier']
    else:
        return False


def sendReport(request, userID=None, receive_sms=None, receive_email=None):
    """Send a reminder to a phone using Twilio SMS"""
    # Get our appointment from the database


    try:
        user = User.query(User.userID==userID).fetch()
    except e:
        # The appointment we were trying to remind someone about
        # has been deleted, so we don't need to do anything
        return e

    appointment_time = arrow.get(datetime(2018, 9, 11), user.timezone)
    body = 'Hi {0}. You have an appointment coming up at {1}.'.format(
        appointment.name,
        appointment_time.format('h:mm a')
    )

    message = client.messages.create(
        body=body,
        to=user.phone,
        from_=settings.TWILIO_NUMBER,
    )


def _updateReports(post, user):
    try:
        logging.info("we are hereeeee")

        A_TRIGGER_KEY = '5185801497362639880'
        A_TRIGGER_SECRET = 'eni6Ave8FH6473y9se1VM2hHdIQWtp'
        updateReportsTask = False
        userUpdated = False

        receive_reports = post['check-receive-reports'] if 'check-receive-reports' in post else None
        receive_sms = post['check-receive-sms'] if 'check-receive-sms' in post else None
        receive_email = post['check-receive-email'] if 'check-receive-email' in post else None
        

        if receive_sms != user.receive_sms:
            userUpdated = True
            updateReportsTask = True
            user.receive_sms = receive_sms

        if receive_email != user.receive_email:
            userUpdated = True
            updateReportsTask = True
            user.receive_email = receive_email

        # None and change = used to receive reports, not anymore
        # If receive_reports is None, we want to delete task and stop reports, but
        # we don't want to keep sending delete requests every time user updates info with reports checkbox unchecked.
        if user.receive_reports != receive_reports:
            # If user saved settings with receive_reports on, we want to create task regardless of other changes.
            updateReportsTask = True if receive_reports else False
            userUpdated = True
            user.receive_reports = receive_reports
            if not receive_reports:
                deleteURL = ('https://api.atrigger.com/v1/tasks/delete?key=' + 
                A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_userID=' + 
                user.userID + '&tag_type=reports')
                delete_response = requests.post(deleteURL)
                logging.info("delete_response")

        
        if updateReportsTask and receive_reports:
            deleteURL = ('https://api.atrigger.com/v1/tasks/delete?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_userID=' + 
            user.userID + '&tag_type=reports')
            delete_response = requests.post(deleteURL)
            logging.info("delete_response")

            triggerurl = ('https://api.atrigger.com/v1/tasks/create?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
            '&timeSlice=1minute&count=-1&url=https%3A%2F%2Fgrow-weather.appspot.com/' + 
            'endpoints/sendReport?query=receive_email=' + (receive_email or 'None') + 
            '%26receive_sms=' + (receive_sms or 'None') + '%26userID=' +
            (user.userID or 'None') + '&tag_userID=' + user.userID + '&tag_type=reports')
            r = requests.post(triggerurl)
            logging.info(receive_reports)
        return userUpdated

    except Exception as e:
        logging.info(e)


def updateUserSettings(request):
    try:
        logging.info("======== We are here in updateUserSettings================")
        id_token = request.META['HTTP_AUTHORIZATION'].split(' ').pop()
        claims = google.oauth2.id_token.verify_firebase_token(
            id_token, HTTP_REQUEST)
        if not claims:
            return 'Unauthorized', 401
        # logging.info(claims)
        # user = User.query(User.userID==claims['sub']).fetch()
        
        name = claims['name']
        email = claims['email']
        post = request.POST
        user = _getUserObject(claims['sub'])
        userUpdated = _updateReports(post, user)

        zipcode = post['input-zip'] if 'input-zip' in post else None
        timezone = _getTimeZone(request, zipcode)
        logging.info(timezone)
        #triggerurl = 'https://api.atrigger.com/v1/tasks/create?key=5185801497362639880&secret=eni6Ave8FH6473y9se1VM2hHdIQWtp&timeSlice=1day&count=-1&url=http%3A%2F%2Fgrow-weather.appspot.com/%2FmyTask%3Fquery%3Dsample&tag_type=testing'
        
        
        user.timezone = timezone
        if not timezone:
            return HttpResponse(json.dumps({'err': 'Invalid Zip Code.'}))
        phone = post['input-phone'] if 'input-phone' in post else None


        receive_rain = post['check-receive-rain'] if 'check-receive-rain' in post else None
        #logging.info(requests.get)

        
        user.name = name
        user.email = email
        user.zipcode = zipcode
        user.phone = phone

        user.put()

        '''if receive_reports == 'on':
            report_time = datetime.time(0,0,0)
            logging.info('here')
            logging.info(report_time)'''
        #usertimeOffset = userZip.timezone
        #user.send_time = datetime.time((8-userTimeOffset)%24)
        
        return HttpResponse(json.dumps({'status':'success'}))
        
    except Exception as e:
        logging.info(e)


def prepopulateFields(request):
    '''
    
'''
    try:
        logging.info("======== We are here in updateUserSettings================")
        id_token = request.META['HTTP_AUTHORIZATION'].split(' ').pop()
        claims = google.oauth2.id_token.verify_firebase_token(
            id_token, HTTP_REQUEST)
        if not claims:
            return 'Unauthorized', 401
        # logging.info(claims)
        # user = User.query(User.userID==claims['sub']).fetch()
        
        name = claims['name']
        email = claims['email']

        user = _getUserObject(claims['sub'])
        logging.info(user)
        return HttpResponse(json.dumps({'receive_reports': user.receive_reports, \
            'receive_rain': user.receive_rain, 'receive_email': user.receive_email, \
            'receive_sms': user.receive_sms, 'phone': user.phone, 'zipcode': user.zipcode}))
        
    except Exception as e:
        logging.info(e)

# TODO check security of serving file this way, and with static server in production
def ATriggerVerify(request):
    ATriggerFilePath = BASE_DIR + '/static/sourcebasesite/ATriggerVerify.txt'
    logging.info(ATriggerFilePath)
    txtfile = open(ATriggerFilePath, 'r')
    logging.info(txtfile)
    #response = HttpResponse(txtfile)
    response = HttpResponse(content=txtfile)
    response['Content-Type'] = 'text/javascript'
    #response['Content-Disposition'] = 'attachment; filename=ATriggerVerify.txt'
    logging.info(response)
    return response
