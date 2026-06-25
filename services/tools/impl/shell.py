import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def execute_shell_command_raw(command: str, cwd: str = None) -> str:
    """Execute a shell command locally in the given working directory."""
    if not command or not command.strip():
        return "❌ No shell command provided."

    command = command.strip()

    # Reject shell command chaining to enforce sequential subcommands
    if any(op in command for op in ["&&", ";", "||", "\n"]):
        return (
            "❌ Shell command chaining is NOT allowed. Please break down the task "
            "and execute only the first immediate subcommand without combining it with other commands."
        )

    try:
        if not cwd or not os.path.isdir(cwd):
            user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
            fallback_desktop = os.path.join(user_profile, "Desktop")
            onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
            if os.path.exists(onedrive_desktop):
                fallback_desktop = onedrive_desktop
            cwd = fallback_desktop

        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL, shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=cwd,
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        sections = []
        if stdout:
            sections.append(stdout)
        if stderr:
            sections.append(f"Errors:\n{stderr}")

        if not sections:
            if result.returncode == 0:
                return "✅ Command executed successfully with no output."
            return f"❌ Command failed with exit code {result.returncode}."

        output = "\n\n".join(sections)

        # Limit huge outputs to avoid flooding the chat.
        max_chars = 12000
        if len(output) > max_chars:
            output = (
                output[:max_chars]
                + "\n\n[Output truncated because it was too large.]"
            )

        if result.returncode != 0:
            return (
                f"❌ Command exited with code {result.returncode}.\n\n"
                f"{output}"
            )

        return output

    except subprocess.TimeoutExpired:
        logger.warning("Shell command timed out: %s", command)
        return "❌ Command timed out after 120 seconds."
    except Exception as e:
        logger.exception("Error executing shell command")
        return f"❌ Error executing command: {str(e)}"
