import os
from langchain_core.tools import tool
from shared.context import active_session_dir
from services.tools.approval_store import require_approval
from services.mcp.client import MCPClientManager

def _get_fallback_desktop() -> str:
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    desktop = os.path.join(user_profile, "Desktop")
    onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
    if os.path.exists(onedrive_desktop):
        return onedrive_desktop
    return desktop

@tool
def git_status(repo_path: str) -> str:
    """
    Get the git status of a repository at the given path.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(repo_path):
        repo_path = os.path.join(current_dir, repo_path)
    abs_path = os.path.abspath(repo_path)
    
    return MCPClientManager.get_instance().call_tool(
        "git", "git_status", repo_path=abs_path
    )

@tool
def git_log(repo_path: str, n: int = 10) -> str:
    """
    Get the last N git commits of a repository.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(repo_path):
        repo_path = os.path.join(current_dir, repo_path)
    abs_path = os.path.abspath(repo_path)

    return MCPClientManager.get_instance().call_tool(
        "git", "git_log", repo_path=abs_path, n=n
    )

@tool
def git_diff(repo_path: str) -> str:
    """
    Show uncommitted changes (git diff) in the repository.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(repo_path):
        repo_path = os.path.join(current_dir, repo_path)
    abs_path = os.path.abspath(repo_path)

    return MCPClientManager.get_instance().call_tool(
        "git", "git_diff", repo_path=abs_path
    )

@tool
def analyze_repo(repo_path: str) -> str:
    """
    Analyze a git repository: show its file structure, README, and recent commits.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(repo_path):
        repo_path = os.path.join(current_dir, repo_path)
    abs_path = os.path.abspath(repo_path)

    return MCPClientManager.get_instance().call_tool(
        "git", "analyze_repo", repo_path=abs_path
    )

@tool
def git_add(repo_path: str, file_pattern: str = "*") -> str:
    """
    Stage changes in the repository.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(repo_path):
        repo_path = os.path.join(current_dir, repo_path)
    abs_path = os.path.abspath(repo_path)

    return MCPClientManager.get_instance().call_tool(
        "git", "git_add", repo_path=abs_path, file_pattern=file_pattern
    )

@tool
def git_commit(repo_path: str, message: str) -> str:
    """
    Commit staged changes in the repository. Requires explicit user approval.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(repo_path):
        repo_path = os.path.join(current_dir, repo_path)
    abs_path = os.path.abspath(repo_path)

    approval = require_approval(
        action_key=f"git_commit:{abs_path}",
        description=f"Commit git changes in repo:\n`{abs_path}`\nMessage: '{message}'",
        details={"repo_path": abs_path, "message": message, "dangerous": True}
    )
    if approval:
        return approval

    return MCPClientManager.get_instance().call_tool(
        "git", "git_commit", repo_path=abs_path, message=message
    )

@tool
def git_checkout(repo_path: str, branch: str) -> str:
    """
    Checkout a branch or commit in the repository.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(repo_path):
        repo_path = os.path.join(current_dir, repo_path)
    abs_path = os.path.abspath(repo_path)

    return MCPClientManager.get_instance().call_tool(
        "git", "git_checkout", repo_path=abs_path, branch=branch
    )

@tool
def git_branch(repo_path: str) -> str:
    """
    List, create, or delete branches in the repository.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(repo_path):
        repo_path = os.path.join(current_dir, repo_path)
    abs_path = os.path.abspath(repo_path)

    return MCPClientManager.get_instance().call_tool(
        "git", "git_branch", repo_path=abs_path
    )
