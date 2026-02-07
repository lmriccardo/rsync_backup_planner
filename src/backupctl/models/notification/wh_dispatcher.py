from dataclasses import dataclass
from typing import ClassVar

from backupctl.models.notification.discord import DiscordWebhook
from backupctl.models.notification.notification import Event, NotifType
from backupctl.models.notification.webhook import Webhook, WebhookNotification


@dataclass(frozen=True, init=False)
class WebhookDispatcher:
    WEBHOOK_MAPPING: ClassVar[dict[NotifType, type[Webhook]]] = \
    {
        NotifType.discord: DiscordWebhook
    }

    @staticmethod
    def dispatch(
        ntfy: WebhookNotification, event: Event 
    ) -> Webhook:
        return WebhookDispatcher\
            .WEBHOOK_MAPPING[ ntfy.webhook_type ]\
            .new( ntfy, event )