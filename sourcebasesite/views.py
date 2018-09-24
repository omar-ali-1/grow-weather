
# -*- coding: utf-8 -*-

# Django imports
from django.shortcuts import render
# from hotelsite.models import Review
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse


from google.oauth2 import id_token
from google.auth.transport import requests as googlerequests
import requests_toolbelt.adapters.appengine

from google.appengine.api import users, mail
from google.appengine.ext import webapp
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from models import *
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import ndb
import google.auth.transport.requests
import google.oauth2.id_token
import requests_toolbelt.adapters.appengine
# json.loads() and json.dumps() loads and dumps a json string, taking it from
# valid json string to python dic object, and vice versa, respectively, with
# dumps() doing the appropriate escaping for us.
import json

from ast import literal_eval
import logging

# request urls and get the response, and be able to manipulate it, etc.
import urllib, urllib2

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()


import datetime
import pytz
import re
import requests
#from celery import shared_task
from django.conf import settings
from twilio.rest import Client


from django.views.decorators.csrf import csrf_exempt


from models import *

import sys, os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()

# Templates

def home(request):
    return render(request, "sourcebasesite/home.html")


# User Verification

def _getClaims(request):
    try:
        id_token = request.META['HTTP_AUTHORIZATION'].split(' ').pop()
        return google.oauth2.id_token.verify_firebase_token(
            id_token, HTTP_REQUEST)
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return None


def verifyOrCreateUser(request):
    claims = _getClaims(request)
    if not claims:
        return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)
    userKey = ndb.Key(User, claims['sub'])
    user = userKey.get()
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
        user.key = userKey
        user.put()
    return HttpResponse(json.dumps({'status':'success'}))


# Google Maps 

def _getGeoString(zipcode):
    try:
        # Google Maps API reverse geolocation using zipcode
        GOOGLE_MAPS_KEY = Settings.get('GOOGLE_MAPS_KEY')
        getGeoLocURL = ('https://maps.googleapis.com/maps/api/geocode/' + 
            'json?key=' + GOOGLE_MAPS_KEY + '&address=' + zipcode)
        geoResponse = requests.get(getGeoLocURL)
        location = geoResponse.json()['results'][0]['geometry']['location']
        return str(location['lat']) + ',' + str(location['lng'])

    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


# Rain Alerts

# TODO later: implement pagination for when alert number becomes high
# csrf exempt to allow GCP Queues to work
@csrf_exempt
def _alertUser(userKey):
    ## lookup by key is strongly consistent
    user = userKey.get()
    # double check that user still wants to receive alert at time of task execution
    if user.receive_rain:
        precipProbability = _getPrecipProb(user.geoString)
        #logging.info(user.name + ':')
        #logging.info(precipProbability)
        if precipProbability >= 30:
            nowUTCDatetime = datetime.datetime.utcnow()
            alert = Alert(user=userKey, datetime=nowUTCDatetime, precipitation=precipProbability)
            alert.put()
            alertBody = u'\nHey {}!\n\nIn about an hour, the chance of rain will be {}%.'.format(user.name, alert.precipitation)
            _sendMessage(userKey, alertBody, rainAlert=True)

# csrf exempt to allow cross-origin trigger request in
@csrf_exempt
def checkRainAndAlertUsers(request):
    try:
        #deferred.defer(_enqueueCheckRainTasks)

        
        userKeysQuery = User.query(User.receive_rain=='on')
        #logging.info('we are here in check rain')
        #logging.info(userKeys)

        ## keys_only makes this a strongly consistent query as long as index is updated, since 
        ## only keys are fetced. Iterator is used on query to allow handling large # of users.
        for userKey in userKeysQuery.iter(keys_only=True):
            deferred.defer(_alertUser, userKey, _queue='alerts-queue')
            

        return HttpResponse(json.dumps({'status':'success'}))
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


def _getPrecipProb(geoString):
    try:

        # Dark Weather API daily forecast
        DARK_SKY_KEY = Settings.get('DARK_SKY_KEY')

        excludeList = 'currently,minutely,daily,alerts,flags'
        getForecastURL = ('https://api.darksky.net/forecast/' + DARK_SKY_KEY + '/' + 
        geoString + '?exclude=' + excludeList)
        forecastResponse = requests.get(getForecastURL)
        hourlyForecast = forecastResponse.json()['hourly']
        rainProb = int(round(hourlyForecast['data'][1]['precipProbability'] * 100))
        return rainProb
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


