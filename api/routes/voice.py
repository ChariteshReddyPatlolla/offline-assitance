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

import speech_recognition as sr

class SDAudioSource(sr.AudioSource):
    def __init__(self, device=None, sample_rate=16000, chunk_size=1024):
        import sounddevice as sd
        self.device_index = device
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.SAMPLE_WIDTH = 2
        self.raw_stream = None
        self.stream = None
    
    def __enter__(self):
        import sounddevice as sd
        self.raw_stream = sd.RawInputStream(
            samplerate=self.SAMPLE_RATE,
            blocksize=self.CHUNK,
            device=self.device_index,
            channels=1,
            dtype='int16'
        )
        self.raw_stream.start()
        
        class StreamWrapper:
            def __init__(self, raw_stream):
                self.raw_stream = raw_stream
            def read(self, size):
                data, overflow = self.raw_stream.read(size)
                return bytes(data)
        
        self.stream = StreamWrapper(self.raw_stream)
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        if self.raw_stream:
            self.raw_stream.stop()
            self.raw_stream.close()

@router.get("/listen", response_model=TranscriptionResult)
async def listen_audio():
    """
    Listens to the system microphone via sounddevice until 1 second of silence is detected, 
    transcribes via SpeechRecognition, and translates.
    """
    try:
        import speech_recognition as sr
        from mtranslate import translate
        import sounddevice as sd
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Required audio packages not installed."
        )

    logger.info("Listening to system microphone dynamically...")
    try:
        # Find a suitable microphone device, avoiding Oculus Virtual Audio
        device_index = None
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0 and 'Oculus' not in dev['name']:
                    # Prefer standard microphones
                    if 'Microphone' in dev['name'] or 'Realtek' in dev['name']:
                        device_index = i
                        break
            if device_index is None:
                device_index = sd.default.device[0]
        except Exception:
            device_index = None

        # Use SpeechRecognition with custom AudioSource
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1.0  # Stop after 1 second of silence
        
        with SDAudioSource(device=device_index) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.info("Ready for speech...")
            try:
                # Listen dynamically up to a 10-second max limit to prevent hanging indefinitely
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                logger.info("No speech detected (WaitTimeoutError). Returning empty text.")
                return TranscriptionResult(text="", language="en", duration=0.0)
            
        logger.info("Audio captured, transcribing...")
        text = recognizer.recognize_google(audio)
        logger.info(f"Original Transcription: '{text}'")
        
        translated_text = translate(text, "en", "auto")
        logger.info(f"Translated Transcription: '{translated_text}'")

        # Estimate duration
        duration = len(audio.frame_data) / (source.SAMPLE_RATE * source.SAMPLE_WIDTH)

        return TranscriptionResult(
            text=translated_text,
            language="en", 
            duration=duration
        )
    except Exception as e:
        error_type = type(e).__name__
        if "UnknownValueError" in error_type:
            logger.info("No speech detected (UnknownValueError). Returning empty text.")
            return TranscriptionResult(text="", language="en", duration=0.0)
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
