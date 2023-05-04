from dataclasses import dataclass, field

from bson import ObjectId


@dataclass
class UserResponse():
    id: ObjectId = field(default=None)
    user_id: str = field(default=None)
    name: str = field(default=None)
    email: str = field(default=None)

    @classmethod
    def from_document(cls, data: dict):
        return cls(**data)
