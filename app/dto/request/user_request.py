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
    last_login: datetime = None
    created_at: datetime = field(default=datetime.now(timezone("Asia/Jakarta")))
