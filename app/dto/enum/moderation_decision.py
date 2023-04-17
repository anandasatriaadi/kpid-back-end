from enum import Enum


class ModerationDecision(Enum):
    PENDING = "PENDING"
    VALID = "VALID"
    INVALID = "INVALID"

    def __str__(self):
        return self.value