def getAlertHistory(request):
    try:
        claims = _getClaims(request)
        if not claims:
            return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)
        # claims['sub'] is the user ID string
        userKey = ndb.Key(User, claims['sub'])
        alerts = Alert.query(Alert.user==userKey).order(-Alert.datetime).fetch()
        #logging.info(alerts)
        alertsList = []
        for alert in alerts:
            #logging.info("Alert: ===========")
            #logging.info(alert)
            alertDict = {}
            alertDict['precipProbability'] = alert.precipitation
            alertDict['datetime'] = alert.datetime.isoformat()
            alertsList.append(alertDict)
        alertsDict = {}
        alertsDict['alerts'] = alertsList
        alerts = json.dumps(alertsDict)
        return HttpResponse(alerts)

    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)



############# Weather Reports

def _getWeather(geoString):
    try:

        # Dark Weather API daily forecast
        DARK_SKY_KEY = Settings.get('DARK_SKY_KEY')
        excludeList = 'currently,minutely,alerts,flags'
        getForecastURL = ('https://api.darksky.net/forecast/' + DARK_SKY_KEY + '/' + 
        geoString + '?exclude=' + excludeList)
        forecastResponse = requests.get(getForecastURL)
        #logging.info(forecastResponse.json())
        hourlyForecast = forecastResponse.json()['hourly']
        dailyForecast = forecastResponse.json()['daily']
        dailySummary = hourlyForecast['summary']
        dailyRainProb = int(round(dailyForecast['data'][0]['precipProbability'] * 100))
        dailyLow = int(round(dailyForecast['data'][0]['temperatureLow']))
        dailyHigh = int(round(dailyForecast['data'][0]['temperatureHigh']))
        return [dailySummary, dailyLow, dailyHigh, dailyRainProb]
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

@csrf_exempt
def _sendMessage(userKey, body, rainAlert=False):
    try:
        error = ''
        user = userKey.get()
        if user.receive_sms:
            # Twilio info
            try:
                authToken = Settings.get('TWILIO_AUTH_TOKEN')
                accountSID = Settings.get('TWILIO_ACCOUNT_SID')
                twilioNumber = Settings.get('TWILIO_ACCT_PHONE_NUMBER')
                #twilioNumber = '+15005550006'


                client = Client(accountSID, authToken)
                message = client.messages.create(
                    body=body,
                    # to='+1 615-592-5253',
                    to= '+1' + user.phone,
                    from_=twilioNumber,
                )
            except e:
                error = "Sorry! We were not able to send you SMS at this time!"

        if user.receive_email:
            if rainAlert:
                subject = 'Rain Alert'
            else:
                subject = 'Your daily weather report from Grow'

            senderAddress = 'omar.ali11231@gmail.com'
            recepientAddress = user.email
            mail.send_mail(sender=senderAddress,
                           to=recepientAddress,
                           subject=subject,
                           body=body + '\n\n' + error
                           )
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


def _getTimeZone(request, zipcode):
    #logging.info("get timezone")
    #logging.info(zipcode)
    TimeZoneURL = ('https://www.zipcodeapi.com/rest/P2XWrO6FkXTl2yfjS85Wl4kHJT' +
    'XoyizlPOT1A6IjBWzWeFDWSXv3WMbOWrJ4VMMH/info.json/' + zipcode + '/degrees')
    TZResponse = requests.get(TimeZoneURL).json()
    #logging.info(TZResponse)
    # TODO handle error better
    if 'error_msg' in TZResponse:
        logging.info(TZResponse['error_msg'])
        return 'err', TZResponse['error_msg']
    # The timezone API simply ignores any chars beyond the 5th in zipcode, doesnt return err.
    elif 'timezone' in TZResponse:
        logging.info("#############TZResponse")
        return '', TZResponse['timezone']['timezone_identifier']
    else:
        return 'err', 'Unknown error! Sorry!'


def _getReportDatetime(timezone):
    try:
        # Tricky stuff! Be careful!
        nowUTCDatetime = pytz.utc.localize(datetime.datetime.utcnow(), is_dst=True)
        userTimezoneObj = pytz.timezone(timezone)
        nowUserDatetime = nowUTCDatetime.astimezone(userTimezoneObj)

        possibleReportDatetime = nowUserDatetime.replace(hour=8, minute=0, second=0, microsecond=0)
        # Report signup time should be at least 10s before report time to allow for proper task processing
        if possibleReportDatetime - nowUserDatetime >= datetime.timedelta(seconds=10):
            reportDatetime = possibleReportDatetime
            # logging.info("3#############3 ITS TRUEEEEEEEE")
        else:
            reportDatetime = possibleReportDatetime + datetime.timedelta(days=1)
        # logging.info(reportDatetime.isoformat())
        return reportDatetime.isoformat()

    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

