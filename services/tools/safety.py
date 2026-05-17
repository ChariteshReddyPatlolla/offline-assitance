"""
Safety guard module — identifies protected paths and dangerous commands.
All matched actions MUST go through require_approval before executing.
"""
import os
import re
from typing import Optional

# Windows system paths that must never be modified without approval
PROTECTED_PATHS = [
    os.environ.get("SystemRoot", "C:\\Windows"),
    os.environ.get("ProgramFiles", "C:\\Program Files"),
    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
    os.environ.get("USERPROFILE", ""),          # user root (not subdirs)
    "C:\\System32",
    "C:\\Windows",
    "C:\\Boot",
    "C:\\Recovery",
]

# Dangerous shell command patterns
DANGEROUS_PATTERNS = [
    r"\brm\b",
    r"\bdel\b",
    r"\brmdir\b",
    r"\brd\b",              # Windows rd /s /q
    r"\bformat\b",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\breg\s+(add|delete|import)",   # Registry edits
    r"\bregsvr32\b",
    r"\bnetsh\b",
    r"\bsfc\b",
    r"\bdiskpart\b",
    r"\bcacls\b",
    r"\bicacls\b",
    r"\btaskkill\b",
    r"\bpowershell.*-executionpolicy\s+bypass",
    r"\bpip\s+uninstall",
    r"\bchoco\s+uninstall",
    r"\bwmic\b",
    r"Remove-Item",
    r"Stop-Process",
    r"Clear-RecycleBin",
    r"Format-Volume",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


def is_protected_path(path: str) -> bool:
    """
    Returns True if the given path falls under a protected system directory.
    """
    try:
        abs_path = os.path.abspath(path).lower()
        # User profile root (but allow subdirs like Documents, Downloads)
        userprofile = os.environ.get("USERPROFILE", "").lower()
        if userprofile and abs_path == userprofile:
            return True
        for protected in PROTECTED_PATHS:
            if not protected:
                continue
            if abs_path.startswith(protected.lower()):
                return True
    except Exception:
        pass
    return False


def is_dangerous_command(command: str) -> bool:
    """
    Returns True if the command matches any dangerous shell pattern.
    """
    for pattern in _COMPILED:
        if pattern.search(command):
            return True
    return False


def get_safety_warning(command: str) -> Optional[str]:
    """
    Returns a human-readable warning string if the command is dangerous,
    or None if the command is safe.
    """
    for pat_str, pattern in zip(DANGEROUS_PATTERNS, _COMPILED):
        if pattern.search(command):
            return f"⚠️ Potentially destructive command detected (matched: `{pat_str}`)"
    return None
