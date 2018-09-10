from __future__ import absolute_import

from celery import shared_task
from django.conf import settings
from twilio.rest import Client

import arrow

from models import *
from datetime import datetime

# Uses credentials from the TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
# environment variables
client = Client()

@shared_task
def sendReport(userID):
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