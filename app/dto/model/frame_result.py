from dataclasses import dataclass


@dataclass
class FrameResult:
    frame_time: float
    frame_url: str

    def as_dict(self):
        data = self.__dict__.copy()
        return data