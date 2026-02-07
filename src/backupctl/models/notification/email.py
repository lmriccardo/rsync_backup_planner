import ssl
import smtplib

from pathlib import Path
from email.message import EmailMessage
from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict, EmailStr

from .notification import NotificationMeta, NotificationType, Event
from backupctl.utils.dataclass import DictConfiguration, PrintableConfiguration
from backupctl.constants import SMTP_PROVIDERS

class SMTP_Cfg(BaseModel):
    server: str
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    ssl: bool = False

class EmailCfg(BaseModel):
    model_config = ConfigDict(extra="forbid", populated_by_name=True)

    from_: EmailStr = Field(alias="from") # The sender email
    to: List[EmailStr]
    password: str # The SMTP password for the email
    smtp: Optional[SMTP_Cfg] = None # Optional SMTP server

    @model_validator(mode="after")
    def fill_smtp_defaults(self) -> 'EmailCfg':
        """ Fills the stmp section with defaults parameter
        from the detected SMTP domain if inferred. """
        if self.smtp is not None: return self
        domain = self.from_.split("@")[-1]
        if domain not in SMTP_PROVIDERS:
            raise ValueError(
                f"No SMTP defaults for '{domain}'. "
                "Please specify smtp.server and smtp.port explicitly."
            )
        
        server, port, ssl = SMTP_PROVIDERS[domain]
        self.smtp = SMTP_Cfg(server=server, port=port, ssl=ssl)
        return self

@dataclass
class EmailNotification(NotificationMeta, DictConfiguration, PrintableConfiguration):
    from_    : str # The email sender
    password : str # The user password
    server   : str # The server hostname or ip address
    port     : int # The remote port on which the server is listening
    ssl      : bool # If the SMTP server support SSL
    to       : List[str] = field(default_factory=list) # A list of recipients

    @staticmethod
    def from_configuration(id_: int, notif: EmailCfg) -> 'EmailNotification':
        """ Creates an object from the Email user configuration """
        return EmailNotification(
            id=id_, type=NotificationType.email, from_=notif.from_, to=notif.to,
            password=notif.password, server=notif.smtp.server,
            port=notif.smtp.port, ssl=notif.smtp.ssl
        )
    
class Emailer(EmailNotification):
    """ Email notification sender """
    def __init__( self, event: Event, **kwargs ):
        super().__init__( **kwargs )
        self.event = event

    @classmethod
    def new(cls, ntfy: EmailNotification, event: Event) -> 'Emailer':
        return cls( event, **ntfy.__dict__ )
    
    def send( self, subject: str, attachments: List[Path] | None ) -> None:
        """ Send the email notification """
        msg = EmailMessage()
        msg["From"] = self.from_
        msg["To"] = self.to
        msg["Subject"] = subject
        msg.set_content(self.event.summary)

        if not attachments is None:
            for attachment in attachments:
                data = attachment.read_bytes()
                msg.add_attachment( data, maintype="application", 
                    subtype="octet-stream", filename=attachment.name)
            
        ctx = ssl.create_default_context()
            
        if self.ssl:
            server = smtplib.SMTP_SSL(self.server, self.port, context=ctx)
        else:
            server = smtplib.SMTP(self.server, self.port)
            server.starttls(context=ctx)

        with server:
            server.login(self.from_, self.password)
            server.send_message(msg)