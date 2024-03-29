from dataclasses import dataclass, field
from datetime import datetime

from bson import ObjectId


@dataclass
class StationResponse:
    _id: ObjectId = field(default=None)
    key: str = field(default=None)
    name: str = field(default=None)
    created_at: datetime = field(default=None)
    updated_at: datetime = field(default=None)

    def as_dict(self):
        data = self.__dict__.copy()
        return data

    @classmethod
    def from_document(cls, data: dict):
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
