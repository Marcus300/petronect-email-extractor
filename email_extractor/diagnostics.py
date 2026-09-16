from __future__ import annotations

from datetime import datetime
import locale
import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path


def runtime_metadata() -> list[str]:
    """Return portable, non-secret runtime information useful for support."""
    executable = Path(sys.executable)
    return [
        f"timestamp={datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"app_frozen={bool(getattr(sys, 'frozen', False))}",
        f"app_executable={executable}",
        f"app_directory={executable.parent}",
        f"working_directory={Path.cwd()}",
        f"python={sys.version.replace(os.linesep, ' ')}",
        f"platform={platform.platform()}",
        f"machine={platform.machine()}",
        f"architecture={platform.architecture()[0]}",
        f"locale={locale.getlocale()}",
        f"filesystem_encoding={sys.getfilesystemencoding()}",
        f"temp_directory={Path(tempfile.gettempdir())}",
    ]


def format_exception(exc: BaseException) -> str:
    """Format an exception including its chained cause and traceback."""
    return "".join(traceback.TracebackException.from_exception(exc).format()).rstrip()


def emergency_log_path() -> Path:
    """Use a user-writable directory even when the executable is read-only."""
    base = os.getenv("LOCALAPPDATA") or tempfile.gettempdir()
    directory = Path(base) / "PetronectEmailExtractor" / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"startup_{datetime.now():%Y%m%d_%H%M%S}.log"


def write_emergency_log(exc: BaseException) -> Path:
    path = emergency_log_path()
    lines = ["=== FALHA NA INICIALIZAÇÃO ===", *runtime_metadata(), "", format_exception(exc)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
