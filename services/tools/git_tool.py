import os
import subprocess
from langchain_core.tools import tool


def _run_git(args: list, cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if result.returncode != 0 and err:
            return f"Git error: {err}"
        return out if out else "(no output)"
    except FileNotFoundError:
        return "Error: git is not installed or not in PATH."
    except Exception as e:
        return f"Error running git: {str(e)}"


@tool
def git_status(repo_path: str) -> str:
    """
    Get the git status of a repository at the given path.
    Shows modified, staged, and untracked files.
    """
    return _run_git(["status", "--short"], repo_path)


@tool
def git_log(repo_path: str, n: int = 10) -> str:
    """
    Get the last N git commits of a repository.
    Args:
        repo_path: path to the git repository
        n: number of commits to show (default 10)
    """
    return _run_git(["log", f"--oneline", f"-{n}"], repo_path)


@tool
def git_diff(repo_path: str) -> str:
    """
    Show uncommitted changes (git diff) in the repository.
    """
    return _run_git(["diff"], repo_path)


@tool
def analyze_repo(repo_path: str) -> str:
    """
    Analyze a git repository: show its file structure, README, and recent commits.
    Use this when the user asks to understand, summarize, or explain a repository.
    """
    output_parts = []

    # File tree (2 levels deep)
    try:
        tree_lines = []
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden dirs and common noise
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'venv', '.git')]
            depth = root.replace(repo_path, '').count(os.sep)
            if depth > 2:
                continue
            indent = '  ' * depth
            tree_lines.append(f"{indent}{os.path.basename(root)}/")
            for f in files[:10]:
                tree_lines.append(f"{indent}  {f}")
        output_parts.append("📁 File Structure:\n" + "\n".join(tree_lines[:60]))
    except Exception as e:
        output_parts.append(f"(Could not read file tree: {e})")

    # README
    for readme_name in ("README.md", "README.txt", "readme.md"):
        readme_path = os.path.join(repo_path, readme_name)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read(2000)
                output_parts.append(f"\n📄 README:\n{content}")
            except Exception:
                pass
            break

    # Recent commits
    commits = _run_git(["log", "--oneline", "-10"], repo_path)
    output_parts.append(f"\n📝 Recent Commits:\n{commits}")

    return "\n".join(output_parts)
