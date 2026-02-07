import subprocess
import sys
import os

from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple
from zipfile import ZipFile, ZIP_DEFLATED

from backupctl.models.plan_config import PlanCfg, load_plan_configuration, LogCfg
from backupctl.constants import DEFAULT_PLAN_CONF_FOLDER, DEFAULT_PLAN_SUFFIX
from backupctl.models.notification import NotificationCls, Event, EventType
from backupctl.models.notification.email import EmailNotification, Emailer
from backupctl.models.notification.webhook import WebhookNotification
from backupctl.models.notification.wh_dispatcher import WebhookDispatcher
from backupctl.utils.console import cinfo

def make_log_file(conf: PlanCfg, suffix: str = ".log") -> Path:
    """ Create the log file into the input base folder """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_dir = Path(conf.log.path)
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
            status = WebhookDispatcher.dispatch( notification_system, event ) \
                                      .send( subject, attachments )
            
            # Save the error only if it is an actual string
            if status.error is not None:
                notification_failures[ ntfy_name ] = status.error

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
    if emailer_ is not None: 
        emailer_.send( subject, attachments )

def make_zip_archive( log_file_group: List[Tuple[Path, datetime]] ) -> None:
    """ Create a .zip archive composed of the files gave as a input
    to this function. The name of the zip archive is the start and stop
    range datetime of the most recent and least recent file. """
    first_datetime = log_file_group[0][-1].strftime("%Y%m%d")
    last_datetime  = log_file_group[-1][-1].strftime("%Y%m%d")
    log_folder = log_file_group[0][0].parent
    archive_file = log_folder / f"log_archive-{first_datetime}-{last_datetime}.zip"
    
    with ZipFile( archive_file, "w", compression=ZIP_DEFLATED ) as zipf:
        for ( log_file, _ ) in log_file_group:
            zipf.write( log_file )
            log_file.unlink( missing_ok=True )

def apply_log_retention( logging_en: bool, log_file: Path | None, retention_cfg: LogCfg ) -> None:
    """ Apply log retention policy if necessary """
    if not logging_en: return # do no perform anything if log was not enabled
    cinfo("[*] Applying log retention policy")

    log_folder_path = log_file.parent
    previous_log_files, log_archives = [], []

    for curr_log_file in os.listdir( log_folder_path ):
        path = log_folder_path / curr_log_file
        
        # Search only for log files created previously. Ignore
        # the one that has been created with the most recent run
        if path.stem == log_file.stem: continue
        if path.name.endswith( '.zip' ): log_archives.append( path )
        elif path.name.endswith( '.log' ):
            date_string = '-'.join( path.stem.split('-')[-2:] )
            log_file_date = datetime.strptime( date_string, "%Y%m%d-%H%M%S" )
            previous_log_files.append( ( path, log_file_date ) )

    # Sort all log the logfiles in ascending order based on their timestamp.
    # For each group of files ( which dimension is defined by the retention
    # policy ) creates a corresponding zip archive.
    if len( previous_log_files ) >= retention_cfg.max_spare_files:
        previous_log_files = sorted(previous_log_files, key=lambda x: x[-1])
        previous_index, curr_size = 0, len( previous_log_files )
        while curr_size >= retention_cfg.max_spare_files:
            next_index = previous_index + retention_cfg.max_spare_files
            log_file_group = previous_log_files[previous_index:next_index]
            make_zip_archive( log_file_group )
            previous_index = next_index
            curr_size -= retention_cfg.max_spare_files

    # Next step of the retention policy is to remove zip archives
    # that has exceeded the maximum retention time
    if len(log_archives) == 0: return

    now = date.today() # Take the current time for computing delta days
    for archive_file in log_archives:
        archive_last_date_str = archive_file.stem.split('-')[-1]
        archive_last_date = datetime.strptime(archive_last_date_str, "%Y%m%d").date()
        days_passed = ( now - archive_last_date ).days
        if days_passed >= retention_cfg.retention_window:
            archive_file.unlink(missing_ok=True)

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

    # Run the backup command, or the generic task If the dry-run flag is used then 
    # we need to add the corresponding option into the list of commands
    if dry_run: plan_configuration.command.insert(-2, "--dry-run")
    
    cinfo("[*] Running the job ...")
    ok, summary = run_backup_command( plan_configuration.command, file_log_path )
    apply_log_retention( logging_en, file_log_path, plan_configuration.log )
    
    event_type = EventType.on_success if ok else EventType.on_failure
    event = Event( plan_configuration.name, event_type, summary )

    if notification_en:
        cinfo("[*] Sending notifications")
        notification_list = plan_configuration.notification
        send_notification(notification_list, event, file_log_path)
        return
    
    # If notifications are disabled then printout content on screeen
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"[Backup: {event.name}] {'OK' if event.ok() else 'FAILED'} ({now})"
    
    cinfo("")
    cinfo("-" * 100)
    cinfo(subject)
    cinfo("-" * 100, end="\n\n")
    cinfo(event.summary)
