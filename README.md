# TubeForge — FFmpeg-enabled Vercel package

## Included
- Flask API and web UI
- yt-dlp integration
- FFmpeg binary discovery through `imageio-ffmpeg`
- Separate video/audio stream selection and FFmpeg merge/remux
- MP3 audio extraction
- Friendly YouTube bot-verification error message
- Vercel Python function entrypoint

## Deploy
1. Replace the matching files in your existing GitHub repository with the files in this ZIP.
2. Ensure `api/index.py` contains `from app import app`.
3. Keep the provided schema-only `vercel.json`.
4. Commit and push to `main`; wait for Vercel to redeploy.
5. Check `/api/health`; it should report `"status":"ok"` and `"ffmpeg":true`.

## Important Vercel limits
This is a best-effort Vercel-only implementation. Downloads and merging happen in the function's temporary directory, then the output is returned from the function. Vercel has deployment bundle, execution time, temporary storage, and response-size limits (including a 4.5 MB function response payload limit in common configurations). Therefore larger media downloads may fail even when FFmpeg is available. The ZIP does not claim these hosting limits are solved.

The app does not use personal browser cookies or bypass access controls. If YouTube requires sign-in or bot verification, that request will fail.

## Local test
Python 3.11+:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
Then open `http://127.0.0.1:5000`.
