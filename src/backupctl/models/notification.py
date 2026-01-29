from enum import Enum

class NotifType(str, Enum):
    discord = "discord"

class EventType(str, Enum):
    on_success = "success"
    on_failure = "failure"