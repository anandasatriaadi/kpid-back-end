from dataclasses import dataclass


@dataclass
class ModerationResponse(object):
    program_name: str
    station_name: str
    start_time: str
    filename: str
    frame_rate: float
    duration: float
