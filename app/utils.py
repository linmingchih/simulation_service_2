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
