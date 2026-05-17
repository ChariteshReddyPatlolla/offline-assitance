"""
Voice transcription route — accepts audio blob, runs faster-whisper offline STT.
"""
import io
import logging
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class TranscriptionResult(BaseModel):
    text: str
    language: str = "en"
    duration: float = 0.0


@router.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe audio to text using faster-whisper (local, offline).
    Accepts any audio format (webm, wav, mp3, ogg, etc.)
    Returns the transcribed text.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="faster-whisper not installed. Run: pip install faster-whisper"
        )

    # Save the uploaded audio to a temp file
    suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        logger.info("Transcribing audio file: %s (%d bytes)", tmp_path, len(content))

        # Load model — use 'base' for good speed/accuracy balance
        # Model will be downloaded on first use (~150MB)
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(tmp_path, beam_size=5)

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        full_text = " ".join(text_parts).strip()
        logger.info("Transcription result: '%s' (lang=%s)", full_text[:100], info.language)

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            duration=info.duration if hasattr(info, "duration") else 0.0,
        )
    except Exception as e:
        logger.error("Transcription error: %s", e)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/status")
def voice_status():
    """Check if faster-whisper is available."""
    try:
        import faster_whisper
        return {"available": True, "version": getattr(faster_whisper, "__version__", "unknown")}
    except ImportError:
        return {"available": False, "message": "Install with: pip install faster-whisper"}
