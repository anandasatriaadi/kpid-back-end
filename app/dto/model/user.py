from dataclasses import dataclass, field
from datetime import datetime

from bson import ObjectId


@dataclass
class User:
    _id: ObjectId = None
    password: str = None
    name: str = None
    email: str = None
    role: str = None
    is_active: bool = None
    last_login: datetime = None
    created_at: datetime = None

    def as_dict(self):
        data = self.__dict__.copy()
        data["_id"] = str(self._id)
        return data

    @classmethod
    def from_document(cls, data: dict):
        return cls(**data)
