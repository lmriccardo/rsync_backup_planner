import json

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

from backupctl.models.notification.notification import Event
from backupctl.models.notification.webhook import HttpRequest, Webhook
from backupctl.utils.dataclass import DictConfiguration

@dataclass
class DiscordPayload(DictConfiguration):
    content     : str                   # the message contents (up to 2000 characters)
    username    : str                   # override the default username of the webhook
    avatar_url  : Optional[str] = None  # override the default avatar of the webhook
    tts         : bool = False          # true if this is a TTS message

class DiscordWebhook( Webhook ):
    """ Webhook specialized for discord """
    def __init__( self, event: Event, **kwargs ):
        super().__init__( event, **kwargs )
    
    def format_request(self, subject: str, attachments: List[Path] | None) -> HttpRequest: 
        """ Format an http POST request for Discord """
        payload = DiscordPayload(content=self.get_content(subject), username="webhook-bot")

        # If there are no attachments we need to send a simple request
        if attachments is None or len(attachments) == 0:
            return HttpRequest( 'POST', self.url, headers=self.headers, json=payload.asdict() )
        
        # Otherwise we need to format the multipart/form-data HTTP Body
        payload_json = json.dumps(payload.asdict())
        files = {"payload_json": (None, payload_json, "application/json")}
        for idx, attachment in enumerate(attachments):
            key = f"files[{idx}]" # The file key as expected by discord
            files[key] = ( attachment.name, attachment.open('rb'), "text/plain" )

        return HttpRequest( 'POST', self.url, headers=self.headers, files=files )