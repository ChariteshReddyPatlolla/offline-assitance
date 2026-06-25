import os

def extract_pdf_text_raw(filepath: str) -> str:
    """Extract all text content from a PDF file."""
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
        if len(full_text) > 8000:
            return full_text[:8000] + "\n\n[... PDF truncated to first 8000 characters ...]"
        return full_text
    except ImportError:
        return "❌ pypdf is not installed. Run: pip install pypdf"
    except FileNotFoundError:
        return f"❌ File not found: {filepath}"
    except Exception as e:
        return f"❌ Error reading PDF: {str(e)}"

def summarize_pdf_raw(filepath: str) -> str:
    """Extract text from a PDF and return it with a request for summarization."""
    text = extract_pdf_text_raw(filepath)
    if text.startswith("❌"):
        return text
    return f"Please summarize the following PDF content:\n\n{text}"

def extract_pdf_tables_raw(filepath: str) -> str:
    """Extract tables from PDF using space-separated layout analysis."""
    try:
        from pypdf import PdfReader
        if not os.path.exists(filepath):
            return f"❌ File not found: {filepath}"
        reader = PdfReader(filepath)
        tables = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            table_lines = []
            for line in lines:
                parts = [p.strip() for p in line.split("  ") if p.strip()]
                if len(parts) >= 2:
                    table_lines.append("| " + " | ".join(parts) + " |")
            if table_lines:
                tables.append(f"### Page {i+1} Tables:\n" + "\n".join(table_lines))
        if not tables:
            return "No tables detected in the PDF using basic layout extraction."
        return "\n\n".join(tables)
    except Exception as e:
        return f"❌ Error extracting tables: {str(e)}"

def split_pdf_raw(filepath: str, page_range: str, output_path: str) -> str:
    """Split a PDF by a page range (e.g. '1-3', '1,3,5', or '2')."""
    try:
        from pypdf import PdfReader, PdfWriter
        if not os.path.exists(filepath):
            return f"❌ File not found: {filepath}"
            
        reader = PdfReader(filepath)
        writer = PdfWriter()
        total_pages = len(reader.pages)
        
        pages_to_extract = []
        parts = page_range.split(",")
        for part in parts:
            if "-" in part:
                start, end = part.split("-")
                s_idx = int(start.strip()) - 1
                e_idx = int(end.strip())
                pages_to_extract.extend(range(s_idx, min(e_idx, total_pages)))
            else:
                p_idx = int(part.strip()) - 1
                if 0 <= p_idx < total_pages:
                    pages_to_extract.append(p_idx)
                    
        if not pages_to_extract:
            return "❌ No valid page numbers specified."
            
        for p in pages_to_extract:
            writer.add_page(reader.pages[p])
            
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        with open(output_path, "wb") as out_f:
            writer.write(out_f)
            
        return f"✅ Successfully split pages {page_range} into `{output_path}`."
    except Exception as e:
        return f"❌ Error splitting PDF: {str(e)}"

def merge_pdfs_raw(filepaths: list, output_path: str) -> str:
    """Merge multiple PDFs into a single output PDF."""
    try:
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        
        for fp in filepaths:
            if not os.path.exists(fp):
                return f"❌ File not found: {fp}"
            reader = PdfReader(fp)
            for page in reader.pages:
                writer.add_page(page)
                
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        with open(output_path, "wb") as out_f:
            writer.write(out_f)
            
        return f"✅ Successfully merged {len(filepaths)} PDFs into `{output_path}`."
    except Exception as e:
        return f"❌ Error merging PDFs: {str(e)}"
