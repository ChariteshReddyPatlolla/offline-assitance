import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.git import (
    git_status_raw,
    git_log_raw,
    git_diff_raw,
    analyze_repo_raw,
    git_add_raw,
    git_commit_raw,
    git_checkout_raw,
    git_branch_raw
)

mcp = FastMCP("git")

@mcp.tool()
def git_status(repo_path: str) -> str:
    """Get the git status of a repository at the given path."""
    return git_status_raw(repo_path)

@mcp.tool()
def git_log(repo_path: str, n: int = 10) -> str:
    """Get the last N git commits of a repository."""
    return git_log_raw(repo_path, n)

@mcp.tool()
def git_diff(repo_path: str) -> str:
    """Show uncommitted changes (git diff) in the repository."""
    return git_diff_raw(repo_path)

@mcp.tool()
def analyze_repo(repo_path: str) -> str:
    """Analyze a git repository: show its file structure, README, and recent commits."""
    return analyze_repo_raw(repo_path)

@mcp.tool()
def git_add(repo_path: str, file_pattern: str = "*") -> str:
    """Stage changes in the repository."""
    return git_add_raw(repo_path, file_pattern)

@mcp.tool()
def git_commit(repo_path: str, message: str) -> str:
    """Commit staged changes in the repository."""
    return git_commit_raw(repo_path, message)

@mcp.tool()
def git_checkout(repo_path: str, branch: str) -> str:
    """Checkout a branch or commit in the repository."""
    return git_checkout_raw(repo_path, branch)

@mcp.tool()
def git_branch(repo_path: str) -> str:
    """List, create, or delete branches in the repository."""
    return git_branch_raw(repo_path)

if __name__ == "__main__":
    mcp.run()
