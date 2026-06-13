import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
import logging
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from shared import schemas, models
from shared.database import get_db
from api.routes import chat, approvals, voice, sessions, pdf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OmniAgent API Gateway",
    description="Offline autonomous AI copilot API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routes
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["Approvals"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF"])


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": "2.0.0",
        "features": [
            "chat", "approvals", "voice-stt", "sessions",
            "pdf-explain", "research", "youtube-automation"
        ]
    }


@app.get("/")
def root():
    return {"message": "OmniAgent API is running. See /docs for API reference."}


from fastapi import Body
import ctypes
from ctypes import wintypes

@app.post("/api/desktop/resize")
async def resize_desktop(payload: dict = Body(...)):
    compact = payload.get("compact", False)
    
    try:
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        
        target_hwnd = None
        
        def foreach_window(hwnd, lParam):
            nonlocal target_hwnd
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                if "OmniAgent" in title or "localhost:5173" in title or "127.0.0.1:5173" in title:
                    target_hwnd = hwnd
                    return False
            return True
            
        EnumWindows(EnumWindowsProc(foreach_window), 0)
        
        if target_hwnd:
            GWL_STYLE = -16
            GWL_EXSTYLE = -20
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            WS_EX_LAYERED = 0x00080000
            LWA_COLORKEY = 0x00000001
            
            GetWindowLong = ctypes.windll.user32.GetWindowLongW
            SetWindowLong = ctypes.windll.user32.SetWindowLongW
            SetWindowPos = ctypes.windll.user32.SetWindowPos
            SetLayeredWindowAttributes = ctypes.windll.user32.SetLayeredWindowAttributes
            
            # SWP flags
            SWP_NOACTIVATE = 0x0010
            SWP_FRAMECHANGED = 0x0020
            SWP_SHOWWINDOW = 0x0040
            
            current_style = GetWindowLong(target_hwnd, GWL_STYLE)
            current_exstyle = GetWindowLong(target_hwnd, GWL_EXSTYLE)
            
            if compact:
                # Strip title bar and borders
                new_style = current_style & ~WS_CAPTION & ~WS_THICKFRAME
                SetWindowLong(target_hwnd, GWL_STYLE, new_style)
                
                # Enable layered window style
                new_exstyle = current_exstyle | WS_EX_LAYERED
                SetWindowLong(target_hwnd, GWL_EXSTYLE, new_exstyle)
                
                # Fuchsia / Magenta chroma key transparency (0x00FF00FF)
                SetLayeredWindowAttributes(target_hwnd, 0x00FF00FF, 0, LWA_COLORKEY)
                
                # Resize and pin to Always-On-Top
                HWND_TOPMOST = -1
                SetWindowPos(target_hwnd, HWND_TOPMOST, 0, 0, 400, 70, SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
            else:
                # Restore title bar and borders
                new_style = current_style | WS_CAPTION | WS_THICKFRAME
                SetWindowLong(target_hwnd, GWL_STYLE, new_style)
                
                # Remove layered transparency style
                new_exstyle = current_exstyle & ~WS_EX_LAYERED
                SetWindowLong(target_hwnd, GWL_EXSTYLE, new_exstyle)
                
                # Restore normal size and unpin Always-On-Top
                HWND_NOTOPMOST = -2
                SetWindowPos(target_hwnd, HWND_NOTOPMOST, 0, 0, 800, 600, SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
    except Exception as e:
        logger.error(f"Win32 window resize failed: {e}")
        
    return {"status": "success", "compact": compact}

