from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from bson import ObjectId


@dataclass
class ActivityResponse:
    _id: ObjectId = None
    date: datetime = None
    users_count: int = None
    users: List[Dict[str, str]] = None

    def as_dict(self):
        data = self.__dict__.copy()
        data["_id"] = str(self._id)
        return data

    @classmethod
    def from_document(cls, data: dict):
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
