from dataclasses import dataclass

@dataclass
class LoginUserRequest(object):
    email: str
    password: str

@dataclass
class CreateUserRequest(object):
    name: str
    email: str
    password: str
    user_id: str = None