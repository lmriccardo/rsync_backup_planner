import os
from pathlib import Path
from enum import Enum

CURR_PATH                = Path(os.getcwd()).absolute()
HOME_PATH                = Path.home().absolute()
DEFAULT_BACKUP_FOLDER    = HOME_PATH / ".backups"
DEFAULT_EXCLUDE_FOLDER   = DEFAULT_BACKUP_FOLDER / "rsync-exclude"
DEFAULT_LOG_FOLDER       = DEFAULT_BACKUP_FOLDER / "log"
DEFAULT_PLAN_CONF_FOLDER = DEFAULT_BACKUP_FOLDER / "plans"
DEFAULT_PLAN_SUFFIX      = "-plan.json"
BACKUPCTL_RUN_COMMAND    = "/usr/local/bin/backupctl"
REGISTERED_JOBS_FILE     = DEFAULT_BACKUP_FOLDER / "REGISTRY"
CRONTAB_TAG_PREFIX       = "#backupctl:"
RELEASE_API_URL          = "https://pypi.org/simple/backupctl/"

SMTP_PROVIDERS = {
    "gmail.com":  ("smtp.gmail.com", 587, False),
    "outlook.com": ("smtp.office365.com", 587, False),
    "yahoo.com":  ("smtp.mail.yahoo.com", 465, True),
    "icloud.com": ("smtp.mail.me.com", 587, False),
}

AVAILABLE_WEBHOOKS = {
    "discord" : "https://discord.com/api/webhooks/" # The discord webhook prefix
}

WEEKDAY_NAMES = {
    "0": "Sunday",
    "1": "Monday",
    "2": "Tuesday",
    "3": "Wednesday",
    "4": "Thursday",
    "5": "Friday",
    "6": "Saturday",
    "7": "Sunday",
}

MONTH_NAMES = {
    "1": "January",
    "2": "February",
    "3": "March",
    "4": "April",
    "5": "May",
    "6": "June",
    "7": "July",
    "8": "August",
    "9": "September",
    "10": "October",
    "11": "November",
    "12": "December",
}

COMMON_4XX_STATUS_CODE = {
    400: "Webhook endpoint rejected the request (400 Bad Request)",
    401: "Webhook endpoint requires authentication (401 Unauthorized)",
    403: "Webhook endpoint denied access (403 Forbidden)",
    404: "Webhook endpoint not found (404)",
    408: "Webhook endpoint request timed out (408)"
}

HTTP_RETRY_STATUS = {408, 429, 500, 502, 503, 504}