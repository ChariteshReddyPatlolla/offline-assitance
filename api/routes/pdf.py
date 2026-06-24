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
    If document_id is provided, retrieves document context via RAG.
    """
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage, SystemMessage
        from services.agent.memory import search_pdf_context

        llm = ChatOllama(model="llama3.2:latest", temperature=0.3)
        
        # Retrieve context if document_id is present
        context = ""
        if request.document_id:
            query = request.question if request.question else request.text
            context = search_pdf_context(request.document_id, query)
            
        system_prompt = (
            "You are OmniAgent, a helpful AI assistant. "
            "Your task is to answer the user's question or explain the selected text concisely and clearly. "
            "Use markdown formatting. Keep the explanation under 200 words unless the text is complex. "
        )
        
        if context:
            system_prompt += (
                "IMPORTANT: You must use the provided document context to answer the user's question. "
                "Do NOT hallucinate or provide random answers outside of this context."
            )
            
        messages = [SystemMessage(content=system_prompt)]
        
        user_prompt = f"Selected Text:\n{request.text}\n"
        if request.question:
            user_prompt += f"\nUser Question:\n{request.question}\n"
        else:
            user_prompt += "\nPlease explain this text.\n"
            
        if context:
            user_prompt += f"\nDocument Context:\n{context}\n"
            
        messages.append(HumanMessage(content=user_prompt))
        
        response = llm.invoke(messages)
        return schemas.ExplainResponse(explanation=response.content)
    except Exception as e:
        logger.error("Explain error: %s", e)
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and save it to a temp directory.
    Indexes the PDF into ChromaDB for RAG, and returns the document ID.
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
    
    document_id = file.filename
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from services.agent.memory import add_pdf_context
        
        loader = PyPDFLoader(filepath)
        docs = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        texts = [doc.page_content for doc in splits]
        
        if texts:
            add_pdf_context(document_id, texts)
            logger.info(f"Successfully indexed {len(texts)} chunks for {document_id}")
    except Exception as e:
        logger.error(f"Failed to process PDF for RAG: {e}")
        # We don't fail the upload entirely if RAG indexing fails, but we log the error.

    return {
        "filepath": filepath,
        "filename": file.filename,
        "size": len(content),
        "document_id": document_id
    }
