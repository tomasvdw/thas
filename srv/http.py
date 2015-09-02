

class HttpError(Exception):
    def __init__(self, message, httpcode):
        self.message = message
        self.httpcode = httpcode

    def __str__(self):
        return self.httpcode + ' ' + self.message  

