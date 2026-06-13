from .shell import run_command

def launch_application(app_name: str, args: str = "") -> bool:
    """
    Launches a desktop application. 
    On Windows, this typically uses 'start'.
    """
    # For a detached launch:
    cmd = f"start {app_name} {args}"
    returncode, _, _ = run_command(cmd)
    return returncode == 0
