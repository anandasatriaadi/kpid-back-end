from enum import Enum


class ModerationStatus(Enum):
    INITIALIZED = "INITIALIZED"
    UPLOADED = "UPLOADED"
    IN_PROGRESS = "IN_PROGRESS"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
