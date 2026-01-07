import subprocess
import smtplib
import ssl
import json
import sys

from email.message import EmailMessage
from datetime import datetime
from pathlib import Path
from typing import List

def read_json_plan( plan_path ):
    return json.load(open(
        plan_path, mode='r', encoding='utf-8'
    ))

def make_log_file(base_dir: str, prefix: str, suffix: str = ".log") -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_dir = Path(base_dir)
    log_file = base_dir / f"{prefix}-{ts}{suffix}"
    base_dir.mkdir(parents=True, exist_ok=True)
    log_file.touch(exist_ok=True)
    return log_file

def run_backup( command, log_file: Path ):
    started = datetime.now()

    try:

        log = log_file.open("w", encoding="utf-8")
        log.write(f"Started : {started.isoformat()}\n")
        log.write(f"Command : {" ".join(command)}\n\n")
        
        out = subprocess.run(command, capture_output=True, text=True, check=False)
        log.write("----- STDOUT -----\n")
        log.write(str(out.stdout))
        log.write("\n")
        
        return_code = out.returncode
        finished = datetime.now()
        duration = finished - started

        log.write(f"Finished : {datetime.now().isoformat()}\n")
        log.write(f"Duration : {duration}\n")
        log.write(f"Exit code: {return_code}\n")
        log.close()

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
    
def send_email_smtp(
    config, subject: str, body: str, attachments: List[Path] = []
) -> None:
    msg = EmailMessage()
    msg["From"] = config["from"]
    msg["To"] = config["to"]
    msg["Subject"] = subject
    msg.set_content(body)

    for attachment in attachments:
        data = attachment.read_bytes()
        msg.add_attachment( data, maintype="application", 
            subtype="octet-stream", filename=attachment.name)
        
    ctx = ssl.create_default_context()
        
    if config["ssl"]:
        server = smtplib.SMTP_SSL(config["server"], config["port"], context=ctx)
    else:
        server = smtplib.SMTP(config["server"], config["port"])
        server.starttls(context=ctx)

    with server:
        server.login(config["from"], config["password"])
        server.send_message(msg)

def send_notification( notification_cfg, title, summary, log_file ):
    for notification_system in notification_cfg:
        if notification_system['type'] == 'email':
            send_email_smtp(notification_system,subject=title,
                body=summary,attachments=[log_file])
            
            continue

        # Otherwise it is using webhooks

def main():
    if len(sys.argv) < 2:
        raise RuntimeError("Missing JSON plan configuration")
    
    json_plan = sys.argv[1]
    plan = read_json_plan( json_plan )
    log_file = make_log_file( plan["log"], plan["name"] )
    ok, summary = run_backup( plan["command"], log_file )

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = plan["name"]
    subject = f"[Backup: {name}] {'OK' if ok else 'FAILED'} ({now})"

    send_notification( plan["notification"], subject, summary, log_file )

if __name__ == "__main__":
    main()