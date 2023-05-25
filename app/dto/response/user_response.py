from dataclasses import dataclass, field
from datetime import datetime

from bson import ObjectId


@dataclass
class UserResponse:
    _id: str = field(default=None)
    name: str = field(default=None)
    email: str = field(default=None)
    role: str = field(default=None)
    last_login: datetime = field(default=None)

    def as_dict(self):
        data = self.__dict__.copy()
        data['last_login'] = data['last_login'].timestamp()
        return data

    @classmethod
    def from_document(cls, data: dict):
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
