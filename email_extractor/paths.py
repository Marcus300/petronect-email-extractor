"""Resolve user-specific writable paths without assuming a Windows language."""

import ctypes
from pathlib import Path
import sys
from uuid import UUID


DEFAULT_EXCEL_FILENAME = "emails_petronect.xlsx"
_DOWNLOADS_FOLDER_ID = UUID("374de290-123f-4565-9164-39c4925e467b")


class _Guid(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_uuid(cls, value: UUID) -> "_Guid":
        return cls(
            value.time_low,
            value.time_mid,
            value.time_hi_version,
            (ctypes.c_ubyte * 8)(*value.bytes[8:]),
        )


def _windows_downloads_folder() -> Path:
    folder_id = _Guid.from_uuid(_DOWNLOADS_FOLDER_ID)
    path_pointer = ctypes.c_wchar_p()
    shell32 = ctypes.windll.shell32
    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(_Guid),
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    result = shell32.SHGetKnownFolderPath(
        ctypes.byref(folder_id), 0, None, ctypes.byref(path_pointer)
    )
    if result != 0 or not path_pointer.value:
        raise OSError(result, "Não foi possível localizar a pasta Downloads do Windows.")
    try:
        return Path(path_pointer.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_pointer)


def downloads_folder() -> Path:
    """Return the current user's Downloads known folder with a portable fallback."""
    if sys.platform == "win32":
        try:
            return _windows_downloads_folder()
        except (AttributeError, OSError):
            pass
    return Path.home() / "Downloads"


def default_excel_path() -> Path:
    return downloads_folder() / DEFAULT_EXCEL_FILENAME
