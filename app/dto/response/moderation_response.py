from dataclasses import dataclass, field
from datetime import datetime

from bson import ObjectId

from app.dto import ModerationStatus


@dataclass
class ModerationResponse():
    _id: ObjectId
    user_id: str
    filename: str
    program_name: str
    station_name: str
    recording_date: datetime
    start_time: str
    end_time: str
    fps: int
    duration: float
    total_frames: int
    description: str = field(default=None)
    status: ModerationStatus = field(default=None)
    created_at: datetime = field(default=None)
    updated_at: datetime = field(default=None)
    result: list = field(default=None)
    frames: list = field(default=None)
    videos: list = field(default=None)

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @classmethod
    def from_document(cls, document: dict):
        data = document.copy()
        data['_id'] = str(data['_id'])
        return cls(**data)
