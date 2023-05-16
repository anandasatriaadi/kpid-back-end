from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CreateStationRequest(object):
    key: str
    name: str
    created_at: datetime = field(default=datetime.utcnow())
    updated_at: datetime = field(default=datetime.utcnow())


@dataclass
class UpdateStationRequest(object):
    key: str
    name: str
    updated_at: datetime = field(default=datetime.utcnow())
