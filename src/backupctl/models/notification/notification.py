from dataclasses import dataclass
from enum import Enum

class NotificationType(str, Enum):
    email   = "email"
    webhook = "webhook"

@dataclass
class NotificationMeta:
    id   : int # The id of the current notification system
    type : NotificationType # The type of the current notification system

class NotifType(str, Enum):
    discord = "discord"

class EventType(str, Enum):
    on_success = "success"
    on_failure = "failure"

@dataclass(frozen=True)
class Event:
    name: str        # The name of the event
    event: EventType # The type of the event
    summary: str     # The event message

    def ok(self) -> bool:
        return self.event == EventType.on_success