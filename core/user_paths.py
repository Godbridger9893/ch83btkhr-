import os
import shutil
from pathlib import Path

_LEGACY_DIR_NAME = 'BrahmaAI'


def get_user_data_dir() -> Path:
    app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    d = Path(app_data) / 'CelestiaAI'
    if not d.exists():
        legacy = Path(app_data) / _LEGACY_DIR_NAME
        if legacy.exists():
            # One-time upgrade: carry memory, keys, and workspace forward so
            # existing installs lose nothing when the folder is renamed.
            try:
                shutil.move(str(legacy), str(d))
            except Exception:
                pass
    if not d.exists():
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Last resort: keep running against the legacy folder.
            legacy = Path(app_data) / _LEGACY_DIR_NAME
            legacy.mkdir(parents=True, exist_ok=True)
            return legacy
    return d
