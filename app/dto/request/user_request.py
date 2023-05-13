from dataclasses import dataclass, field
from datetime import datetime

from pytz import timezone


@dataclass
class LoginUserRequest(object):
    email: str
    password: str


@dataclass
class CreateUserRequest(object):
    name: str
    email: str
    password: str
    confirm_password: str
    role: str = field(default="user")
    last_login: datetime = field(default=None)
    created_at: datetime = field(default=datetime.utcnow())

@ dataclass
class UpdateUserRequest:
    user_id: str = field(default=None)
    name: str = field(default=None)
    email: str = field(default=None)
    role: str = field(default=None)
