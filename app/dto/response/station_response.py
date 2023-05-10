from dataclasses import dataclass, field
from datetime import datetime

from bson import ObjectId


@dataclass
class StationResponse():
    _id: str = field(default=None)
    key: str = field(default=None)
    name: str = field(default=None)
    created_at: datetime = field(default=None)
    updated_at: datetime = field(default=None)

    def as_dict(self):
        data = self.__dict__.copy()
        return data

    @classmethod
    def from_document(cls, data: dict):
        return cls(**data)
