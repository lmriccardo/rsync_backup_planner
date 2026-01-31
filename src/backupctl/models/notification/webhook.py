import requests
import requests.sessions as sessions
import time
import re

from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeAlias, Annotated
from dataclasses import dataclass
from pydantic import BaseModel, model_validator, HttpUrl, Field, \
    ConfigDict, computed_field, AfterValidator

from .notification import NotificationType, NotificationMeta, Event, NotifType, EventType
from backupctl.constants import HTTP_RETRY_STATUS, AVAILABLE_WEBHOOKS
from backupctl.utils.dataclass import DictConfiguration, PrintableConfiguration

HttpRequest: TypeAlias = requests.Request

def _validate_timeout_str( v: Optional[str] ) -> Optional[str]:
    """ Validate the timeout string """
    if v is None: return v # None value can be provided
    # This regex, matches scientific notation and time notation
    pattern = re.compile(r"^(\d+)(?:\.(\d+))?(?:e(\d+))?(s|ms|us)$")
    match = re.fullmatch( pattern, v )
    if match is None:
        raise ValueError(f"Incorrect formatting for timeout field {v}")
    return v

def _get_timeout_float_sec( v: Optional[str] ) -> Optional[float]:
    """ Convert the timeout string into a float value """
    if v is None: return None
    pattern = re.compile(r"^(\d+)(?:\.(\d+))?(?:e(\d+))?(s|ms|us)$")
    units, decs, exp, time_unit = pattern.fullmatch( v ).groups()
    result = int(units)
    if decs is not None: result += int( decs ) / ( 10**len(decs) )
    if exp is not None: result *= 10**int(exp)
    result /= ( { "s" : 1, "ms" : 1000, "us": 1e6 }[time_unit] )
    return result

TimeoutField = Annotated[str, AfterValidator(_validate_timeout_str)]

class WebhookCfg(BaseModel):
    model_config = ConfigDict(extra="forbid", 
                              populate_by_name=True, 
                              validate_default=True)
    
    type_       : NotifType = Field(alias="type")               # The type of the webhook endpoint
    name        : str                                           # The name given to the webhook
    url         : HttpUrl                                       # The URL endpoint for the webhook
    events      : List[EventType] = Field(default_factory=list, min_length=1) # List of subscribed events
    timeout     : Optional[TimeoutField] = None                 # Optional timeout for receiving the response
    max_retries : Optional[int] = Field( default=None, ge=0 ) # Maximum number of retries
    headers     : Optional[Dict[str,Any]] = None                # Optional additional headers for the HTTP request

    @model_validator(mode="after")
    def validate( self ) -> 'WebhookCfg':
        """ Validates the webhook notification type """
        if self.type_.value not in AVAILABLE_WEBHOOKS:
            raise ValueError(f"Uknown webhook notification type")
        
        encoded_url = self.url.encoded_string()
        expected_prefix = AVAILABLE_WEBHOOKS[self.type_.value]
        if not encoded_url.startswith( expected_prefix ):
            raise ValueError(
                f"For webhook notification type '{self.type_.value}' " + \
                f"a URL starting with '{expected_prefix}' is expected!"
            )

        return self
    
    @computed_field
    @property
    def timeout_s(self) -> Optional[float]:
        return _get_timeout_float_sec( self.timeout )

@dataclass
class WebhookNotification(NotificationMeta, DictConfiguration, PrintableConfiguration):
    webhook_type: NotifType # The wehbook type system (discord etc)
    name: str # The name of the current webhook
    url: str  # The URL endpoint for the current webhook
    max_retries: int # Maximum number of retries
    events: List[EventType] # List of subscribed events
    timeout_s: Optional[float] = None # Timeout for receiving the response
    headers: Optional[Dict[str, Any]] = None # Additional headers for the HTTP request

    @staticmethod
    def from_configuration( id_: int, notif: WebhookCfg ) -> 'WebhookNotification':
        """ Creates an object from Webhook user configuration """
        return WebhookNotification(
            id=id_, type=NotificationType.webhook, webhook_type=notif.type_,
            name=notif.name, url=notif.url.encoded_string(), events=notif.events, 
            timeout_s=notif.timeout_s, max_retries=notif.max_retries,
            headers=notif.headers
        )
    
class Webhook(ABC, WebhookNotification):
    def __init__( self, event: Event, **kwargs ):
        super().__init__( **kwargs )
        self.event = event

    @classmethod
    def new(cls, ntfy: WebhookNotification, event: Event) -> 'Webhook':
        return cls( event, **ntfy.__dict__ )
    
    def get_content( self, subject: str ) -> str:
        return f"{subject}\n{self.event.summary}"
    
    def send( self, subject: str, attachments: List[Path] | None ) -> str | None:
        """ Creates and sends the requests """
        request = self.format_request( subject, attachments )
        last_error: str | None = None # The error returned by the send function
        session = sessions.Session()
        for attempt in range(1, self.max_retries + 1):
            try:
                prep_req = session.prepare_request( request )
                response = session.send(
                    prep_req, allow_redirects=True, timeout=self.timeout_s
                )
                
                # Wait for the response to arrive. When it is arrived check
                # its status. Some status codes permit retryies, while
                # for some others we shall fail fast
                if response.ok: break
                
                last_error = (
                    f"Webhook request failed with HTTP {response.status_code}: "
                    f"{response.reason}"
                )

                if response.status_code in HTTP_RETRY_STATUS:
                    retry_sleep_time = self.backoff( attempt )
                    if (
                            response.status_code == 429 \
                        and ( ra := response.headers.get("Retry-After") ) is not None
                    ):
                        retry_sleep_time = ra
                    
                    if attempt == self.max_retries: break
                    time.sleep(retry_sleep_time)
                    continue

            except ( requests.Timeout, requests.ConnectionError ) as e:
                last_error = (
                    f"Network error contacting webhook "
                    f"(attempt {attempt}/{self.max_retries}): {e}"
                )

                if attempt == self.max_retries: break
                time.sleep(self.backoff( attempt ))
                continue

            except requests.RequestException as e:
                last_error = f"Unexpected error while sending webhook: {e}"
                break
        
        # Close the session before returning
        session.close()
        return last_error or "Webhook request failed for unknown reason"

    @staticmethod
    def backoff(attempt: int) -> float:
        return min( 2 ** attempt, 30 )

    @abstractmethod
    def format_request( 
        self, subject: str, attachments: List[str] 
    ) -> HttpRequest: 
        """ Format and returns the (endpoint specialized) request """
        ...