class BaseResponse(object):
    def __init__(self, data=None, status=None):
        self.data = data
        self.status = status
    
    def setResponse(self, data, status):
        self.data = data
        self.status = status
