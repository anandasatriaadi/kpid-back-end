from dataclasses import dataclass, field
from datetime import datetime

from bson import ObjectId
from pytz import timezone


@dataclass
class User():
    _id: ObjectId = None
    password: str = None
    user_id: str = None
    name: str = None
    email: str = None
    last_login: datetime = None
    created_at: datetime = None

    @classmethod
    def from_document(cls, data: dict):
        return cls(**data)