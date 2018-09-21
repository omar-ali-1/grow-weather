
# -*- coding: utf-8 -*-

from django.shortcuts import render
# from hotelsite.models import Review
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
# import mongoengine
# AppEngine Imports
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

# Our App imports
from google.appengine.api import users, mail
from google.appengine.ext import webapp
from google.appengine.ext import ndb
from google.appengine.ext import deferred
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

def home(request):
    return render(request, "sourcebasesite/home.html")


def verifyOrCreateUser(request):
    claims = _getClaims(request)
    if not claims:
        return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)

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
        return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)

    profile = query_database(claims['sub'], claims)


    return HttpResponse(json.dumps(profile))



def signIn(request):
    # Verify Firebase auth.
    id_token = request.headers['Authorization'].split(' ').pop()
    claims = google.oauth2.id_token.verify_firebase_token(
        id_token, HTTP_REQUEST)
    if not claims:
        return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)
    else:
        return HttpResponse("Welcome, " + claims['sub'] + "!")


def _getGeoString(zipcode):
    try:
        # Google Maps API reverse geolocation using zipcode
        gMapsKey = 'AIzaSyA7LKqVl3C-0Vr38bDUi5B52LU434MopPA'
        getGeoLocURL = ('https://maps.googleapis.com/maps/api/geocode/' + 
            'json?key=' + gMapsKey + '&address=' + zipcode)
        geoResponse = requests.get(getGeoLocURL)
        location = geoResponse.json()['results'][0]['geometry']['location']
        return str(location['lat']) + ',' + str(location['lng'])

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
        user = _getUserObject(claims['sub'])
        userKey = user.userID
        alerts = Report.query(Report.user==userKey, Report.reportType=='rainAlert').order(-Report.datetime).fetch()
        logging.info(alerts)
        alertsList = []
        for alert in alerts:
            logging.info("Alert: ===========")
            logging.info(alert)
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


# Tasklet automatically handles batching of queries when using asynchronous get_async()
@ndb.tasklet
def _checkRainTask(userID):
    userKey = ndb.Key(User, userID)
    user = userKey.get_async()
    precipProbability = _getPrecipProb(user.geoString)
    logging.info(user.name + ':')
    logging.info(precipProbability)
    if precipProbability > -1:
        nowUTCDatetime = datetime.datetime.utcnow()
        reportType = 'rainAlert'
        report = Report(user=user.userID, datetime=nowUTCDatetime, precipitation=precipProbability, reportType=reportType)
        report.put()
        _sendReport(user, report, rainAlert=True)


@ndb.tasklet
def _enqueueCheckRainTasks():
    

@csrf_exempt
def checkRainAndAlertUsers(request):
    try:
        deferred.defer(_enqueueCheckRainTasks)
        users = User.query(User.receive_rain=='on').fetch()
        logging.info('we are here in check rain')
        logging.info(users)
        for user in users:
            precipProbability = _getPrecipProb(user.geoString)
            logging.info(user.name + ':')
            logging.info(precipProbability)
            if precipProbability > -1:
                nowUTCDatetime = datetime.datetime.utcnow()
                reportType = 'rainAlert'
                report = Report(user=user.userID, datetime=nowUTCDatetime, precipitation=precipProbability, reportType=reportType)
                report.put()
                _sendReport(user, report, rainAlert=True)
        return HttpResponse(json.dumps({'status':'success'}))
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


