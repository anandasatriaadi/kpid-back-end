from dataclasses import dataclass
from bson import ObjectId


@dataclass
class UserResponse():
    id: ObjectId = None
    user_id: str = None
    name: str = None
    email: str = None

    @classmethod
    def from_document(cls, data: dict):
        return cls(**data)
