from dataclasses import dataclass
from typing import List

from app.dto import ModerationDecision


@dataclass
class ModerationResult:
    second: float
    clip_url: str
    decision: ModerationDecision
    category: List[str]

    def as_dict(self):
        data = self.__dict__.copy()
        return data

    @classmethod
    def from_document(cls, data: dict):
        return cls(**data)