# deferred
@csrf_exempt
def _updateATriggerTask(userKey):
    '''
    Deferred task which updates the the scheduled task in A Trigger
    which sends weather reports to user at 8 am.
    '''
    try:

        A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
        A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')
        #user = User.query(User.key==userKey).fetch(projection=[User.receive_reports, User.timezone])[0]
        user = userKey.get()
        #logging.info("++++++++++++ Update A Trgigger +++++++++++")
        #logging.info(user)
        #logging.info(user.receive_reports)

        if user.receive_reports and not user.task_exists:

            reportDatetime = _getReportDatetime(user.timezone)
            domain = 'https%3A%2F%2Fgrow-weather.appspot.com'
            #domain = 'https%3A%2F%2Ffc2116ab.ngrok.io'

            addURL = ('https://api.atrigger.com/v1/tasks/create?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
            '&timeSlice=1day&count=-1&url=' + domain + 
            '/endpoints/sendReport/' + 
            '&tag_ID=' + userKey.id() + '&tag_type=reports&first=' + reportDatetime + '&post=True')
            
            #logging.info(triggerurl)
            A_TRIGGER_PAYLOAD_SECRET = Settings.get('A_TRIGGER_PAYLOAD_SECRET')
            data = {'userID': userKey.id() or 'None', 'A_TRIGGER_PAYLOAD_SECRET': A_TRIGGER_PAYLOAD_SECRET}
            #r = requests.post(addURL, data={'userID': user.userID or 'None'}, verify=True)
            addTaskResponse = requests.post(addURL, data=data, verify=True)
            user.task_exists = True
            user.put()
        else:
            deleteURL = ('https://api.atrigger.com/v1/tasks/delete?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_ID=' + 
            userKey.id() + '&tag_type=reports')
            deleteTaskResponse = requests.post(deleteURL, verify=True)
            user.task_exists = False
            user.put()
        #logging.info("####################### here in updateatrigger")
        #logging.info(addTaskResponse.json())
        return HttpResponse()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)



@csrf_exempt 
def sendReport(request):
    """Send a reminder to a phone using Twilio SMS"""
    # Get our appointment from the database
    try:
        '''
        A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
        A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')

        validateRequestIpURL = ('https://api.atrigger.com/v1/ipverify?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&ip=127.0.0.1'
        '''

        req = request.REQUEST
        # logging.info('########## Request Data:')
        # logging.info(request)

        # Additional security check to make sure task was created by this app. Payload is SSL-secured.
        if Settings.get('A_TRIGGER_PAYLOAD_SECRET') != request.POST['A_TRIGGER_PAYLOAD_SECRET']:
            return HttpResponse(error, status=401)

        userID = request.POST['userID']
        userKey = ndb.Key(User, userID)
        user = userKey.get()
        dailySummary, dailyLow, dailyHigh, dailyRainProb = _getWeather(user.geoString)
        #logging.info('======== Weather Data:')
        #logging.info(_getWeather(user.zipcode))
        #logging.info("======== We are here in sendReport===============")
        
        nowUTCDatetime = datetime.datetime.utcnow()

        report = Report(user=userKey, datetime=nowUTCDatetime, dailyLow=dailyLow, dailyHigh=dailyHigh, summary=dailySummary, precipitation=dailyRainProb)
        report.put()

        reportBody = u'\nHey {}!\n\nHere is your forecast for today:\n\n{}\n\nDaily Low: {}\N{DEGREE SIGN}F\nDaily High: {}\N{DEGREE SIGN}F\nChance of rain: {}%'.format(user.name, report.summary, report.dailyLow, report.dailyHigh, report.precipitation)
        #logging.info(reportBody)
        userKey = ndb.Key(User, userID)
        deferred.defer(_sendMessage, userKey, reportBody, _queue='reports-queue')

        '''if receive_reports == 'on':
            report_time = datetime.time(0,0,0)
            logging.info('here')
            logging.info(report_time)'''
        #usertimeOffset = userZip.timezone
        #user.send_time = datetime.time((8-userTimeOffset)%24)
        
        return HttpResponse(json.dumps({'status':'success'}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)



def resendReport(request):
    try:
        claims = _getClaims(request)
        userKey = ndb.Key(User, claims['sub'])
        user = userKey.get()
        report = Report.query(Report.user==userKey).order(-Report.datetime).get()
        if report:
            reportBody = u'\nHey {}!\n\nHere is your forecast for today:\n\n{}\n\nDaily Low: {}\N{DEGREE SIGN}F\nDaily High: {}\N{DEGREE SIGN}F\nChance of rain: {}%'.format(user.name, report.summary, report.dailyLow, report.dailyHigh, report.precipitation)
            deferred.defer(_sendMessage, userKey, reportBody, _queue='reports-queue')
            return HttpResponse(json.dumps({'status':'success'}))
        else:
            return HttpResponse(json.dumps({'err':'You don\'t have any reports yet!'}))
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)




