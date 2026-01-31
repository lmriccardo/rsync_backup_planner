import subprocess
import sys

from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from backupctl.models.plan_config import PlanCfg, load_plan_configuration
from backupctl.constants import DEFAULT_PLAN_CONF_FOLDER, DEFAULT_PLAN_SUFFIX
from backupctl.models.notification import NotificationCls, Event, EventType
from backupctl.models.notification.email import EmailNotification, Emailer
from backupctl.models.notification.webhook import WebhookNotification
from backupctl.models.notification.wh_dispatcher import WebhookDispatcher

def make_log_file(conf: PlanCfg, suffix: str = ".log") -> Path:
    """ Create the log file into the input base folder """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_dir = Path(conf.log)
    log_file = base_dir / f"{conf.name}-{ts}{suffix}"
    base_dir.mkdir(parents=True, exist_ok=True)
    log_file.touch(exist_ok=True)
    return log_file

def run_backup_command( command: List[str], log_file: Path | None ) -> Tuple[bool, str]:
    started = datetime.now()

    try:

        log = sys.stdout if not log_file else log_file.open("w", encoding="utf-8")
        log.write(f"Started : {started.isoformat()}\n")
        log.write(f"Command : {" ".join(command)}\n\n")

        out = subprocess.run(command, capture_output=True, text=True, check=False)
        log.write("----- STDOUT -----\n")
        log.write(str(out.stdout))
        log.write("\n")
        log.write("----- STDERR -----\n")
        log.write(str(out.stderr))
        log.write("\n")
        log.write("----- END STDERR -----\n")
        
        return_code = out.returncode
        finished = datetime.now()
        duration = finished - started

        log.write(f"Finished : {datetime.now().isoformat()}\n")
        log.write(f"Duration : {duration}\n")
        log.write(f"Exit code: {return_code}\n")
        log.flush()

        if log_file is not None: log.close()

        ok = out.returncode == 0

        summary = (
            f"{'✅ SUCCESS' if ok else '❌ FAILED'}\n"
            f"Command : {" ".join(command)}\n"
            f"Started : {started}\n"
            f"Finished: {finished}\n"
            f"Duration: {duration}\n"
            f"Exit    : {return_code}\n"
            f"Log file: {log_file}"
        )

        if out.stderr:
            summary += "\n\n--- STDERR ---\n"
            summary += out.stderr.strip()
        
        return ok, summary
        
    except Exception as e:
        return False, (
                "❌ BACKUP ERROR (exception)\n"
                f"Command  : {command}\n"
                f"Error    : {type(e).__name__}: {e}"
            )
    
def send_notification( 
    notification_cfg: List[NotificationCls], event: Event, log_file: Path | None
) -> None:
    """ Sends notifications """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"[Backup: {event.name}] {'OK' if event.ok() else 'FAILED'} ({now})"
    attachments=[log_file] if log_file is not None else []

    emailer_ = None
    notification_failures = dict()

    for notification_system in notification_cfg:
        if isinstance(notification_system, WebhookNotification):
            if event.event not in notification_system.events: continue
            
            ntfy_name = notification_system.name
            error = WebhookDispatcher.dispatch( notification_system, event ) \
                                     .send( subject, attachments )
            
            notification_failures[ ntfy_name ] = error

        if isinstance(notification_system, EmailNotification):
            emailer_ = Emailer.new(notification_system, event)

    # If the dictionary is not empty we need to report notification
    # failures into the log file
    if log_file is not None and len(notification_failures) > 0:
        log = sys.stdout if not log_file else log_file.open("+a", encoding="utf-8")
        log.write("\n---------- NOTIFICATION SYSTEM FAILURES ----------\n")
        
        # Log all the notification errors
        for name, message in notification_failures.items():
            log.write(f"[NOTIFICATION SYS: {name}] Failed with message: {message}")
        
        log.flush()

        # Close the stream if the iostream was a file
        if log_file is not None: log.close()
    
    # Emails are sent at the end also reporting errors in the log
    # file with any previous notification system failed
    emailer_.send( subject, attachments )

def run_job( 
    target: str, dry_run: bool, notification_en: bool, logging_en: bool 
) -> None:
    """ Run the job associated to the input target. If notifications
    are enabled then the notification system is triggered. The
    dry-run flag performes a local uneffective run, meaning that
    files are not copied to the remote location. """

    # First we need to load the configuration file into the Plan
    target_conf_path = DEFAULT_PLAN_CONF_FOLDER / f"{target}{DEFAULT_PLAN_SUFFIX}"
    plan_configuration = load_plan_configuration( target_conf_path )

    # Create the log file if logging is enabled
    file_log_path = None if not logging_en else \
        make_log_file(plan_configuration)

    # Run the backup command, or the generic task
    # If the dry-run flag is used then we need to add the
    # corresponding option into the list of commands
    if dry_run: plan_configuration.command.insert(-2, "--dry-run")
    print("[*] Running the job ...")
    ok, summary = run_backup_command( plan_configuration.command, file_log_path )
    event_type = EventType.on_success if ok else EventType.on_failure
    event = Event( plan_configuration.name, event_type, summary )

    if notification_en:
        print("[*] Sending notifications")
        notification_list = plan_configuration.notification
        send_notification(notification_list, event, file_log_path)
        return
    
    # If notifications are disabled then printout content on screeen
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"[Backup: {event.name}] {'OK' if event.ok() else 'FAILED'} ({now})"
    
    print()
    print("-" * 100)
    print(subject)
    print("-" * 100, end="\n\n")
    print(event.summary)
