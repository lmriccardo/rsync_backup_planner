from .notification import *
from typing import TypeAlias, Union
from .webhook import WebhookNotification
from .email import EmailNotification

NotificationCls: TypeAlias = Union[
    EmailNotification,
    WebhookNotification
]