########### Update User



def _updateUserProperties(user, post, claims, timezone):
    try:
        #logging.info("we are hereeeee")

        userUpdated = False

        name = claims['name']
        email = claims['email']
        phone = post['input-phone'] if 'input-phone' in post else None

        receive_reports = post['check-receive-reports'] if 'check-receive-reports' in post else None
        receive_sms = post['check-receive-sms'] if 'check-receive-sms' in post else None
        receive_email = post['check-receive-email'] if 'check-receive-email' in post else None
        receive_rain = post['check-receive-rain'] if 'check-receive-rain' in post else None

        zipcode = post['input-zip'] if 'input-zip' in post else None
        # Get geoString and save to user to save google API calls converting zipcode 
        # to geoStr every time we fetch weather
        geoString = user.geoString
        if user.zipcode != zipcode or not zipcode:
            geoString = _getGeoString(zipcode)

        # Was user updated? zipcode change implies geostring and timezone changes
        userUpdated = user.name != name or user.email != email or user.phone != phone or \
        user.receive_reports != receive_reports or user.receive_sms != receive_sms or \
        user.receive_email != receive_email or user.receive_rain != receive_rain or user.zipcode != zipcode

        user.name = name
        user.email = email
        user.phone = phone
        user.receive_reports = receive_reports
        user.receive_sms = receive_sms
        user.receive_email = receive_email
        user.receive_rain = receive_rain
        user.zipcode = zipcode
        #logging.info('aaaaaaaaa timezone aaaaaaaa')
        #logging.info(timezone)
        user.timezone = timezone
        user.geoString = geoString


            #logging.info(r.json())
        return userUpdated

    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        # logging.info(e, exc_tb.tb_lineno)


def _isValidPhoneNumber(phone):
    try:
        authToken = 'ace161d8b47b77ad5a729b10c02633f0'
        accountSID = 'AC437de0c4319e3101f8a41972a7ed10fa'
        client = Client(accountSID, authToken)
        number = client.lookups.phone_numbers('+1' + phone).fetch()
        return True
    except:
        return False


