import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from services.tools.impl.pdf import (
    extract_pdf_text_raw,
    summarize_pdf_raw,
    extract_pdf_tables_raw,
    split_pdf_raw,
    merge_pdfs_raw
)

mcp = FastMCP("pdf")

@mcp.tool()
def extract_pdf_text(filepath: str) -> str:
    """Extract all text content from a PDF file."""
    return extract_pdf_text_raw(filepath)

@mcp.tool()
def summarize_pdf(filepath: str) -> str:
    """Extract text from a PDF and return it with a request for summarization."""
    return summarize_pdf_raw(filepath)

@mcp.tool()
def extract_pdf_tables(filepath: str) -> str:
    """Extract tables from PDF using layout analysis."""
    return extract_pdf_tables_raw(filepath)

@mcp.tool()
def split_pdf(filepath: str, page_range: str, output_path: str) -> str:
    """Split a PDF by a page range (e.g. '1-3', '1,3,5', or '2')."""
    return split_pdf_raw(filepath, page_range, output_path)

@mcp.tool()
def merge_pdfs(filepaths: list[str], output_path: str) -> str:
    """Merge multiple PDFs into a single output PDF."""
    return merge_pdfs_raw(filepaths, output_path)

if __name__ == "__main__":
    mcp.run()
