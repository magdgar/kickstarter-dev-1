import json
from google.appengine.api import users
import webapp2
from UsersConnector import UserConnector, User


class UserHandler(webapp2.RequestHandler):
    def get(self):
        current_user = users.get_current_user()
        row = UserConnector().select_where("name = '%s'" % current_user.nickname())
        response = []
        obj = {
            'name': row[0],
            'money': row[1]
            }
        response.append(obj)
        return self.response.out.write(json.dumps(response))


app = webapp2.WSGIApplication([
    ('/user', UserHandler)
])