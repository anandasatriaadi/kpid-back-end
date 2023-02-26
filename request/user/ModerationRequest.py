from dataclasses import dataclass

@dataclass
class CreateModerationRequest(object):
    program_name: str
    station_name: str
    start_time: str