from dataclasses import dataclass, field
from datetime import datetime

from pytz import timezone


@dataclass
class CreateActivityRequest:
    date: datetime
    users_count: int
    users: list
    created_at: datetime = field(default=datetime.utcnow())
    updated_at: datetime = field(default=datetime.utcnow())
