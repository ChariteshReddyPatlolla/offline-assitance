"""
PDF API routes — text explanation and file upload.
"""
import os
import tempfile
import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from shared import schemas
from shared.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/explain", response_model=schemas.ExplainResponse)
async def explain_text(request: schemas.ExplainRequest):
    """
    Explain a piece of text (e.g. selected from a PDF) using the local LLM.
    """
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOllama(model="llama3.1:8b", temperature=0.3)
        messages = [
            SystemMessage(content=(
                "You are OmniAgent, a helpful AI assistant. "
                "Explain the following text concisely and clearly. "
                "Use markdown formatting. Keep the explanation under 200 words unless the text is complex."
            )),
            HumanMessage(content=f"Please explain this text:\n\n{request.text}"),
        ]
        response = llm.invoke(messages)
        return schemas.ExplainResponse(explanation=response.content)
    except Exception as e:
        logger.error("Explain error: %s", e)
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and save it to a temp directory.
    Returns the filepath for subsequent PDF operations.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    upload_dir = os.path.join(tempfile.gettempdir(), "omniagent_pdfs")
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, file.filename)
    content = await file.read()

    with open(filepath, "wb") as f:
        f.write(content)

    logger.info("PDF uploaded: %s (%d bytes)", filepath, len(content))
    return {
        "filepath": filepath,
        "filename": file.filename,
        "size": len(content),
    }
