import json
import requests
import requests.sessions as sessions

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from backupctl.models.notification.notification import Event
from backupctl.models.notification.webhook import HttpRequest, Webhook, WebhookStatus
from backupctl.utils.dataclass import DictConfiguration, dataclass_from_dict

@dataclass
class DiscordPayload(DictConfiguration):
    content     : str                   # the message contents (up to 2000 characters)
    username    : str                   # override the default username of the webhook
    avatar_url  : Optional[str] = None  # override the default avatar of the webhook
    tts         : bool = False          # true if this is a TTS message

@dataclass
class DiscordMessage(DictConfiguration):
    id_        : str      # The Id of the message
    author     : str      # The author of the message
    timestamp  : datetime # The timestamp of the message
    pinned     : bool     # If the message is pinned
    webhook_id : str      # The Id of the webhook

class DiscordWebhook( Webhook ):
    """ Webhook specialized for discord """
    CHANNEL_MESSAGES_URL: str = "https://discord.com/api/channels/{}/messages/pins"
    CHANNEL_PIN_URL: str = CHANNEL_MESSAGES_URL + "/{}"

    def __init__( self, event: Event, **kwargs ):
        super().__init__( event, **kwargs )
    
    def format_request(self, subject: str, attachments: List[Path] | None) -> HttpRequest: 
        """ Format an http POST request for Discord """
        payload = DiscordPayload(content=self.get_content(subject), username="webhook-bot")

        # If there are no attachments we need to send a simple request
        if attachments is None or len(attachments) == 0:
            return HttpRequest( 'POST', self.url, headers=self.headers, json=payload.asdict(), params={ "wait" : True } )
        
        # Otherwise we need to format the multipart/form-data HTTP Body
        payload_json = json.dumps(payload.asdict())
        files = {"payload_json": (None, payload_json, "application/json")}
        for idx, attachment in enumerate(attachments):
            key = f"files[{idx}]" # The file key as expected by discord
            files[key] = ( attachment.name, attachment.open('rb'), "text/plain" )

        return HttpRequest( 'POST', self.url, headers=self.headers, files=files, params={ "wait" : True } )
    
    def _get_pinned_message(self, webhook_id: str, channel_id: str) -> DiscordMessage | None:
        """ Get the last pinned message """
        f_url = self.CHANNEL_MESSAGES_URL.format( channel_id )
        response = requests.get( f_url, headers=self.headers, params={'limit': 10} )
        if not response.ok: response.raise_for_status()

        try:
            response_data = response.json()
            for message in response_data.get('items'):
                message_data = message.get('message')
                if message_data["webhook_id"] != webhook_id: continue
                return dataclass_from_dict( DiscordMessage, message_data )

        except Exception: ...

        return None
    
    def _pin_message( self, channel_id: str, message_id: str, unpin: bool = False ) -> None:
        """ pin/unpin a message given the channel id and message id """
        f_url = self.CHANNEL_PIN_URL.format( channel_id, message_id )
        r_method = 'PUT' if not unpin else 'DELETE'
        request = HttpRequest( r_method, f_url, headers=self.headers )

        with sessions.Session() as session:
            reqp = session.prepare_request( request )
            response = session.send( reqp, allow_redirects=True )
            response.raise_for_status()

    def send( self, subject: str, attachments: List[Path] | None ) -> WebhookStatus:
        """ Discord specialized send follow-up: pin and unpin messages """
        # First call the parent send function
        status = super().send( subject, attachments )
        if status.error is not None: return status

        # Otherwise, if there was no error we can step further
        response = status.response # Take the last response
        try:
            response_data = response.json()
            channel_id = response_data.get( 'channel_id' )
            webhook_id = response_data.get( 'webhook_id' )
            message_id = response_data.get( 'id' )

            # Get the pinned message corresponding to the webhook_id
            pinned_msg = self._get_pinned_message( webhook_id, channel_id )
            if pinned_msg is not None: self._pin_message( channel_id, pinned_msg.id_, True )

            # After the message has been unpinned we need to pin the new one
            self._pin_message( channel_id, message_id )

        except Exception as e:
            print(f"Error {e}")

        return status