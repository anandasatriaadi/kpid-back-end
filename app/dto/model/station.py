from dataclasses import dataclass
from datetime import datetime

from bson import ObjectId


@dataclass
class Station:
    _id: ObjectId = None
    key: str = None
    name: str = None
    created_at: datetime = None
    updated_at: datetime = None

    def as_dict(self):
        data = self.__dict__.copy()
        data["_id"] = str(self._id)
        return data

    @classmethod
    def from_document(cls, data: dict):
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
