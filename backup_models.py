from __future__ import annotations

import croniter
import yaml
import re

from typing import Optional, List, Union, Dict
from pathlib import Path
from pydantic import (
    BaseModel, Field, ConfigDict, EmailStr,
    field_validator, model_validator,
    ValidationError
)

SMTP_PROVIDERS = {
    "gmail.com":  ("smtp.gmail.com", 587, False),
    "outlook.com": ("smtp.office365.com", 587, False),
    "yahoo.com":  ("smtp.mail.yahoo.com", 465, True),
    "icloud.com": ("smtp.mail.me.com", 587, False),
}

CronField = Optional[Union[int,str]]

class RemoteDest(BaseModel):
    module: str # The remote rsync module
    folder: str # The remote folder under the module

class Remote(BaseModel):
    host: str # The remote hostname 
    port: int = Field(default=873, ge=1, le=65535) # The remote port (rsync)
    user: Optional[str] = None # The remote username
    password_file: Optional[str] = None # The password file for non-interactive mode
    dest: RemoteDest # Remote Destination

class RsyncCfg(BaseModel):
    exclude_output_folder: Optional[str] = None
    compress: bool = False # Enable or disable compression before transmitting
    verbose: bool = True # Enable/Disable verbosity
    show_progress: bool = True # Show progress while synching
    exclude_from: Optional[str] = None
    excludes: List[str] = Field(default_factory=list)
    includes: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list, min_length=1)

class Schedule(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    weekday : CronField = None # Range 0-7 (Sun = 0 or 7)
    month   : CronField = None # Range 1-12
    day     : CronField = None # Day of the month Range 1-31
    hour    : CronField = None # Range 0-23
    minute  : CronField = None # Range 0-59

    @field_validator("weekday", "month", "day", "hour", "minute", mode="before")
    @classmethod
    def normalize_fields(cls, field_value) -> str:
        """ Normalize fields to strings for cron validator """
        if field_value is None: return "*"
        if isinstance(field_value, int): return str(field_value)
        if isinstance(field_value, str) and field_value.strip():
            return field_value.strip()
        raise ValueError("must be null, int, or a cron field string")
    
    @model_validator(mode="after")
    def validate_as_cron(self) -> 'Schedule':
        """ Validates the model as a cronstring """
        expr = f"{self.minute} {self.hour} {self.day} {self.month} {self.weekday}"
        
        try:
            croniter.croniter(expr) # This raises if invalid
        except Exception as e:
            raise ValueError(f"Invalid schedule format; cron='{expr}: {e}'")

        return self
    
class SMTP_Cfg(BaseModel):
    server: str
    port: Optional[int] = Field(min=1, max=65535,default=None)
    ssl: bool = False

class EmailCfg(BaseModel):
    model_config = ConfigDict(extra="forbid", populated_by_name=True)

    from_: EmailStr = Field(alias="from") # The sender email
    to: List[EmailStr]
    password: str # The SMTP password for the email
    smtp: Optional[SMTP_Cfg] = None # Optional SMTP server

    @model_validator(mode="after")
    def fill_smtp_defaults(self) -> EmailCfg:
        """ Fills the stmp section with defaults parameter
        from the detected SMTP domain if inferred. """
        if self.smtp is not None: return self
        domain = self.from_.split("@")[-1]
        if domain not in SMTP_PROVIDERS:
            raise ValidationError(
                f"No SMTP defaults for '{domain}'. "
                "Please specify smtp.server and smtp.port explicitly."
            )
        
        server, port, ssl = SMTP_PROVIDERS[domain]
        self.smtp = SMTP_Cfg(server=server, port=port, ssl=ssl)
        return self

class NotificationCfg(BaseModel):
    email: Optional[EmailCfg] = None # Optional email notification syste

class Target(BaseModel):
    remote: Remote # The remote rsync host
    rsync: RsyncCfg # rsync configuration
    schedule: Schedule # Schedule configuration
    notification: Optional[NotificationCfg]=None # The optional notification system

class BackupCfg(BaseModel):
    exclude_output: Optional[str] = None
    targets: Optional[Dict[str, Target]] = None

class YAML_Conf(BaseModel):
    model_config = ConfigDict(extra="forbid")  # <-- rejects unknown keys
    backup: BackupCfg # Backup configuration for each target

ROOT_SCHEMA_CLASS = YAML_Conf # For Schema generation

def load_configuration( conf_path: Path | str ) -> YAML_Conf:
    """ Load and validate the input configuration """
    if isinstance(conf_path, str):
        conf_path = Path(conf_path).absolute()

    data = yaml.safe_load(open(conf_path, mode='r', encoding='utf-8'))
    return YAML_Conf.model_validate(data)