import json
import urllib

import operator
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
from google.appengine.api import mail
from protorpc import messages
import datetime

from backend.files.File import File
from backend.transactions.Transaction import Transaction
from backend.users.User import User

GOAL_OVC = 100


class Status(messages.Enum):
    ACTIVE = 0
    ACCEPTED = 1
    EXPIRED = 2
    HIDDEN = 3


class Project(ndb.Model):
    name = ndb.StringProperty()
    description = ndb.TextProperty()
    money = ndb.IntegerProperty(default=0)
    createdOn = ndb.DateTimeProperty(auto_now_add=True)
    creator = ndb.KeyProperty(kind='User')
    status = msgprop.EnumProperty(Status, default=Status.ACTIVE, indexed=True)

    def to_json_object(self):
        user = self.creator.get()
        obj = {
            'id': int(self.key.id()),
            'name': self.name,
            'description': self.description,
            'creatoryid': user.google_id,
            'creatorname': user.name,
            'money': self.money,
            'status': int(self.status),
            'date': str(self.createdOn.date()),
            'time': str(self.createdOn.strftime('%H:%M:%S')),
            'attachments': get_attachments(self)
        }
        return obj

    def check_if_accepted(self):
        if self.money >= GOAL_OVC:
            self.status = Status.ACCEPTED
            self.put()
            send_accepted_emails(self)

    def hide(self):
        self.status = Status.HIDDEN
        self.put()

    def get_url(self):
        return "https://kickstarter-dev.appspot.com/project/" + urllib.quote(str(self.name))


def send_accepted_emails(project):
    recipient = project.creator.get().name
    if '@' not in recipient:
        recipient += "@gmail.com"
    message = mail.EmailMessage(sender="Ocado Kickstarter <a.sokolowski@ocado.com>",
                                subject="[Ocado Kickstarter] Your project {0} has reached its goal!".format(
                                    project.name))
    message.to = "%s <%s>" % (project.creator.get().name, recipient)
    message.body = """
            Dear {0}:
            Your project has reached its goal. Congratulations! You've earned it.
            {1}
            """.format(project.creator.get().name, project.get_url())
    message.send()


def convert_to_json(projects):
    projects_jsons = []
    for project in projects:
        obj = project.to_json_object()
        projects_jsons.append(obj)
    return projects_jsons


def get_project_by_name(name):
    project = Project.query(Project.name == name).get()
    if project:
        return project.to_json_object()


def get_all_projects(query_params):
    projects = get_with_pagination(Project.query(), query_params.page, query_params.page_size)
    return convert_to_json(projects)


def update_projects_status():
    month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    expired_projects = Project.query().filter(Project.createdOn < month_ago).fetch()
    for project in expired_projects:
        if project.status == Status.ACTIVE:
            project.status = Status.EXPIRED
            project.put()


def get_best_projects(query_params):
    project_query = Project.query().order(-Project.money)
    projects = get_with_pagination(project_query, query_params.page, query_params.page_size)
    return convert_to_json(projects)


def get_trending_projects(query_params):
    timestamp = datetime.datetime.now() - datetime.timedelta(weeks=4)
    transactions_from_last_week = Transaction.query(Transaction.time_stamp > timestamp).fetch()
    projects = {}
    for t in transactions_from_last_week:
        projects[t.project] = 0

    for t in transactions_from_last_week:
        projects[t.project] += t.money

    pk = sorted(projects, key=projects.__getitem__)[:query_params.page_size]
    return convert_to_json(Project.query(ndb.AND(Project.key.IN(pk), Project.status == Status.ACTIVE)).fetch())


def get_projects_by_status(query_params):
    project_query = Project.query(Project.status == Status(query_params.status))
    projects = get_with_pagination(project_query, query_params.page, query_params.page_size)
    return convert_to_json(projects)


def search_for_projects(query_params):
    search_phrase = query_params.phrase.lower()
    all_projects = Project.query().fetch()
    return convert_to_json(filter(lambda p: search_phrase in p.name.lower() or search_phrase in p.description.lower()
                                      or check_project_author(p, search_phrase),
                                  all_projects))


def check_project_author(project, phrase):
    return phrase in project.creator.get().name.lower()


def get_usernames_for_phrase(phrase):
    return filter(lambda u: phrase in u.name, User.query().fetch())


def get_with_pagination(query, page, page_size):
    return query.fetch_page(page_size, offset=page * page_size)[0]


def get_attachments(project):
    attachments_json = []
    attachments = File.query(File.project == project.key).fetch()
    for attachment in attachments:
        attachments_json.append(attachment.to_json())
    return attachments_json if len(attachments_json) > 0 else ''
