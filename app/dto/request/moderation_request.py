from dataclasses import dataclass, field
from datetime import datetime

from pytz import timezone

from app.dto.enum import ModerationStatus
from app.dto.model import Station


@dataclass
class CreateModerationRequest():
    user_id: str
    filename: str
    program_name: str
    station_name: Station
    description: str
    recording_date: datetime
    start_time: str
    end_time: str
    fps: int
    duration: float
    total_frames: int
    status: ModerationStatus = field(default=ModerationStatus.INITIALIZED)
    result: list = field(default_factory=list)
    created_at: datetime = field(default=datetime.now(timezone("Asia/Jakarta")))
    updated_at: datetime = field(default=datetime.now(timezone("Asia/Jakarta")))

    def as_dict(self):
        data = self.__dict__.copy()
        data['status'] = self.status.value
        data['station_name'] = self.station_name.__dict__
        return data


@dataclass
class UpdateModerationRequest():
    filename: str
    program_name: str
    station_name: Station
    status: ModerationStatus
    updated_at: datetime = field(default=datetime.now(timezone("Asia/Jakarta")))
    result: list = field(default_factory=list)

    def as_dict(self):
        data = self.__dict__.copy()
        data['status'] = self.status.value
        return data
