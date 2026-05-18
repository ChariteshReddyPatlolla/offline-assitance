"""
Safety guard module — identifies protected paths and dangerous commands.
Use this module to decide whether a tool action should require user approval.

Policy:
- ALL shell commands require approval (default-secure behavior).
- File writes/deletes require approval only for protected paths.
- Dangerous commands are flagged with stronger warnings.
"""

import os
import re
from typing import Optional

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

USERPROFILE = os.environ.get("USERPROFILE", "")

# Safe user folders where file modifications are allowed without approval.
SAFE_USER_FOLDERS = [
    os.path.join(USERPROFILE, "Desktop"),
    os.path.join(USERPROFILE, "Documents"),
    os.path.join(USERPROFILE, "Downloads"),
    os.path.join(USERPROFILE, "Pictures"),
    os.path.join(USERPROFILE, "Videos"),
    os.path.join(USERPROFILE, "Music"),
]

# Protected system directories.
PROTECTED_PATHS = [
    os.environ.get("SystemRoot", r"C:\Windows"),
    os.environ.get("ProgramFiles", r"C:\Program Files"),
    os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    r"C:\System32",
    r"C:\Windows",
    r"C:\Boot",
    r"C:\Recovery",
    r"C:\ProgramData",
]

# High-risk file extensions.
HIGH_RISK_EXTENSIONS = {
    ".exe",
    ".dll",
    ".sys",
    ".bat",
    ".cmd",
    ".ps1",
    ".reg",
    ".msi",
    ".vbs",
    ".js",
    ".jar",
}

# ============================================================================
# DANGEROUS COMMAND PATTERNS
# ============================================================================

DANGEROUS_PATTERNS = [
    # File deletion
    r"\brm\b",
    r"\bdel\b",
    r"\berase\b",
    r"\brmdir\b",
    r"\brd\b",

    # Formatting / partitions
    r"\bformat\b",
    r"\bdiskpart\b",
    r"\bFormat-Volume\b",

    # Shutdown / reboot
    r"\bshutdown\b",
    r"\brestart\b",

    # Registry
    r"\breg\s+(add|delete|import)",
    r"\bregsvr32\b",

    # Networking / firewall
    r"\bnetsh\b",

    # Permissions / repair
    r"\bsfc\b",
    r"\bcacls\b",
    r"\bicacls\b",

    # Process control
    r"\btaskkill\b",
    r"\bStop-Process\b",

    # PowerShell destructive commands
    r"\bRemove-Item\b",
    r"\bClear-RecycleBin\b",

    # Execution policy bypass
    r"\bpowershell.*-executionpolicy\s+bypass",

    # Package removal
    r"\bpip\s+uninstall\b",
    r"\bchoco\s+uninstall\b",
    r"\bnpm\s+uninstall\b",

    # Service control
    r"\bsc\s+(create|delete|config|stop|start)\b",

    # Git destructive
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-fd\b",
]

_COMPILED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in DANGEROUS_PATTERNS
]

# Commands that are generally safe and still require approval only because they
# can affect the local machine. This list is useful for tailoring messages.
COMMON_SAFE_COMMANDS = [
    "dir",
    "ls",
    "pwd",
    "echo",
    "python --version",
    "pip install",
    "npm install",
    "git status",
]


# ============================================================================
# PATH HELPERS
# ============================================================================

def normalize_path(path: str) -> str:
    """
    Normalize a path for comparison.
    """
    return os.path.abspath(os.path.expandvars(path)).lower()


def is_safe_user_folder(path: str) -> bool:
    """
    Returns True if the path is inside a common user folder.
    """
    try:
        abs_path = normalize_path(path)

        for folder in SAFE_USER_FOLDERS:
            if folder and abs_path.startswith(normalize_path(folder)):
                return True
    except Exception:
        pass

    return False


def is_protected_path(path: str) -> bool:
    """
    Returns True if a path is considered system-critical.
    """
    try:
        abs_path = normalize_path(path)

        # Common user folders are allowed.
        if is_safe_user_folder(abs_path):
            return False

        # Root profile directory requires approval.
        if USERPROFILE and abs_path == normalize_path(USERPROFILE):
            return True

        # System directories.
        for protected in PROTECTED_PATHS:
            if protected and abs_path.startswith(normalize_path(protected)):
                return True

        # Executables/scripts anywhere require approval.
        _, ext = os.path.splitext(abs_path)
        if ext.lower() in HIGH_RISK_EXTENSIONS:
            return True

    except Exception:
        pass

    return False


# ============================================================================
# COMMAND ANALYSIS
# ============================================================================

def is_dangerous_command(command: str) -> bool:
    """
    Returns True if the command matches a high-risk pattern.
    """
    if not command:
        return False

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(command):
            return True

    return False


def get_safety_warning(command: str) -> Optional[str]:
    """
    Returns a human-readable warning if the command is dangerous.
    """
    if not command:
        return None

    for pattern_text, pattern in zip(
        DANGEROUS_PATTERNS,
        _COMPILED_PATTERNS,
    ):
        if pattern.search(command):
            return (
                "⚠️ Potentially destructive command detected "
                f"(matched pattern: `{pattern_text}`)"
            )

    return None


# ============================================================================
# APPROVAL POLICY
# ============================================================================

def should_require_shell_approval(command: str) -> bool:
    """
    Returns True if this shell command should require approval.

    Current production policy:
    - Every shell command requires approval.

    Why:
    Even seemingly harmless commands can:
    - Download code
    - Install packages
    - Modify project files
    - Leak sensitive data
    - Chain into dangerous commands

    This function exists so that future policies can be implemented without
    changing tool code.
    """
    if not command or not command.strip():
        return False

    return True


def should_require_path_approval(path: str) -> bool:
    """
    Returns True if writing/deleting this path should require approval.
    """
    return is_protected_path(path)


def should_force_reapproval(command: str) -> bool:
    """
    Returns True if approval must be requested every time,
    even if the user previously approved the same action.

    Dangerous commands should always require fresh approval.
    """
    return is_dangerous_command(command)