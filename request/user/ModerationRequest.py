from dataclasses import dataclass, field

@dataclass
class CreateModerationRequest(object):
    user_id: str
    filename: str
    program_name: str
    station_name: str
    start_time: str
    end_time: str
    fps: int
    duration: float
    total_frames: int
    result: list = field(default_factory=list)
