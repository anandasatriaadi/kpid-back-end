from dataclasses import dataclass
from typing import List

from app.dto import ModerationDecision


@dataclass
class ModerationResult:
    second: float = None
    clip_url: str = None
    decision: ModerationDecision = None
    category: List[str] = None
    label: List[str] = None

    def as_dict(self):
        data = self.__dict__.copy()
        return data

    @classmethod
    def from_document(cls, data: dict):
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)
