import os
import shutil
import stat


def remove_dir(path):
    """Remove directory and handle read-only files on Windows."""

    def _onerror(func, target, exc_info):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except Exception:
            pass

    if os.path.isdir(path):
        shutil.rmtree(path, onerror=_onerror)


def is_file_locked(path):
    """Check if a file is locked by attempting to acquire an exclusive lock."""
    try:
        if os.name == "nt":
            import msvcrt
            with open(path, "r+") as fh:
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    return True
        else:
            import fcntl
            with open(path, "r+") as fh:
                try:
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(fh, fcntl.LOCK_UN)
                except OSError:
                    return True
    except Exception:
        return True
    return False
