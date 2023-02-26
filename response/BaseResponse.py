from dataclasses import dataclass
from http import HTTPStatus


@dataclass
class BaseResponse(object):
    data: any = None
    status: HTTPStatus = None

    def set_response(self, data, status):
        self.data = data
        self.status = status