def _getPrecipProb(geoString):
    try:

        # Dark Weather API daily forecast
        darkWKey = 'e1a069d73553d2e120bf253c6de506c6'
        excludeList = 'currently,minutely,daily,alerts,flags'
        getForecastURL = ('https://api.darksky.net/forecast/' + darkWKey + '/' + 
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



def _getWeather(geoString):
    try:

        # Dark Weather API daily forecast
        darkWKey = 'e1a069d73553d2e120bf253c6de506c6'
        excludeList = 'currently,minutely,daily,alerts,flags'
        getForecastURL = ('https://api.darksky.net/forecast/' + darkWKey + '/' + 
        geoString + '?exclude=' + excludeList)
        forecastResponse = requests.get(getForecastURL)
        hourlyForecast = forecastResponse.json()['hourly']
        dailyForecast = forecastResponse.json()['daily']
        dailySummary = hourlyForecast['summary']
        dailyRainProb = int(round(dailyForecast['data'][0]['precipProbability'] * 100))
        dailyTemp = int(round(dailyForecast['data'][0]['temperature']))
        return [dailySummary, dailyTemp, dailyRainProb]
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


def resendReport(request):
    try:
        claims = _getClaims(request)
        user = _getUserObject(claims['sub'])
        userKey = claims['sub']
        report = Report.query(Report.user==userKey, Report.reportType=='dailyForecast').order(-Report.datetime).get()
        if report:
            _sendReport(user, report)
            return HttpResponse(json.dumps({'status':'success'}))
        else:
            return HttpResponse(json.dumps({'err':'You don\'t have any reports yet!'}))
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


def _sendReport(user, report, rainAlert=False):
    try:
        if rainAlert:
            reportBody = u'\nHey {}!\n\nIn about an hour, the chance of rain will be {}%.'.format(user.name, report.precipitation)
        else:
            reportBody = u'\nHey {}!\n\nHere is your forecast for today:\n\n{}\n\nTemp: {}\N{DEGREE SIGN}F\nChance of rain: {}%'.format(user.name, report.summary, report.temperature, report.precipitation)
        #logging.info(reportBody)

        # Twilio test
        authToken = 'ace161d8b47b77ad5a729b10c02633f0'
        accountSID = 'AC437de0c4319e3101f8a41972a7ed10fa'
        twilioNumber = '+16292069621'
        #twilioNumber = '+15005550006'


        client = Client(accountSID, authToken)
        message = client.messages.create(
            body=reportBody,
            # to='+1 615-592-5253',
            to= '+1' + user.phone,
            from_=twilioNumber,
        )

        senderAddress = 'omar.ali11231@gmail.com'
        recepientAddress = user.email
        mail.send_mail(sender=senderAddress,
                       to=recepientAddress,
                       subject="Your daily weather report from Grow",
                       body=reportBody
                       )
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


# TODO validate IP address of A Trigger API server
@csrf_exempt 
def sendReport(request):
    """Send a reminder to a phone using Twilio SMS"""
    # Get our appointment from the database
    try:

        req = request.REQUEST
        #logging.info('########## Request Data:')
        #logging.info(request.__dict__)
        user = _getUserObject(request.POST['userID'])
        dailySummary, dailyTemp, dailyRainProb = _getWeather(user.geoString)
        #logging.info('======== Weather Data:')
        #logging.info(_getWeather(user.zipcode))
        logging.info("======== We are here in sendReport===============")
        
        nowUTCDatetime = datetime.datetime.utcnow()
        reportType = 'dailyForecast'

        report = Report(user=user.userID, datetime=nowUTCDatetime, temperature=dailyTemp, summary=dailySummary, precipitation=dailyRainProb, reportType='dailyForecast')
        report.put()


        _sendReport(user, report)

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


def _updateReports(post, user, first=None):
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
                A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_ID=' + 
                user.userID + '&tag_type=reports')
                delete_response = requests.post(deleteURL)
                logging.info("delete_response")

        
        if updateReportsTask and receive_reports:
            deleteURL = ('https://api.atrigger.com/v1/tasks/delete?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + '&tag_ID=' + 
            user.userID + '&tag_type=reports')
            delete_response = requests.post(deleteURL)
            logging.info("delete_response")
            # ab6c5aca.ngrok.io/
            # grow-weather.appspot.com/



            reportDatetime = _getReportDatetime(user.timezone)


            triggerurl = ('https://api.atrigger.com/v1/tasks/create?key=' + 
            A_TRIGGER_KEY + '&secret=' + A_TRIGGER_SECRET + 
            '&timeSlice=1minute&count=-1&url=https%3A%2F%2Fab6c5aca.ngrok.io/' + 
            'endpoints/sendReport/' + 
            '&tag_ID=' + user.userID + '&tag_type=reports&first=' + '2018-09-14T12:46:47.260683-10:00' + '&post=True')
            logging.info(triggerurl)
            r = requests.post(triggerurl, data={'userID': user.userID or 'None'}, verify=True)
            logging.info(r.json())
        return userUpdated

    except Exception as e:
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


def _updateBasicUserInfo(user, claims):
    name = claims['name']
    email = claims['email']
    user.name = name
    user.email = email

def updateUserSettings(request):
    try:
        #### User authentication and fetching ###
        #logging.info("======== We are here in updateUserSettings================")
        claims = _getClaims(request)
        if not claims:
            return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)
        user = _getUserObject(claims['sub'])

        #### Request processing ###
        post = request.POST
        
        # Validate zipcode input and update corresponding user property
        zipcode = post['input-zip'] if 'input-zip' in post else None
        if not re.match(r"^[0-9]{5}(?:-[0-9]{4})?$", zipcode):
            return HttpResponse(json.dumps({'err': "Invalid zipcode."}))
        
        # Get geoString and save to user to save google API calls converting zipcode 
        # to geoStr every time we fetch weather
        geoString = _getGeoString(zipcode)


        # Fetch timezone info for the zipcode if zipcode has changed, and update corresp. user property
        timezone = _getTimeZone(request, zipcode) if zipcode != user.zipcode else ('', user.timezone)
        #logging.info(timezone)
        if timezone[0] == "err":
            return HttpResponse(json.dumps({'err': timezone[1]}))
        
        logging.info('############## timezone:')
        logging.info(user.timezone)

        # Validate phone input via Twilio API and update corresponding user property
        phone = post['input-phone'] if 'input-phone' in post else None
        if not _isValidPhoneNumber(phone):
            return HttpResponse(json.dumps({'err': "Invalid US phone number. Valid Format: 1234567891"}))
        
        # update user info
        user.zipcode = zipcode
        user.geoString = geoString
        user.phone = phone
        user.timezone = timezone[1]
        #logging.info('======== Weather Data:')
        #weatherData = _getWeather('37209')
        #logging.info(weatherData)
        # Update user's basic info
        _updateBasicUserInfo(user, claims)

        # Update user's report settings, and scheduled task via A Trigger Scheduling API
        _updateReports(post, user)
        user.receive_rain = post['check-receive-rain'] if 'check-receive-rain' in post else None

        # Save updated user to Datastore
        user.put()

        
        #logging.info(requests.get)

        
        return HttpResponse(json.dumps({'status':'success'}))
        
    except Exception as e:
        logging.info(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


def prepopulateFields(request):
    '''
    
'''
    try:
        logging.info("======== We are here in updateUserSettings================")
        claims = _getClaims(request)
        if not claims:
            return HttpResponse('Sorry! You did not provide the credentials necessary to access this resource.', status=401)
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
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
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
