from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Union

from bson import ObjectId

from app.dto import ModerationResult, ModerationStatus, Station


@dataclass
class ModerationResponse:
    _id: ObjectId
    user_id: str
    filename: str
    program_name: str
    station_name: Union[Station, str]
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
    frames: list = field(default=None)

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @classmethod
    def from_document(cls, document: dict):
        data = document.copy()
        data["_id"] = str(data["_id"])
        if isinstance(data["station_name"], dict):
            data["station_name"] = Station.from_document(data["station_name"]).as_dict()

        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
