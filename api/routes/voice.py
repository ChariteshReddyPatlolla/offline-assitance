"""
Voice transcription route — listens directly from the system microphone using sounddevice,
transcribes using SpeechRecognition, translates using mtranslate, and returns the result.
"""
import logging
import tempfile
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class TranscriptionResult(BaseModel):
    text: str
    language: str = "en"
    duration: float = 0.0

@router.get("/listen", response_model=TranscriptionResult)
async def listen_audio():
    """
    Listens to the system microphone via sounddevice, saves to wav, transcribes via SpeechRecognition, and translates.
    """
    try:
        import speech_recognition as sr
        from mtranslate import translate
        import sounddevice as sd
        from scipy.io.wavfile import write
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Required audio packages not installed."
        )

    fs = 44100  # Sample rate
    seconds = 5  # Listen for 5 seconds

    logger.info("Listening to system microphone for 5 seconds...")
    try:
        # Record audio
        myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()  # Wait until recording is finished
        
        # Save as temp WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        
        write(tmp_path, fs, myrecording)
        
        # Use SpeechRecognition on the file
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = False
        recognizer.energy_threshold = 34000
        recognizer.dynamic_energy_adjustment_damping = 0.010
        recognizer.dynamic_energy_ratio = 1.0
        recognizer.pause_threshold = 0.3
        
        with sr.AudioFile(tmp_path) as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.record(source)
            
        logger.info("Audio captured, transcribing...")
        text = recognizer.recognize_google(audio)
        logger.info(f"Original Transcription: '{text}'")
        
        translated_text = translate(text, "en", "auto")
        logger.info(f"Translated Transcription: '{translated_text}'")

        # Cleanup
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        return TranscriptionResult(
            text=translated_text,
            language="en", 
            duration=seconds
        )
    except Exception as e:
        error_type = type(e).__name__
        if "UnknownValueError" in error_type:
            logger.info("No speech detected (UnknownValueError). Returning empty text.")
            return TranscriptionResult(text="", language="en", duration=seconds)
        if "RequestError" in error_type:
            raise HTTPException(status_code=500, detail=f"Could not request results from service; {e}")
        
        logger.error("Transcription error: %s - %s", type(e), e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e) or type(e).__name__}")

@router.get("/status")
def voice_status():
    """Check if SpeechRecognition and sounddevice are available."""
    try:
        import speech_recognition as sr
        import sounddevice as sd
        from mtranslate import translate
        return {"available": True, "version": sr.__version__}
    except ImportError:
        return {"available": False, "message": "Install with: pip install SpeechRecognition sounddevice scipy mtranslate"}
