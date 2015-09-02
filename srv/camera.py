import main
from http import HttpError
from redis import StrictRedis
from urllib import unquote
from user import User
import hashlib
import geohash
import string
import re
import unittest
import point

from shapely.geometry import Point, LineString
from shapely.geometry.polygon import Polygon

rd = StrictRedis(host='localhost', port=6379, db=0)


class Camera:

    def __init__(self, camstring):  
        "Creates a camera from a string"
        self.camstring = camstring
        self.userid, self.num, loc, self.direction = camstring.split(':')
        self.loc = point.Point(loc) 

    @classmethod
    def create_new(cls, userid, num, loc, direction):
        "Creates a camera with the given params"
        return cls(':'.join([userid, num, loc, direction]))


    def hash(self):
        "return the geohash of the location of the camera"
        return geohash.encode(self.loc.lat, self.loc.lon, 7)

    def __str__(self):
        return self.camstring

    @classmethod
    def activate(cls, pipe, user):
        "put cams in the index so they are active"
        for n in range(1,5):
            if 'cam' + str(n) in user:
                cam = cls(user['cam' + str(n)])
                pipe.sadd('camloc:'+cam.hash(), str(cam))

    @classmethod
    def deactivate(cls, pipe, user):
        "Remove cams from index so they become inactive"
        for n in range(1,5):
            if 'cam' + str(n) in user:
                cam = cls(user['cam' + str(n)])
                pipe.srem('camloc:'+cam.hash(), str(cam))

    def check_camera_line(self, loc1, loc2, userid):
        "Checks if the line fals within the given line"

        # Ignore my own cameras
        if self.userid == userid:
            return False

        line = LineString([(loc1.lon, loc1.lat),(loc2.lon,loc2.lat)])
        start = Point(loc1.lon, loc1.lat)
        # Setup geometry for this cam
        cam_shape = self.get_cam_shape()

        isect = line.intersection(cam_shape)
        if isect.is_empty:
            return False
        else:
            return isect.distance(start)


        return False 

    def get_cam_shape(self):
        "Returns the shape object for this camera"
        RADIUS_M = 50 # m
        RADIUS_DEG = RADIUS_M / 111000
        cam_shape = Point(self.loc.lon, self.loc.lat).buffer(RADIUS_DEG,32)

        return cam_shape

    @classmethod
    def check_line(cls, loc1, loc2, userid):
        "Check if the given line intersects with a camera"

        # get all cameras in the neighbourhood
        hashes = geohash.expand(geohash.encode(loc1.lat, loc1.lon, 7))
        if str(loc1) != str(loc2):
            hashes.extend(geohash.expand(geohash.encode(loc2.lat, loc2.lon, 7)))
        sets = ['camloc:' + h for h in hashes]
        cams = rd.sunion(sets)

        for camstring in cams:
            cam = Camera(camstring)
            rate = cam.check_camera_line(loc1, loc2, userid)

        return False

    def place(self, user, pipe):

        if ('cam'+str(self.num) in user):

            # remove existing camera
            prevcam = Camera(user['cam'+str(self.num)])
            pipe.srem('camloc:'+prevcam.hash(), str(prevcam))


        pipe.sadd('camloc:'+self.hash(), str(self))
        pipe.hset('u:'+self.userid, 'cam'+str(self.num), str(self))

        pipe.execute()

        return 'OK'

class Tests(unittest.TestCase):
    def test_cons(self):
        "test constructor"
        camstring = 'tomtomtom:1:55.1x4.1:2'
        c = Camera(camstring)
        self.assertEqual(c.num, '1')
        self.assertEqual(c.userid, 'tomtomtom')
        self.assertEqual(c.camstring, camstring)

    def test_create(self):
        c = Camera.create_new('tomtomtom','1', '55.1x4.1', '2')
        self.assertEqual(c.camstring, 'tomtomtom:1:55.1x4.1:2')
        self.assertEqual(c.loc.lat, 55.1)

    def test_api(self):
        rd.flushall()
        main.test('/signup', { 
           'name':'tomtomtom', 
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



if __name__ == "__main__":
    unittest.main()
