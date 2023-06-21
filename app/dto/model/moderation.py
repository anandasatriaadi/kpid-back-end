from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Union

from bson import ObjectId

from app.dto.enum.moderation_status import ModerationStatus
from app.dto.model.frame_result import FrameResult
from app.dto.model.moderation_result import ModerationResult
from app.dto.model.station import Station


@dataclass
class Moderation:
    _id: ObjectId
    user_id: str
    filename: str
    program_name: str
    station_name: Station
    start_time: str
    end_time: str
    fps: int
    duration: float
    total_frames: int
    recording_date: datetime = field(default=None)
    description: str = field(default=None)
    status: ModerationStatus = field(default=None)
    created_at: datetime = field(default=None)
    updated_at: datetime = field(default=None)
    result: List[ModerationResult] = field(default=None)
    frames: List[FrameResult] = field(default=None)

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def as_dict(self):
        data = self.__dict__.copy()
        data["_id"] = str(self._id)
        return data

    @classmethod
    def from_document(cls, document: dict):
        data = document.copy()
        data["_id"] = str(data["_id"])
        data["station_name"] = Station.from_document(data["station_name"]).as_dict()

        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
