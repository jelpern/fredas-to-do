#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import datetime
from pprint import pprint

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# [END imports]

DEFAULT_TASKLIST_OWNER = "default_tasklist"


def tasklist_key(tasklist_name):
    """Constructs a Datastore key for a tasklist entity.
    """
    return ndb.Key('Task_Store', tasklist_name)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, t, **kw):
        # t = JINJA_ENVIRONMENT.get_template(template)
        return t.render(kw)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def user_check(self):
        """ Checks if the user is logged in. If so, writes a greeting and returns
        a string with the value of the tasklist key for that user.
        """
        user = users.get_current_user()
        if user:
            self.write(user.nickname() + "<br><br><br>")
            tasklist_name = user.nickname()
        else:
            tasklist_name = DEFAULT_TASKLIST_OWNER
            self.redirect(users.create_login_url(self.request.uri))
        return tasklist_name


class Task(ndb.Model):

    index = ndb.IntegerProperty()
    description = ndb.StringProperty(indexed = False) 
    completed = ndb.BooleanProperty()
    due_date = ndb.DateProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    owner = ndb.UserProperty()

    # description = ""
    # due_date = ""

    # def __init__(self, index, description, due_date, user=None):
    #     self.index = index
    #     self.description = description
    #     self.due_date = due_date
    #     self.user = user


class MainHandler(Handler):

    def render_front(self, kw):
        t = JINJA_ENVIRONMENT.get_template("index.html")
        self.response.write(t.render(kw))

    def get(self):
        # Checks for active Google account session
        tasklist_name = self.user_check()
        user = users.get_current_user()
        url = users.create_logout_url(self.request.uri)
        url_linktext = 'Logout'

        # temporary lines to set up data structure for template
        # sample_task = Task(parent=tasklist_key(tasklist_name))
        # sample_task.index = 1
        # sample_task.description = "This is a sample task"
        # sample_task.completed = False
        # sample_task.due_date = datetime.date(2015, 12, 31)
        # sample_task.owner = user
        # sample_task.put()

        # sample_task2 = Task(parent=tasklist_key(tasklist_name))
        # sample_task2.index = 2
        # sample_task2.description = "This is another sample task"
        # sample_task2.completed = True
        # sample_task2.due_date = datetime.date(2015, 12, 31)
        # sample_task2.owner = user
        # sample_task2.put()

        # back to our regularly scheduled programming
        tasks_query = Task.query(ndb.AND(Task.completed == False,
                                         Task.owner == user)).order(Task.created)
        tasks_list = []
        for task in tasks_query:
            tasks_list.append(task)

        # build the parameters for the template 
        template_values = {
            "tasks": tasks_list,
            "url": url,
            "url_linktext": url_linktext
        }
        # self.write(template_values)
        
        # self.render_str(t, template_values)
        # self.render("index.html", template_values)
        self.render_front(kw=template_values)

    def post(self):
        self.write("This is supposed to be the post action.")
        self.render_front()


class AddHandler(Handler):
    def post(self):
        # We set the same parent key on the 'Greeting' to ensure each Greeting
        # is in the same entity group. Queries across the single entity group
        # will be consistent. However, the write rate to a single entity group
        # should be limited to ~1/second.
        tasklist_name = self.user_check()
        user = users.get_current_user()

        # build new task object
        task = Task(parent=tasklist_key(tasklist_name))
        
        # TODO: add unique key generator
        pprint(vars(task))
        task.index = ndb.Model.allocate_ids(size=1,
                                            parent=tasklist_key(tasklist_name))[0]
        task.description = self.request.get("new_task")
        task.completed = False
        year = int(self.request.get("year"))
        month = int(self.request.get("month"))
        day = int(self.request.get("day"))
        task.due_date = datetime.date(year, month, day)
        task.owner = user
        print "  "
        pprint(vars(task))
        task_key = task.put()
        print("task_key class: " + str(task_key.__class__))
        print("task_key value: " + str(task_key.id()))
        # pprint(dir(task_key))

        # self.write("This is supposed to be the add action.")
        self.redirect('/')


class UpdateHandler(Handler):

    def post(self):
        tasklist_name = self.user_check()
        user = users.get_current_user()

        # self.write("Filler page for updating the database" + "<br>")
        # self.write("The full HTTP request: " + "<br><br>")
        # self.write(self.request)
        # self.write("<br><br>")

        # get all of the checkbox names
        checked_tasks = self.request.arguments()
        for value in checked_tasks:
            if self.request.get(value) == "completed":
                # TODO mark it as completed in database
                qry = Task.query(ndb.AND(Task.index == int(value),
                                         Task.owner == user))
                print("Value: " + value + "; number: " + 
                      str(qry.count()) + "<br>")
                if qry:
                    task = qry.fetch(1)[0]
                    print(task.description)
                    task.completed = True
                    task.put()
        self.redirect('/')


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/add', AddHandler),
    ('/update', UpdateHandler)
], debug=True)
