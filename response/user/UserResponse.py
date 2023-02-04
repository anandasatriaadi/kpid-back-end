from dataclasses import dataclass

@dataclass
class UserResponse(object):
    name: str
    email: str