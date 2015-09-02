

# Script that handles point creation

import main
import iso8601
from http import HttpError
from redis import StrictRedis
from urllib import unquote
from user import User
from point import Point
from datetime import datetime
from camera import Camera
import hashlib
import geohash
import string
import re

rd = StrictRedis(host='localhost', port=6379, db=0)

LOCK_TIME = 300

TRIP_DIST = 500  # distance in m to travel in a trip
TRIP_TIME = 60 * 30 # time in seconds to wait in a trip

TRIP_TIMEOUT = 5 * 60 # expire time when no data arrives

class Trip(dict):

    @classmethod 
    def load(cls, userid):
        "Loads the trip from the database"
        d = rd.hgetall('t:' + userid)
        if not d:
            return None
        trip = Trip()
        for k,v in d.iteritems():
            trip[k] = v
        return trip

    @classmethod
    def create_new(cls, userid, loc):
        "Inititializes a new trip in memory"
        self = cls()
        self['userid'] = userid
        self['loc'] = self['loc1'] = self['loc2'] = str(loc)
        self['created'] = datetime.utcnow().isoformat()
        self['points'] = 0
        self['point_count'] = 0
        return self


    def extend(self, loc, evilness):
        "Extends the bounding box of the trip with loc and add evilness points"
        self['points'] = str(int(self['points']) + evilness )
        self['point_count'] = str(int(self['point_count']) + 1)
        ll = Point(self['loc1'])
        ur = Point(self['loc2'])
        if (loc.lat < ll.lat): ll.lat = loc.lat
        if (loc.lon < ll.lon): ll.lon = loc.lon
        if (loc.lat > ur.lat): ur.lat = loc.lat
        if (loc.lon > ur.lon): ur.lon = loc.lon
        self['loc1'] = str(ll)
        self['loc2'] = str(ur)

    def progress(self):
        "Returns the progress in the trip as value between 0 and 1"

        ll = Point(self['loc1'])
        ur = Point(self['loc2'])

        dist_prog = ll.distance(ur) / TRIP_DIST

        delta = datetime.utcnow() - \
            iso8601.parse_date(self['created']).replace(tzinfo=None)
        time_prog = float(delta.seconds + delta.days * 24 * 3600) / TRIP_TIME
        return min(dist_prog, time_prog)

    def save(self, pipe):
        "Stores the trip in the database"

        pipe.hmset('t:'+self['userid'], self)
        pipe.expire('t:'+self['userid'], TRIP_TIMEOUT)        

    @classmethod
    def create_point(cls,request):
    
        # load and check user
        userid = unquote(request.form['name']).lower()
        user = User.load(userid=userid)
        user.check_password(request)
    
    
        # check if locked
        if user.locked_for() > 0:
            return 'LOCKED: ' + str(user.locked_for())

        # get existing trip
        trip = Trip.load(userid)

        # see where we moving from and to
        loc = Point(unquote(request.form['loc']))
        prevloc = Point(trip['loc']) if trip else loc

        pipe = rd.pipeline()

        # remove user from map
        if trip:
            pipe.srem('userloc:'+prevloc.hashUser(), userid)

        # count users
        evilness = rd.scard('userloc:' + loc.hashUser())

        if Camera.check_line(prevloc, loc, userid):
            Camera.deactivate(pipe, user)
            pipe.delete('t:' + userid)

            # add feed "Spotted"
            #  
            # 
            pipe.execute()
            return 'LOCKED: ' + str(user.locked_for())

        # now we now we're good
        # see if we have a camera to place
        if ('cam-num' in request.form):
           direction = request.form['cam-direction']
           num = request.form['cam-num']
           cam = Camera.create_new(userid, num, str(loc), direction)
           cam.place(user, pipe)


        # add user to map
        pipe.sadd('userloc:'+loc.hashUser(), userid)

        # update users centre-spot
        user.update_centre(pipe, loc)
        
        if not trip:
            # create a new trip
            trip = Trip.create_new(userid, loc)
            trip.save(pipe)
            Camera.activate(pipe, user)

        else:
            # extend trip
            trip.extend(loc, evilness)

            if (trip.progress() >= 1):
                # we're done
                trip.save(pipe)
                user.add_trip_points(pipe, float(trip['points']) / float(trip['point_count']))
                trip = Trip.create_new(userid, loc)
                # feed.create()
                pipe.execute()
                return 'DON'
            else:
                # save
                trip.save(pipe)

        pipe.execute()
        return 'ACT: ' + str(trip.progress()) + ':' + str(evilness)

    @classmethod
    def stop(cls, request):
        userid = unquote(request.form['name']).lower()
        user = User.load(userid)
    
        user.check_password(request)

        # get existing trip
        trip = Trip.load(userid)

        pipe = rd.pipeline()

        # remove user from map
        if trip:
            prevloc = Point(trip['loc'])
            pipe.srem('userloc:'+prevloc.hashUser(), userid)

        Camera.deactivate(pipe, user)
        pipe.delete('t:' + userid)
        pipe.execute()

        return 'OK'
    

if __name__ == "__main__":
    from pesto.testing import TestApp
    data = { 
          'name':'tomtomtom2', 
          'password':'merced33', 
          'loc':'51.1x3.1203',
          'key':main.KEY
    }
    print(TestApp(main.dispatcher).post('/trip', data))

