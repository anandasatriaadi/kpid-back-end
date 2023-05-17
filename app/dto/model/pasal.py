from dataclasses import dataclass

from bson import ObjectId


@dataclass
class Pasal(object):
    _id: ObjectId
    category: str
    chapter: str
    description: str
    pasal: str

    def as_dict(self):
        data = self.__dict__.copy()
        data["_id"] = str(self._id)
        return data

    @classmethod
    def from_document(cls, data: dict):
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
