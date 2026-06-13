import os
import time
import logging
import subprocess
from langchain_core.tools import tool
from services.tools.shell import execute_shell_command
from services.tools.desktop import open_application, close_application
from services.tools.file_ops import write_file, read_file
from services.tools.email_tool import save_to_drafts
from services.tools.research import research_topic
from services.tools.approval_store import require_tool_approval
from services.mcp.client import MCPClientManager

logger = logging.getLogger(__name__)

def call_mcp_tool_sync(server_name: str, tool_name: str, **kwargs):
    """Programmatically calls an MCP tool synchronously by name using the active server process."""
    manager = MCPClientManager.get_instance()
    return manager.call_tool(server_name, tool_name, **kwargs)

@tool
def create_python_project(project_name: str, code: str) -> str:
    """
    Desktop Coding Workflow:
    Opens VS Code, creates a project folder, creates main.py with the provided code,
    opens it in VS Code, executes the script, and returns the output.
    """
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    desktop = os.path.join(user_profile, "Desktop")
    if not os.path.exists(desktop):
        desktop = os.path.join(user_profile, "OneDrive", "Desktop")
        
    project_dir = os.path.join(desktop, project_name)
    main_py = os.path.join(project_dir, "main.py")
    
    # 1. Create project folder via Filesystem MCP create_directory
    try:
        call_mcp_tool_sync("filesystem", "create_directory", path=project_dir)
    except Exception as e:
        logger.warning("Failed to create directory via MCP: %s. Using fallback.", e)
        os.makedirs(project_dir, exist_ok=True)
        
    # 2. Write code to main.py and open in VS Code using our write_file tool
    write_res = write_file.invoke({
        "filepath": main_py,
        "content": code,
        "open_in_editor": "vscode"
    })
    
    # Check if write_res requires approval
    if "[NEEDS_APPROVAL:" in write_res:
        return write_res
        
    # 3. Wait briefly for editor to open
    time.sleep(3)
    
    # 4. Run the code
    run_res = execute_shell_command.invoke({
        "command": f"python \"{main_py}\""
    })
    
    return f"Project created successfully.\n\nWriting Output:\n{write_res}\n\nExecution Output:\n{run_res}"

@tool
def modify_file_and_rerun(filepath: str, append_code: str) -> str:
    """
    Notepad Modification Workflow:
    Opens Notepad, appends additional print or code statements to the file,
    saves the file, reruns the file, and returns the output.
    """
    if not os.path.exists(filepath):
        return f"❌ File not found: {filepath}"
        
    # 1. Read existing content
    try:
        content = read_file.invoke({"filepath": filepath})
    except Exception:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
    # Append the new code
    new_content = content + "\n" + append_code
    
    # 2. Open Notepad and write/save the file
    write_res = write_file.invoke({
        "filepath": filepath,
        "content": new_content,
        "open_in_editor": "notepad"
    })
    
    if "[NEEDS_APPROVAL:" in write_res:
        return write_res
        
    # 3. Run the modified file
    run_res = execute_shell_command.invoke({
        "command": f"python \"{filepath}\""
    })
    
    return f"File modified successfully.\n\nModification Output:\n{write_res}\n\nExecution Output:\n{run_res}"

@tool
def browser_research_and_save(query: str, filepath: str) -> str:
    """
    Browser Research Workflow:
    Opens browser, searches Google/DuckDuckGo for a query, extracts text,
    summarizes the content, and saves notes to a markdown file.
    """
    # 1. Perform web search/research topic
    research_res = research_topic.invoke({"query": query})
    
    # 2. Write findings to the filepath
    write_res = write_file.invoke({
        "filepath": filepath,
        "content": research_res
    })
    
    if "[NEEDS_APPROVAL:" in write_res:
        return write_res
        
    return f"Research completed and saved.\n\nSummary:\n{research_res}\n\nSaved to: {filepath}"

