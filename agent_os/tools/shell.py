import subprocess
from typing import Dict, Tuple

def run_command(command: str, cwd: str = ".") -> Tuple[int, str, str]:
    """
    Executes a shell command.
    Returns: (returncode, stdout, stderr)
    """
    result = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr

def process_running(process_name: str) -> bool:
    """Checks if a process is running (Windows specific via tasklist)."""
    returncode, stdout, _ = run_command(f"tasklist /FI \"IMAGENAME eq {process_name}\"")
    return process_name.lower() in stdout.lower()
