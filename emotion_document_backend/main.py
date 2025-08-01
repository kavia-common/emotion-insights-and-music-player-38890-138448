import os
import shutil
from tempfile import NamedTemporaryFile
from typing import List, Optional, Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import fitz  # PyMuPDF for PDF parsing
import uvicorn

# PUBLIC_INTERFACE
class UploadProgress(BaseModel):
    status: str = Field(..., description="Current upload status (progress, complete, error)")
    detail: Optional[str] = Field(None, description="Extra information about progress or error")

# PUBLIC_INTERFACE
class EmotionResult(BaseModel):
    emotions: List[str] = Field(..., description="Top detected emotions")
    scores: Dict[str, float] = Field(..., description="Emotion confidence scores")
    suggestions: List[str] = Field(..., description="Suggested music tones for the detected emotions")

# Simple mapping of emotions to sample music files/URLs (adjust/add files as needed)
EMOTION_MUSIC = {
    "happy": "assets/music/happy.mp3",
    "sad": "assets/music/sad.mp3",
    "angry": "assets/music/angry.mp3",
    "fear": "assets/music/fear.mp3",
    "surprise": "assets/music/surprise.mp3",
    "neutral": "assets/music/neutral.mp3"
}

# Simple emotion keywords (demonstration purpose only)
EMOTION_KEYWORDS = {
    "happy": ["happy", "joy", "delighted", "pleased", "smile", "cheerful", "thrilled", "elated", "excited"],
    "sad": ["sad", "down", "depressed", "unhappy", "gloomy", "cry", "tear", "sorrow", "tragic"],
    "angry": ["angry", "mad", "furious", "rage", "irritated", "annoyed", "hate", "upset"],
    "fear": ["afraid", "scared", "fear", "frighten", "panic", "nervous", "worry", "terrify"],
    "surprise": ["surprise", "astonish", "amaze", "shocked", "astonished", "unexpected"],
    "neutral": []
}

UPLOAD_DIR = "uploads"
ASSETS_MUSIC_DIR = "assets/music"

app = FastAPI(
    title="Emotion Document Backend",
    description="Handles document upload, emotion extraction, and music tone suggestion based on detected emotions.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Upload", "description": "Endpoints for uploading documents."},
        {"name": "Emotion Extraction", "description": "Extract emotion info from documents."},
        {"name": "Tone Suggestion", "description": "Map detected emotions to music tones."}
    ]
)

origins = ["*"]  # In production, restrict this!
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Create required directories if not present
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ASSETS_MUSIC_DIR, exist_ok=True)

# PUBLIC_INTERFACE
@app.post("/upload", tags=["Upload"], summary="Upload a document (.txt or PDF)", response_model=UploadProgress)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a .txt or PDF file for analysis.

    - **file**: The file to upload (.txt or .pdf)
    Returns progress or error status.
    """
    filename = file.filename
    ext = filename.split(".")[-1].lower()
    if ext not in {"txt", "pdf"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only .txt and .pdf allowed.")

    try:
        file_location = os.path.join(UPLOAD_DIR, filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return UploadProgress(status="complete", detail=f"File uploaded as {filename}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# PUBLIC_INTERFACE
@app.post("/extract_emotions", tags=["Emotion Extraction"], summary="Extract emotions from document", response_model=EmotionResult)
async def extract_emotions(filename: str = None):
    """
    Parses uploaded document, extracts text, and analyzes to return top 3 detected emotions and music suggestions.

    - **filename**: Name of the previously uploaded file (from /upload).

    Returns: Top 3 emotions, confidence scores, and music tone suggestions.
    """
    if filename is None:
        raise HTTPException(status_code=400, detail="Filename not provided.")

    file_location = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="File not found. Please upload first.")

    ext = filename.split(".")[-1].lower()
    try:
        text = ""
        if ext == "txt":
            with open(file_location, 'r', encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif ext == "pdf":
            doc = fitz.open(file_location)
            text = " ".join([page.get_text() for page in doc])
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type for extraction.")

        # Very simple emotion keyword matching as placeholder (replace with ML model for production)
        emotion_counts = {emo: 0 for emo in EMOTION_KEYWORDS}
        for emo, keywords in EMOTION_KEYWORDS.items():
            for keyword in keywords:
                emotion_counts[emo] += text.lower().count(keyword)

        # Sort emotions by count
        top_emotions = sorted(
            ((emo, cnt) for emo, cnt in emotion_counts.items() if cnt > 0),
            key=lambda x: -x[1]
        )

        if not top_emotions:
            # Default to neutral if no emotion detected
            result_emotions = ["neutral"]
            scores = {"neutral": 1.0}
        else:
            result_emotions = [emo for emo, cnt in top_emotions[:3]]
            total = sum(cnt for emo, cnt in top_emotions[:3])
            scores = {emo: round(cnt / total, 3) for emo, cnt in top_emotions[:3]}

        suggestions = [EMOTION_MUSIC.get(e, EMOTION_MUSIC["neutral"]) for e in result_emotions]

        return EmotionResult(emotions=result_emotions, scores=scores, suggestions=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction or parsing failed: {str(e)}")

# PUBLIC_INTERFACE
@app.get("/music_tone", tags=["Tone Suggestion"], summary="Get music tone for emotion", description="Serve a music file (MIDI/MP3) for the detected emotion.")
async def get_music_tone(emotion: str):
    """
    Returns a music file corresponding to the detected (or user-selected) emotion.

    - **emotion**: One of the supported emotion keywords.

    Returns: Music file for playback (audio/mp3).
    """
    path = EMOTION_MUSIC.get(emotion.lower())
    if not path or not os.path.isfile(path):
        # fallback
        path = EMOTION_MUSIC["neutral"]
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Music tone file not found on server.")
    file_name = os.path.basename(path)
    return FileResponse(path, media_type="audio/mpeg", filename=file_name)

# PUBLIC_INTERFACE
@app.get("/health", tags=["Upload"], summary="Health check endpoint")
def health():
    """
    Health check endpoint for readiness/liveness probes.
    """
    return {"status": "ok"}

# PUBLIC_INTERFACE
@app.get("/openapi.json", include_in_schema=False)
def custom_openapi():
    """
    Override for OpenAPI schema if needed.
    """
    return app.openapi()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=True)