@tool
def youtube_search_and_play(query: str) -> str:
    """
    YouTube Workflow:
    Opens YouTube, searches for a query, and plays the first video.
    """
    from services.tools.shell import search_youtube
    return search_youtube.invoke({"query": query})

@tool
def git_commit_and_push(repo_path: str, message: str) -> str:
    """
    Git Workflow:
    Checks git status, stages all changes, commits with message, and pushes to remote.
    """
    # 1. Check status
    try:
        status_res = call_mcp_tool_sync("git", "git_status", repo_path=repo_path)
    except Exception:
        from services.tools.git_tool import git_status
        status_res = git_status.invoke({"repo_path": repo_path})
        
    # 2. Git add and Git commit
    try:
        call_mcp_tool_sync("git", "git_add", repo_path=repo_path, file_pattern="*")
        commit_res = call_mcp_tool_sync("git", "git_commit", repo_path=repo_path, message=message)
    except Exception as e:
        commit_res = f"Commit failed or approval required: {e}"
        
    if "[NEEDS_APPROVAL:" in commit_res:
        return commit_res
        
    # 3. Git push via execute_shell_command
    push_res = execute_shell_command.invoke({
        "command": f"git -C \"{repo_path}\" push"
    })
    
    return f"Git Workflow completed.\n\nStatus:\n{status_res}\n\nCommit Output:\n{commit_res}\n\nPush Output:\n{push_res}"

@tool
def research_and_email(topic: str, recipient: str) -> str:
    """
    Research and Email Workflow:
    Researches a topic, summarizes it, drafts an email with the summary, and sends it.
    """
    # 1. Research topic
    research_res = research_topic.invoke({"query": topic})
    
    # 2. Draft email
    subject = f"Research Summary: {topic}"
    email_res = save_to_drafts.invoke({
        "to": recipient,
        "subject": subject,
        "body": research_res
    })
    
    return email_res

@tool
def analyze_resume_skills(resume_path: str) -> str:
    """
    Reads a resume file (PDF or text) and extracts key skills, email,
    and target job titles for job matching.
    """
    if not os.path.exists(resume_path):
        return f"❌ Resume file not found at: {resume_path}"
        
    content = ""
    if resume_path.lower().endswith(".pdf"):
        from services.tools.impl.pdf import extract_pdf_text_raw
        content = extract_pdf_text_raw(resume_path)
    else:
        from services.tools.impl.file_ops import read_file_raw
        content = read_file_raw(resume_path)
        
    if "❌" in content or not content.strip():
        return f"❌ Failed to extract content from resume: {content}"
        
    import re
    text_lower = content.lower()
    
    keywords = [
        "python", "javascript", "typescript", "java", "c++", "c#", "ruby", "php", "go", "rust",
        "react", "angular", "vue", "next.js", "node.js", "django", "flask", "fastapi", "spring",
        "html", "css", "sql", "nosql", "mongodb", "postgresql", "mysql", "sqlite", "redis",
        "docker", "kubernetes", "aws", "azure", "gcp", "git", "ci/cd", "machine learning",
        "deep learning", "nlp", "ai", "pytorch", "tensorflow", "agile", "scrum"
    ]
    
    found_skills = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower)]
    
    email = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', content)
    email_str = email[0] if email else "Not found"
    
    roles = ["software engineer", "developer", "frontend", "backend", "full stack", "data scientist", "data analyst", "project manager"]
    found_roles = [r for r in roles if r in text_lower]
    target_role = found_roles[0].title() if found_roles else "Software Professional"
    
    summary = (
        f"Resume Analysis for {os.path.basename(resume_path)}:\n"
        f"- Target Role: {target_role}\n"
        f"- Contact Email: {email_str}\n"
        f"- Detected Skills: {', '.join(found_skills) if found_skills else 'None detected'}\n\n"
        f"Resume Content Preview (first 1500 chars):\n"
        f"{content[:1500]}..."
    )
    return summary
