from dataclasses import dataclass, field

from bson import ObjectId


@dataclass
class PasalResponse:
    _id: ObjectId = field(default=None)
    category: str = field(default=None)
    chapter: str = field(default=None)
    description: str = field(default=None)
    pasal: str = field(default=None)

    def as_dict(self):
        data = self.__dict__.copy()
        return data

    @classmethod
    def from_document(cls, data: dict):
        return cls(**data)
