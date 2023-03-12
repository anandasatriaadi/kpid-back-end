from dataclasses import dataclass


@dataclass
class UserResponse(object):
    user_id: str = None
    name: str = None
    email: str = None
