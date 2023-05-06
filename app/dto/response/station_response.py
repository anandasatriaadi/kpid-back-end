from dataclasses import dataclass, field

from bson import ObjectId


@dataclass
class StationResponse():
    _id: str = field(default=None)
    key: str = field(default=None)
    name: str = field(default=None)

    @classmethod
    def from_document(cls, data: dict):
        return cls(**data)
