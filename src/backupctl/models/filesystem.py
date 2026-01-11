import os, pwd, grp, stat

from typing import NamedTuple, Optional
from pathlib import Path

class UserStat(NamedTuple):
    """ User Id and Group Id of the user """
    uid: int    # The User Id
    name: str   # The name of the user
    gid: int    # The Group Id of the user
    gname: str  # The Group name of the user

class FolderStat(NamedTuple):
    """ Collection of folder stat """
    path:  Path # The folder absolute path
    owner: UserStat # Stat of the folder owner
    perms: str # String description of the permissions
    mode: int # Octet description of the permissions

def get_user_stat( folder: Optional[Path] = None ) -> UserStat:
    """ Load the user stat of an input path (folder/file) """
    uid, gid = os.getuid(), os.getgid()
    if folder is not None:
        stat = folder.stat()
        uid, gid = stat.st_uid, stat.st_gid

    username = pwd.getpwuid(uid).pw_name
    groupname = grp.getgrgid(gid).gr_name
    return UserStat( uid, username, gid, groupname )

def get_folder_stat( path: str | Path ) -> FolderStat:
    """ Load the entire folder stat of an input path folder """
    folder_path = (Path(path) if isinstance(path, str) else path).absolute()
    folder_stat = folder_path.stat()
    folder_mode = oct(stat.S_IMODE(folder_stat.st_mode))
    return FolderStat( folder_path, get_user_stat(folder_path), 
        stat.filemode(folder_stat.st_mode), folder_mode)

def print_permission_error( path: Path, with_parent: bool=False ):
    print(f"[ERORR] Permission Error when accessing/creating {path}: ")
    f_stat = get_folder_stat( path if not with_parent else path.parent )
    u_stat = get_user_stat()

    print("[ERORR] Target directory:")
    print(f"    Path       : {f_stat.path}")
    print(f"    Owner      : {f_stat.owner.name} (uid={f_stat.owner.uid})")
    print(f"    Group      : {f_stat.owner.gname} (gid={f_stat.owner.gid})")
    print(f"    Permissions: {f_stat.perms} ({f_stat.mode})")

    print()
    print("[ERROR] Current user:")
    print(f"    User       : {u_stat.name} (uid={u_stat.uid})")
    print(f"    Group      : {u_stat.gname} (gid={u_stat.gid})")