from dataclasses import dataclass

@dataclass
class CreateModerationRequest(object):
    email: str
    password: str