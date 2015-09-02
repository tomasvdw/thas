
from datetime import datetime

from pesto import Response, dispatcher_app

from user import User
from trip import Trip

from http import HttpError

application = dispatcher = dispatcher_app()

# Pepper
KEY = 'constantinopel12'



@dispatcher.match('/', 'GET')
def versioninfo(request):
     """
     Show version info
     """
     return Response('THAS server 1.0')


@dispatcher.match('/signup', 'POST')
def POST_signup(request):
    return _process(User.signup, request)

@dispatcher.match('/get-user', 'POST')
def GET_user(request):
    return _process(User.get, request)

@dispatcher.match('/stop-trip', 'POST')
def POST_stoptrip(request):
    return _process(Trip.stop, request)


@dispatcher.match('/trip', 'POST')
def POST_trip(request):
    return _process(Trip.create_point, request)

def _process(func, request):
    try:
        return Response(func(request))
    except HttpError as e:
        return Response(e.message, e.httpcode)
    except Exception as e:
        raise
    #return Response('Internal server error: ' + str(e), 500)

def test(url, data):
    from pesto.testing import TestApp
    data['key'] = KEY
    print(TestApp(dispatcher).post(url, data))


