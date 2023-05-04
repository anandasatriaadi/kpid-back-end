from dataclasses import dataclass
from typing import List

from app.dto import ModerationDecision


@dataclass
class ModerationResult():
    second: float
    clip_url: str
    decision: ModerationDecision
    category: List[str]
