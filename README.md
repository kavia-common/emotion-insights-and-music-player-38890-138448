# emotion-insights-and-music-player-38890-138448

## Backend Usage Instructions

### Install requirements

```bash
cd emotion_document_backend
pip install -r requirements.txt
```

### Start backend

```bash
uvicorn main:app --reload --port 8081
```

### Endpoints

- `/upload` (POST) - Upload .txt or .pdf file. Returns status.
- `/extract_emotions` (POST) - Input: filename (from upload), returns top 3 emotions, scores, suggested music file paths.
- `/music_tone` (GET) - Query param: `emotion`. Returns audio file for playback.
- `/health` (GET) - Health check.

### Music Assets

Put your `.mp3` files for each emotion in `emotion_document_backend/assets/music/`. Filenames should match mapping in `main.py`.