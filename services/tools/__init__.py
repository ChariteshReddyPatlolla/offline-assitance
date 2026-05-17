from services.tools.shell import execute_shell_command, open_url_in_browser, search_youtube, web_search
from services.tools.file_ops import read_file, write_file, delete_file, list_directory
from services.tools.desktop import open_application, take_screenshot_description, type_text_at_cursor, press_hotkey
from services.tools.git_tool import git_status, git_log, git_diff, analyze_repo
from services.tools.email_tool import draft_email
from services.tools.pdf_tool import extract_pdf_text, summarize_pdf
from services.tools.research import research_topic

all_tools = [
    # Browser / Web
    open_url_in_browser,
    search_youtube,
    web_search,
    # Desktop
    open_application,
    take_screenshot_description,
    type_text_at_cursor,
    press_hotkey,
    # Files
    read_file,
    write_file,
    delete_file,
    list_directory,
    # Shell (approval required)
    execute_shell_command,
    # Git
    git_status,
    git_log,
    git_diff,
    analyze_repo,
    # Email (approval required)
    draft_email,
    # PDF
    extract_pdf_text,
    summarize_pdf,
    # Research
    research_topic,
]
