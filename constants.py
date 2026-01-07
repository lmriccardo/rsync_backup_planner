import os
from pathlib import Path

CURR_PATH                = Path(os.getcwd()).absolute()
HOME_PATH                = Path.home().absolute()
DEFAULT_BACKUP_FOLDER    = HOME_PATH / ".backups"
DEFAULT_EXCLUDE_FOLDER   = DEFAULT_BACKUP_FOLDER / "rsync-exclude"
DEFAULT_LOG_FOLDER       = DEFAULT_BACKUP_FOLDER / "log"
DEFAULT_PLAN_CONF_FOLDER = DEFAULT_BACKUP_FOLDER / "plans"