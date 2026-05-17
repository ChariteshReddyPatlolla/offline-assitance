import os
from langchain_core.tools import tool


@tool
def extract_pdf_text(filepath: str) -> str:
    """
    Extract all text content from a PDF file.
    Use this when the user uploads or references a PDF document.
    Args:
        filepath: absolute or relative path to the PDF file
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"[Page {i+1}]\n{text}")
        if not pages_text:
            return "No text could be extracted from the PDF."
        full_text = "\n\n".join(pages_text)
        # Limit to first 8000 chars to avoid token overflow
        if len(full_text) > 8000:
            return full_text[:8000] + "\n\n[... PDF truncated to first 8000 characters ...]"
        return full_text
    except ImportError:
        return "❌ pypdf is not installed. Run: pip install pypdf"
    except FileNotFoundError:
        return f"❌ File not found: {filepath}"
    except Exception as e:
        return f"❌ Error reading PDF: {str(e)}"


@tool
def summarize_pdf(filepath: str) -> str:
    """
    Extract text from a PDF and prepare it for summarization.
    Returns the extracted text with an instruction to summarize.
    Use this when the user asks to summarize a PDF.
    """
    text = extract_pdf_text.invoke({"filepath": filepath})
    if text.startswith("❌"):
        return text
    return f"Please summarize the following PDF content:\n\n{text}"
