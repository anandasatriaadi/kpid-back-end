from dataclasses import dataclass, field
from datetime import datetime
from app.dto.enum import ModerationStatus

@dataclass
class CreateModerationRequest():
    user_id: str
    filename: str
    program_name: str
    station_name: str
    description: str
    start_time: str
    end_time: str
    fps: int
    duration: float
    total_frames: int
    status: ModerationStatus = field(default=ModerationStatus.INITIALIZED)
    result: list = field(default_factory=list)
    created_at: datetime = field(default=datetime.utcnow())
    updated_at: datetime = field(default=datetime.utcnow())

    def as_dict(self):
        data = self.__dict__.copy()
        data['status'] = self.status.value
        return data


@dataclass
class UpdateModerationRequest():
    filename: str
    program_name: str
    station_name: str
    status: ModerationStatus
    updated_at: datetime
    result: list = field(default_factory=list)

    def as_dict(self):
        data = self.__dict__.copy()
        data['status'] = self.status.value
        return data
