# این فایل مسیر ویدیو را در ویندوز و Git Bash به‌صورت امن و قابل‌اعتماد resolve می‌کند.
"""Video path resolution (Git Bash / MSYS backslash-safe on Windows)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def patch_sys_argv_from_windows_command_line() -> None:
    """
    Git Bash / MSYS strip or mangle backslashes in argv (e.g. \\Users -> broken path).
    Rebuild argv from the real Windows command line when possible.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        shell32 = ctypes.windll.shell32
        GetCommandLineW = kernel32.GetCommandLineW
        GetCommandLineW.argtypes = []
        GetCommandLineW.restype = wintypes.LPCWSTR
        CommandLineToArgvW = shell32.CommandLineToArgvW
        CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
        CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
        LocalFree = kernel32.LocalFree
        LocalFree.argtypes = [wintypes.HLOCAL]
        LocalFree.restype = wintypes.HLOCAL

        line = GetCommandLineW()
        argc = ctypes.c_int(0)
        argv_ptr = CommandLineToArgvW(line, ctypes.byref(argc))
        if not argv_ptr or argc.value <= 0:
            return
        new_argv = [argv_ptr[i] for i in range(argc.value)]
        LocalFree(argv_ptr)
        if len(new_argv) < 2:
            return
        # CommandLineToArgvW includes the Python exe; argparse uses sys.argv[1:].
        # Keep [script_path, ...user_args] only (same shape as unpatched python main.py ...).
        script_idx = None
        for i, part in enumerate(new_argv):
            lowered = part.lower().replace("\\", "/")
            if lowered.endswith("/main.py") or lowered.endswith("\\main.py") or part == "main.py":
                script_idx = i
                break
        if script_idx is not None:
            sys.argv[:] = [new_argv[script_idx], *new_argv[script_idx + 1 :]]
    except Exception:
        return


def resolve_video_path(video_path: str | os.PathLike[str], *, cwd: Path | None = None) -> Path:
    """
    Resolve a user-supplied path to an existing video file.

    Tries: as given, normalized slashes, then basename under cwd (for broken absolute paths).
    """
    cwd = cwd or Path.cwd()
    raw = os.fspath(video_path).strip().strip('"')

    candidates: list[Path] = []
    p = Path(raw)
    candidates.append(p.expanduser())
    if not p.is_absolute():
        candidates.append((cwd / raw).expanduser())
    norm = Path(raw.replace("\\", "/"))
    if norm not in candidates:
        candidates.append(norm.expanduser())

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved

    basename = Path(raw).name
    if basename and (cwd / basename).is_file():
        return (cwd / basename).resolve()

    raise FileNotFoundError(
        "Video not found. Tried: "
        + ", ".join(str(c) for c in candidates[:3])
        + ". Tip: use forward slashes in Git Bash (e.g. C:/Users/.../v.avi) or quote the path."
    )