def updateUser(request):
    try:
        userUpdated = False
        #### User authentication and fetching ###
        #logging.info("======== We are here in updateUserSettings================")
        claims = _getClaims(request)
        if not claims:
            error = 'Sorry! You did not provide the credentials necessary to access this resource.'
            return HttpResponse(error, status=401)
        userKey = ndb.Key(User, claims['sub'])
        user = userKey.get()

        #### Request processing ###
        post = request.POST

        # Validate zipcode input and update corresponding user property
        zipcode = post['input-zip'] if 'input-zip' in post else None
        timezone = user.timezone
        if user.zipcode != zipcode or not zipcode:
            if not re.match(r"^[0-9]{5}(?:-[0-9]{4})?$", zipcode):
                return HttpResponse(json.dumps({'err': "Invalid zipcode."}))

        # Fetch timezone info for the zipcode if zipcode has changed, and update corresp. user property
            timezoneTuple = _getTimeZone(request, zipcode) if zipcode != user.zipcode else ('', user.timezone)
            #logging.info(timezone)
            if timezoneTuple[0] == "err":
                return HttpResponse(json.dumps({'err': timezoneTuple[1]}))
            else:
                timezone = timezoneTuple[1]

        # Validate phone input via Twilio API and update corresponding user property
        phone = post['input-phone'] if 'input-phone' in post else None
        if not phone:
            return HttpResponse(json.dumps({'err': "Invalid US phone number. Valid Format: 1234567891"}))
        elif user.phone != phone:
            if not _isValidPhoneNumber(phone):
                return HttpResponse(json.dumps({'err': "Invalid US phone number. Valid Format: 1234567891"}))
        receive_reports = post['check-receive-reports'] if 'check-receive-reports' in post else None
        updateReports = False

        if user.receive_reports != receive_reports:

            updateReports = True
        
        # Update user's basic info
        userUpdated = _updateUserProperties(user, post, claims, timezone)
        # Update user's report settings, and scheduled task via A Trigger Scheduling API
        

        if userUpdated:
            user.put()
            if updateReports:
                # Enqueue task which updates trigger in ATrigger database. We can use 
                # defer/queueing without timing issues because task addition/deletion 
                # depends on user property
                deferred.defer(_updateATriggerTask, userKey, _queue='ATrigger-queue')
            
            #logging.info(requests.get)

        
        return HttpResponse(json.dumps({'status':'success'}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(json.dumps({'err': exc_type + fname + exc_tb.tb_lineno}))


def prepopulateFields(request):
    '''
    
'''
    try:
        #logging.info("======== We are here in updateUserSettings================")
        claims = _getClaims(request)
        if not claims:
            return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)
        # logging.info(claims)
        # user = User.query(User.userID==claims['sub']).fetch()
        
        name = claims['name']
        email = claims['email']

        user = ndb.Key(User, claims['sub']).get()
        #logging.info(user)
        return HttpResponse(json.dumps({'receive_reports': user.receive_reports, \
            'receive_rain': user.receive_rain, 'receive_email': user.receive_email, \
            'receive_sms': user.receive_sms, 'phone': user.phone, 'zipcode': user.zipcode}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return HttpResponse(json.dumps({'err': 'User does not exist (yet).'}))


# Daylight savings update

def _updateUserReportTime(userKey):
        A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
        A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')
        #user = User.query(User.key==userKey).fetch(projection=[User.receive_reports, User.timezone])[0]
        user = userKey.get()
        #logging.info("++++++++++++ Update A Trgigger +++++++++++")
        #logging.info(user)
        #logging.info(user.receive_reports)
        if user.receive_reports:
            eastern = timezone('US/Eastern')
            # allow 2 hours extra after daylight time switch (4 am instead of 2 am)
            DSTStartOrEndDateTime = eastern.localize(datetime.datetime(2018, 3, 11, 4), is_dst=True)
            # DSTStartOrEndDateTime = eastern.localize(datetime.datetime(2018, 11, 4, 4), is_dst=True)

            
            # logging.info(reportDatetime.isofor

            domain = 'https%3A%2F%2Fgrow-weather.appspot.com'
            #domain = 'https%3A%2F%2Ffc2116ab.ngrok.io'

            addURL = ('https://api.atrigger.com/v1/tasks/create?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
            '&timeSlice=1day&count=-1&url=' + domain + 
            '/endpoints/sendReport/' + '&tag_type=DST&first=' + DSTStartOrEndDateTime + '&post=True')
            
            #logging.info(triggerurl)
            A_TRIGGER_PAYLOAD_SECRET = Settings.get('A_TRIGGER_PAYLOAD_SECRET')
            data = {'userID': userKey.id() or 'None', 'A_TRIGGER_PAYLOAD_SECRET': A_TRIGGER_PAYLOAD_SECRET}
            #r = requests.post(addURL, data={'userID': user.userID or 'None'}, verify=True)
            addDSTTaskResponse = requests.post(addURL, data=data, verify=True)
            
        return HttpResponse()


def _updateUserReportTimeDST(userKey):
        A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
        A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')
        #user = User.query(User.key==userKey).fetch(projection=[User.receive_reports, User.timezone])[0]
        user = userKey.get()
        #logging.info("++++++++++++ Update A Trgigger +++++++++++")
        #logging.info(user)
        #logging.info(user.receive_reports)

        # task_exists ensures that not only is user signed up to get reports, but that the task exists in
        # A Trigger in order to avoid duplicate tasks. Otherwise, user is not signed up or task is queued
        # for creation
        if user.receive_reports and user.task_exists:
            # allow 2 hours extra after daylight time switch (4 am instead of 2 am)
            reportDatetime = _getReportDatetime(user.timezone)
            domain = 'https%3A%2F%2Fgrow-weather.appspot.com'
            #domain = 'https%3A%2F%2Ffc2116ab.ngrok.io'

            addURL = ('https://api.atrigger.com/v1/tasks/create?key=' + 
                A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
                '&timeSlice=1day&count=-1&url=' + domain + 
                '/endpoints/sendReport/' + 
                '&tag_ID=' + userKey.id() + '&tag_type=reports&first=' + '2018-09-14T12:46:47.260683-10:00' + '&post=True')

            A_TRIGGER_PAYLOAD_SECRET = Settings.get('A_TRIGGER_PAYLOAD_SECRET')
            data = {'userID': userKey.id() or 'None', 'A_TRIGGER_PAYLOAD_SECRET': A_TRIGGER_PAYLOAD_SECRET}
            #r = requests.post(addURL, data={'userID': user.userID or 'None'}, verify=True)
            
            addTaskResponse = requests.post(addURL, data=data, verify=True)

        return HttpResponse()

@csrf_exempt
def updateDaylightSavings(request):
    try:

        req = request.REQUEST
        # logging.info('########## Request Data:')
        # logging.info(request)

        # Additional security check to make sure task was created by this app. Payload is SSL-secured.
        #if Settings.get('A_TRIGGER_PAYLOAD_SECRET') != request.POST['A_TRIGGER_PAYLOAD_SECRET']:
        #    return HttpResponse(error, status=401)

        A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
        A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')

        deleteURL = ('https://api.atrigger.com/v1/tasks/delete?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_type=reports')
        
        deleteTaskResponse = requests.post(deleteURL, verify=True)

        # task_exists ensures that not only is user signed up to get reports, but that the task exists in
        # A Trigger in order to avoid duplicate tasks. Otherwise, user is not signed up or task is queued
        # for creation
        userKeysQuery = User.query(User.receive_rain=='on', User.task_exists==True)
        logging.info(userKeysQuery.fetch())
        for userKey in userKeysQuery.iter(keys_only=True):
            deferred.defer(_updateUserReportTimeDST, userKey, _queue='DST-queue')

        '''if receive_reports == 'on':
            report_time = datetime.time(0,0,0)
            logging.info('here')
            logging.info(report_time)'''
        #usertimeOffset = userZip.timezone
        #user.send_time = datetime.time((8-userTimeOffset)%24)
        
        return HttpResponse(json.dumps({'status':'success'}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)




# A Trigger Verification

# TODO check security of serving file this way, and with static server in production
def ATriggerVerify(request):
    ATriggerFilePath = BASE_DIR + '/static/sourcebasesite/ATriggerVerify.txt'
    #logging.info(ATriggerFilePath)
    txtfile = open(ATriggerFilePath, 'r')
    #logging.info(txtfile)
    #response = HttpResponse(txtfile)
    response = HttpResponse(content=txtfile)
    response['Content-Type'] = 'text/javascript'
    #response['Content-Disposition'] = 'attachment; filename=ATriggerVerify.txt'
    #logging.info(response)
    return response






'''
def createDSTUpdateTask(request):
    A_TRIGGER_KEY = Settings.get('A_TRIGGER_KEY')
    A_TRIGGER_SECRET = Settings.get('A_TRIGGER_SECRET')
    eastern = pytz.timezone('US/Eastern')
    # allow 2 hours extra after daylight time switch (4 am instead of 2 am)
    # DSTStartOrEndDateTime = eastern.localize(datetime.datetime(2019, 3, 11, 4), is_dst=True).isoformat()
    DSTStartOrEndDateTime = eastern.localize(datetime.datetime(2018, 11, 4, 4), is_dst=True).isoformat()

    
    logging.info(DSTStartOrEndDateTime)

    domain = 'https%3A%2F%2Fgrow-weather.appspot.com'
    #domain = 'https%3A%2F%2Ffc2116ab.ngrok.io'

    addURL = ('https://api.atrigger.com/v1/tasks/create?key=' + 
    A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
    '&timeSlice=1year&count=-1&url=' + domain + 
    '/endpoints/updateDaylightSavings/' + '&tag_type=DST&first=' + DSTStartOrEndDateTime + '&post=True')

    A_TRIGGER_PAYLOAD_SECRET = Settings.get('A_TRIGGER_PAYLOAD_SECRET')
    data = {'A_TRIGGER_PAYLOAD_SECRET': A_TRIGGER_PAYLOAD_SECRET}
    #r = requests.post(addURL, data={'userID': user.userID or 'None'}, verify=True)
    addDSTTaskResponse = requests.post(addURL, data=data, verify=True)
    return HttpResponse(json.dumps(addDSTTaskResponse.json()))
'''
