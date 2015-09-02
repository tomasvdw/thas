

import math
import geohash

class Point:
    def __init__(self, s):
        self.lat, self.lon = s.split('x')
        self.lat = float(self.lat)
        self.lon = float(self.lon)

    def __str__(self):
        return str(self.lat) + 'x' + str(self.lon)

    def hashUser(self):
        return self.hash(5)

    def hashCamera(self):
        return self.hash(7)

    def hash(self, zoom):
        return geohash.encode(self.lat, self.lon, zoom)


    def distance(self, other):
        lat1, lon1 = self.lat, self.lon
        lat2, lon2 = other.lat, other.lon
        radius = 6371000 # m

        dlat = math.radians(lat2-lat1)
        dlon = math.radians(lon2-lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
          * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d = radius * c

        return d

