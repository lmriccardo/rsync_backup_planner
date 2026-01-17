from __future__ import annotations

import backupctl.models.user_config as user_cfg
import json

from backupctl.constants import DEFAULT_LOG_FOLDER
from backupctl.utils.rsync import create_rsync_command
from backupctl.utils.dataclass import *
from dataclasses import dataclass, field
from typing import List, TypeAlias, Union, Dict, Any
from pathlib import Path

class NotificationType(str, Enum):
    email   = "email"
    webhook = "webhook"

@dataclass
class NotificationMeta:
    id   : int # The id of the current notification system
    type : NotificationType # The type of the current notification system

@dataclass
class EmailNotification(NotificationMeta, DictConfiguration, PrintableConfiguration):
    from_    : str # The email sender
    password : str # The user password
    server   : str # The server hostname or ip address
    port     : int # The remote port on which the server is listening
    ssl      : bool # If the SMTP server support SSL
    to       : List[str] = field(default_factory=list) # A list of recipients

    @staticmethod
    def from_notification(id_: int, notif: user_cfg.EmailCfg) -> 'EmailNotification':
        """ Creates an object from the Email user configuration """
        return EmailNotification(
            id=id_, type=NotificationType.email,
            from_=notif.from_, to=notif.to,
            password=notif.password, server=notif.smtp.server,
            port=notif.smtp.port, ssl=notif.smtp.ssl
        )

@dataclass
class WebhookNotification(NotificationMeta, DictConfiguration, PrintableConfiguration):
    ...

NotificationCls: TypeAlias = Union[
    EmailNotification,
    WebhookNotification
]

@dataclass
class PlanCfg(DictConfiguration, PrintableConfiguration):
    name         : str # The name of the backup plan
    log          : str # The root log folder for this job
    compression  : bool # Enable/Disable compression
    command      : str # rsync command to run
    notification : List[NotificationCls] = \
        field(default_factory=list) # Notification system config
    
TYPE_DISCRIMINATOR: Dict[str, Any] = \
{
    "email"   : EmailNotification,
    "webhook" : WebhookNotification
}

def load_plan_configuration( conf_path: Path | str ) -> PlanCfg:
    """ Load the json file into the `PlanCfg` dataclass """
    conf_path = conf_path.expanduser().resolve()
    if not conf_path.exists() or not conf_path.is_file():
        raise ValueError(f"File {conf_path} does not exists or is not a file")
    
    with conf_path.open('r', encoding='utf-8') as io:
        data = json.load(io)

    return dataclass_from_dict( PlanCfg, data, TYPE_DISCRIMINATOR )

def load_from_target( target: user_cfg.Target ) -> PlanCfg:
    """ Creats a plan configuration out of a target. Notification
    systems that will be written into the configuration are filtered
    based on the input notification erros mapping if provided. """
    cfg = PlanCfg( None, None, None, None )
    cfg.name = target.name
    cfg.log = (DEFAULT_LOG_FOLDER / target.name).__str__()
    cfg.compression = target.rsync.options.compress

    # Create the rsync command
    password_file = Path(target.remote.password_file).resolve().__str__()
    cfg.command = create_rsync_command(
        host=target.remote.host, port=target.remote.port, user=target.remote.user,
        password_file=password_file, module=target.remote.dest.module, 
        folder=target.remote.dest.folder, list_only=False, 
        progress=target.rsync.options.show_progress, includes=target.rsync.includes,
        verbose=target.rsync.options.verbose, exclude_from=target.rsync.exclude_from, 
        sources=target.rsync.sources, use_flags=True,
        delete=target.rsync.options.delete, 
        itemize_changes=target.rsync.options.itemize_changes
    )

    # Now we need to put only those notification system that
    # successfully have passed the previous checks
    cfg.notification = []
    curr_ns_identifier = 0

    if target.notification.email is not None:
        curr_ns_identifier += 1
        cfg.notification.append(EmailNotification.from_notification(
            curr_ns_identifier, target.notification.email
        ))

    return cfg

def write_plan_configuration(path: Path, conf: PlanCfg) -> None:
    """ Dumps the configuration into a JSON file """
    path.touch(exist_ok=True) # Create the file if it does not exists
    with path.open(mode='w', encoding='utf-8') as io:
        json.dump( conf.asdict(), io, indent=2 )