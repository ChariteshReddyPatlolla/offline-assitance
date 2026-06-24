from services.tools.shell import execute_shell_command, open_url_in_browser, search_youtube, web_search
from services.tools.browser import (
    pause_playback,
    resume_playback,
    browser_navigate,
    browser_click,
    browser_type,
    browser_wait_for,
    browser_take_screenshot,
    browser_close,
    browser_scroll,
    browser_extract_text,
    list_browser_tabs,
    switch_browser_tab
)
from services.tools.file_ops import (
    read_file,
    write_file,
    delete_file,
    list_directory,
    create_directory,
    search_files,
    move_file
)
from services.tools.desktop import (
    open_application,
    take_screenshot_description,
    type_text_at_cursor,
    press_hotkey,
    close_application,
    search_start_menu,
    focus_application,
    minimize_application,
    maximize_application,
    run_editor_sync_demo,
    open_file_in_vscode,
    open_folder_in_vscode,
    run_command_in_vscode_terminal,
    execute_workflow
)
from services.tools.git_tool import (
    git_status,
    git_log,
    git_diff,
    analyze_repo,
    git_add,
    git_commit,
    git_checkout,
    git_branch
)
from services.tools.email_tool import send_email, send_email_fast, save_to_drafts, read_emails, search_emails
from services.tools.pdf_tool import (
    extract_pdf_text,
    summarize_pdf,
    extract_pdf_tables,
    split_pdf,
    merge_pdfs
)
from services.tools.research import (
    research_topic,
    scrape_page,
    extract_links,
    search_jobs
)
from services.tools.sqlite_tool import (
    read_query,
    write_query,
    list_tables,
    describe_table
)
from services.tools.approval_store import require_tool_approval
from services.tools.memory_ops import remember_fact

# All core tools available to uvicorn/agent
all_tools = [
    open_url_in_browser,
    search_youtube,
    pause_playback,
    resume_playback,
    web_search,
    open_application,
    close_application,
    search_start_menu,
    focus_application,
    minimize_application,
    maximize_application,
    take_screenshot_description,
    type_text_at_cursor,
    press_hotkey,
    read_file,
    list_directory,
    create_directory,
    git_status,
    git_log,
    git_diff,
    analyze_repo,
    git_add,
    git_checkout,
    git_branch,
    extract_pdf_text,
    summarize_pdf,
    research_topic,
    run_editor_sync_demo,
    read_query,
    list_tables,
    describe_table,
    browser_navigate,
    browser_click,
    browser_type,
    browser_wait_for,
    browser_take_screenshot,
    browser_close,
    browser_scroll,
    browser_extract_text,
    list_browser_tabs,
    switch_browser_tab,
    search_files,
    extract_pdf_tables,
    split_pdf,
    merge_pdfs,
    scrape_page,
    extract_links,
    search_jobs,
    open_file_in_vscode,
    open_folder_in_vscode,
    run_command_in_vscode_terminal,
    execute_workflow,
    
    write_file,
    delete_file,
    execute_shell_command,
    send_email,
    save_to_drafts,
    read_emails,
    search_emails,
    git_commit,
    write_query,
    move_file,
    remember_fact,
]

# Mark tools with built-in approval to prevent double-wrapping
delete_file.__dict__["has_built_in_approval"] = True
execute_shell_command.__dict__["has_built_in_approval"] = True
send_email.__dict__["has_built_in_approval"] = True
git_commit.__dict__["has_built_in_approval"] = True
write_query.__dict__["has_built_in_approval"] = True
