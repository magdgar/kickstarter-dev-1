from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
from protorpc import messages
import datetime

GOAL_OVC = 100


class Status(messages.Enum):
    ACTIVE = 0
    ACCEPTED = 1
    EXPIRED = 2


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
            'time': str(self.createdOn.time())
        }
        return obj

    def check_if_accepted(self):
        if self.money >= GOAL_OVC:
            self.status = Status.ACCEPTED
            self.put()


def get_entities_by_name(name):
    if name != "":
        project = Project.query(Project.name == name).get()
        return project.to_json_object()

    else:
        projects = Project.query().fetch(25)
        projects_jsons = []
        for project in projects:
            obj = project.to_json_object()
            projects_jsons.append(obj)
        return projects_jsons


def update_projects_status():
    month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    expired_projects = Project.query().filter(Project.createdOn < month_ago).fetch()
    for project in expired_projects:
        if project.status == Status.ACTIVE:
            project.status = Status.EXPIRED
            project.put()