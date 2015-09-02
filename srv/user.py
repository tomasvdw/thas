

import main
from pesto import Response
from urllib import unquote, quote
from redis import StrictRedis

from datetime import datetime

from http import HttpError
import iso8601
import geohash

import re
import random
import string
import hashlib
import unittest

from point import Point

rd = StrictRedis(host='localhost', port=6379, db=0)

USERNAME_REGEX = r"^[a-zA-Z0-9-_]{3,12}$"
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$"
PASSWORD_REGEX = r"^.{3,15}$"

 
class User(dict):

    def __init__(self):
        pass

    @classmethod
    def load(cls, userid):
        "Loads the user from the database"
        d = rd.hgetall('u:' + userid)
        if (not d or not 'pass_seed' in d):
            raise HttpError('Invalid username/password', 400)
        user = User()
        for k,v in d.iteritems():
            user[k] = v
        return user

    def check_password(self, request):
        "Checks the supplied password"
        supplied_password = unquote(request.form['password'])

        m = hashlib.sha1()
        m.update(supplied_password)
        m.update(self['pass_seed'])
        supplied_passhash = m.hexdigest()
    
        if (supplied_passhash != self['pass_hash']):
            raise HttpError('Invalid username/password', 400)

    def locked_for(self):
        if not 'locked' in self:
            return 0

        delta = iso8601.parse_date(self['locked']) - datetime.now() 
        return delta.total_seconds()


    @classmethod
    def get(cls, request):
        name = unquote(request.form['name'])
        userid = name.lower()
        user = cls.load(userid)

        isme = ('password' in request.form)
        if (isme):
           user.check_password(request)

        result = [];

        result.append('name=' + (user['name']))

        if (isme):
            for n in ['cam'+str(x) for x in range(1,5)]:
                if (n in user):
                    result.append(n+'=' + user[n])


        return '\n'.join(result)

    def update_centre(self, pipe, point):
        
        if not 'points' in self:
            self['points'] = 1
        else:
            self['points'] = int(self['points']) + 1

        if not 'centre' in self:
            self['centre'] = str(point)
        else:
            c = Point(self['centre'])
            c.lat = ((c.lat * (self['points']-1) + point.lat)
                / self['points'] )
            c.lon = ((c.lon * (self['points']-1) + point.lon)
                / self['points'] )

        userid = self['name'].lower()
        pipe.hset('u:' + userid, 'centre', self['centre'])
        pipe.hset('u:' + userid, 'points', self['points'])



        
    @classmethod
    def signup(cls, request):
        if request.content_type != 'application/x-www-form-urlencoded':
            raise HttpError('Invalid content type\n', 400)
 
        user = User()
        user['name'] = unquote(request.form['name'])
        user['email'] = unquote(request.form['email'])
        userid = user['name'].lower()
        password = unquote(request.form['password'])
        privatekey = unquote(request.form['key'])
 
        # validate
 
        if not re.match(USERNAME_REGEX, user['name']):
           raise HttpError('Invalid username', 400)
 
        if not re.match(EMAIL_REGEX, user['email']):
           raise HttpError('Invalid email', 400)
 
        if not re.match(PASSWORD_REGEX, password):
           raise HttpError('Invalid password', 400)
 
        if main.KEY != privatekey:
           raise HttpError('Invalid key', 400)
 
        # setup seed 
        user['pass_seed'] = ''.join(random.choice(string.hexdigits) for n in xrange(16))
        m = hashlib.sha1()
        m.update(password)
        m.update(user['pass_seed'])
        user['pass_hash'] = m.hexdigest()
 
        # check if email exists
        # ignore atomicity problem for now; we're fast enough
        if rd.exists('email:' + user['email']):
           raise HttpError('Email exists', 409)
 
        # check if user exsists
        if rd.exists('u:' + userid):
           raise HttpError('Name exists', 409)
 
        user['created'] = datetime.utcnow().isoformat()
 
        # store user as hash and email in uniqueness set
        pipe = rd.pipeline()
        pipe.hmset('u:' + userid, user)
        pipe.set('email:' + user['email'], userid) 
        pipe.execute()

        return 'OK'

class Tests(unittest.TestCase):

    def test_api(self):
        rd.flushall()
        main.test('/signup', { 
           'name':'Tomtomtom', 
           'password':'merced33', 
           'email':'tomasvdw@gmail.com'
           })

        main.test('/trip', {
            'name':'tomtomtom', 
            'password':'merced33', 
            'loc':'51x4',
            'cam-num':'2',
            'cam-direction':'2'
        })
        main.test('/trip', {
            'name':'tomtomtom', 
            'password':'merced33', 
            'loc':'51x4.002',
            'cam-num':'2',
            'cam-direction':'2'
        })

        main.test('/get-user', { 
           'name':'tomtomtom', 
           'password':'merced33'
           })


if __name__ == "__main__":
    unittest.main()
