import os
from langchain_core.tools import tool
from shared.context import active_session_dir
from services.mcp.client import MCPClientManager

def _get_fallback_desktop() -> str:
    user_profile = os.environ.get("USERPROFILE", r"C:\Users\patlo")
    desktop = os.path.join(user_profile, "Desktop")
    onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
    if os.path.exists(onedrive_desktop):
        return onedrive_desktop
    return desktop

@tool
def extract_pdf_text(filepath: str) -> str:
    """
    Extract all text content from a PDF file.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)
    abs_path = os.path.abspath(filepath)

    return MCPClientManager.get_instance().call_tool(
        "pdf", "extract_pdf_text", filepath=abs_path
    )

@tool
def summarize_pdf(filepath: str) -> str:
    """
    Extract text from a PDF and prepare it for summarization.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)
    abs_path = os.path.abspath(filepath)

    return MCPClientManager.get_instance().call_tool(
        "pdf", "summarize_pdf", filepath=abs_path
    )

@tool
def extract_pdf_tables(filepath: str) -> str:
    """
    Extract tables from PDF using layout analysis.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)
    abs_path = os.path.abspath(filepath)
    return MCPClientManager.get_instance().call_tool(
        "pdf", "extract_pdf_tables", filepath=abs_path
    )

@tool
def split_pdf(filepath: str, page_range: str, output_path: str) -> str:
    """
    Split a PDF by a page range (e.g. '1-3', '1,3,5', or '2').
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    if not os.path.isabs(filepath):
        filepath = os.path.join(current_dir, filepath)
    if not os.path.isabs(output_path):
        output_path = os.path.join(current_dir, output_path)
    abs_path = os.path.abspath(filepath)
    abs_out_path = os.path.abspath(output_path)
    return MCPClientManager.get_instance().call_tool(
        "pdf", "split_pdf", filepath=abs_path, page_range=page_range, output_path=abs_out_path
    )

@tool
def merge_pdfs(filepaths: list[str], output_path: str) -> str:
    """
    Merge multiple PDFs into a single output PDF.
    """
    current_dir = active_session_dir.get() or _get_fallback_desktop()
    abs_paths = []
    for fp in filepaths:
        if not os.path.isabs(fp):
            fp = os.path.join(current_dir, fp)
        abs_paths.append(os.path.abspath(fp))
    if not os.path.isabs(output_path):
        output_path = os.path.join(current_dir, output_path)
    abs_out_path = os.path.abspath(output_path)
    return MCPClientManager.get_instance().call_tool(
        "pdf", "merge_pdfs", filepaths=abs_paths, output_path=abs_out_path
    )
