# Copyright 2015 Google Inc
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# [START imports]
import unittest

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

import datetime
import pytz
# [END imports]


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



class Settings(ndb.Model):
  name = ndb.StringProperty()
  value = ndb.StringProperty()

  @staticmethod
  def get(name):
    NOT_SET_VALUE = "NOT SET"
    retval = Settings.query(Settings.name == name).get()
    if not retval:
      retval = Settings()
      retval.name = name
      retval.value = NOT_SET_VALUE
      retval.put()
    if retval.value == NOT_SET_VALUE:
      raise Exception(('Setting %s not found in the database. A placeholder ' +
        'record has been created. Go to the Developers Console for your app ' +
        'in App Engine, look up the Settings record with name=%s and enter ' +
        'its value in that record\'s value field.') % (name, name))
    return retval.value



# [START datastore_example_1]
class TestModel(ndb.Model):
    """A model class used for testing."""
    number = ndb.IntegerProperty(default=42)
    text = ndb.StringProperty()


class TestEntityGroupRoot(ndb.Model):
    """Entity group root"""
    pass


# [START datastore_example_test]
class DatastoreTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        # Clear ndb's in-context cache between tests.
        # This prevents data from leaking between tests.
        # Alternatively, you could disable caching by
        # using ndb.get_context().set_cache_policy(False)
        ndb.get_context().clear_cache()

# [END datastore_example_test]

    # [START datastore_example_teardown]
    def tearDown(self):
        self.testbed.deactivate()
    # [END datastore_example_teardown]

    # [START datastore_example_insert]
    def testInsertUser(self):
    	user = User(userID='LCaU4CoqV2foifOhhzUnsF3m9dt1', name='Omar Ali', email='omar.ali11231@gmail.com', 
			phone='6156387550', zipcode='37209', timezone='America/Chicago', geoString='36.1484862,-86.9523954',
			receive_email='on', receive_sms='on', receive_rain='on', receive_reports='on')
        user.put()
        self.assertEqual(user, user.key.get())
    def testInsertReport(self):
        report = Report(user=ndb.Key(User, 'LCaU4CoqV2foifOhhzUnsF3m9dt1'),
            datetime=datetime.datetime.now(), dailyLow=40, dailyHigh=70, precipitation=30, summary="some summary")
        report.put()
        self.assertEqual(report, Report.query().fetch()[0])
    def testInsertAlert(self):
        alert = Alert(user=ndb.Key(User, 'LCaU4CoqV2foifOhhzUnsF3m9dt1'), 
            datetime=datetime.datetime.now(), precipitation=80)
        alert.put()
        self.assertEqual(alert, Alert.query().fetch()[0])

    # [END datastore_example_insert]

    # [START datastore_example_filter]
    def testFilterByRainAlert(self):
        user1 = User(userID='LCaU4CoqV2foifOhhzUnsF3m9dt1', receive_rain='on')
        user2 = User(userID='MCaU4CoqV2foifOhhzUnsF3m9dt2', receive_rain=None)
        user1.put()
        user2.put()
        usersReceivingAlerts = User.query().filter(User.receive_rain=='on').fetch()
        self.assertEqual(1, len(usersReceivingAlerts))
        self.assertEqual(user1, usersReceivingAlerts[0])
    # [END datastore_example_filter]



# [START HRD_example_1]
from google.appengine.datastore import datastore_stub_util  # noqa


class HighReplicationTestCaseOne(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Create a consistency policy that will simulate the High Replication
        # consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(
            probability=0)
        # Initialize the datastore stub with this policy.
        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        # Initialize memcache stub too, since ndb also uses memcache
        self.testbed.init_memcache_stub()
        # Clear in-context cache before each test.
        ndb.get_context().clear_cache()

    def tearDown(self):
        self.testbed.deactivate()

    def testEventuallyConsistentGlobalQueryResult(self):
        class TestModel(ndb.Model):
            pass

        user_key = ndb.Key('User', 'ryan')

        # Put two entities
        ndb.put_multi([
            TestModel(parent=user_key),
            TestModel(parent=user_key)
        ])

        # Global query doesn't see the data.
        self.assertEqual(0, TestModel.query().count(3))
        # Ancestor query does see the data.
        self.assertEqual(2, TestModel.query(ancestor=user_key).count(3))
# [END HRD_example_1]

    # [START HRD_example_2]
    def testDeterministicOutcome(self):
        # 50% chance to apply.
        self.policy.SetProbability(.5)
        # Use the pseudo random sequence derived from seed=2.
        self.policy.SetSeed(2)

        class TestModel(ndb.Model):
            pass

        TestModel().put()

        self.assertEqual(0, TestModel.query().count(3))
        self.assertEqual(0, TestModel.query().count(3))
        # Will always be applied before the third query.
        self.assertEqual(1, TestModel.query().count(3))
    # [END HRD_example_2]


# [START main]
if __name__ == '__main__':
    unittest.main()
# [END main]