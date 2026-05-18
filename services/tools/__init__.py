from services.tools.shell import execute_shell_command, open_url_in_browser, search_youtube, web_search
from services.tools.file_ops import read_file, write_file, delete_file, list_directory
from services.tools.desktop import open_application, take_screenshot_description, type_text_at_cursor, press_hotkey
from services.tools.git_tool import git_status, git_log, git_diff, analyze_repo
from services.tools.email_tool import draft_email
from services.tools.pdf_tool import extract_pdf_text, summarize_pdf
from services.tools.research import research_topic
from services.tools.approval_store import require_tool_approval

# SAFE TOOLS (no approval)
all_tools = [
    open_url_in_browser,
    search_youtube,
    web_search,            # <-- IMPORTANT: should NOT be wrapped
    open_application,      # wrap only if you want approval
    take_screenshot_description,
    type_text_at_cursor,
    press_hotkey,
    read_file,
    list_directory,
    git_status,
    git_log,
    git_diff,
    analyze_repo,
    extract_pdf_text,
    summarize_pdf,
    research_topic,
    
    write_file,
    delete_file,
    execute_shell_command,
    draft_email,
]

