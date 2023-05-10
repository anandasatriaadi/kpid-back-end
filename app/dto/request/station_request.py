from dataclasses import dataclass, field
from datetime import datetime

from pytz import timezone


@dataclass
class CreateStationRequest(object):
    key: str
    name: str
    created_at: datetime = field(default=datetime.now(timezone("Asia/Jakarta")))
    updated_at: datetime = field(default=datetime.now(timezone("Asia/Jakarta")))

@dataclass
class UpdateStationRequest(object):
    key: str
    name: str
    updated_at: datetime = field(default=datetime.now(timezone("Asia/Jakarta")))