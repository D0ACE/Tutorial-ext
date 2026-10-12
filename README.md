# YouTube Learning & Project Analyzer

A Chrome extension that detects the active browser tab's URL and displays:
- Technologies/frameworks/libraries identified in the transcript
- The project being built and its likely purpose
- Learning topics covered
- A short summary
- The transcript text
- A warning when the video is detected as a song or another non-tutorial video

The current prototype supports YouTube links only. For another video website, it displays: **It is just a prototype for YouTube; in future it will work for every video.**

## Important limitation

This tool reads captions/transcripts that YouTube makes available. It does not listen to or transcribe audio itself. Videos without accessible captions may fail. Auto-generated captions can contain errors. The default analyzer uses keyword heuristics, so it may miss context or list a tool that was only mentioned.

For stronger, context-aware analysis, you can optionally configure a Google Gemini API key for the local backend. The transcript is then sent to the configured Gemini model for analysis. Keep your API key private.

Gemini also classifies whether the video is a technical tutorial. For songs, music videos, trailers, podcasts, and other non-tutorial content, the extension displays **🚫 Nah bro, it is not an tutorial**.

## Setup (Windows)

### 1. Install Python dependencies

Open PowerShell in the `backend` folder:

```powershell
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

### 2. (Optional) Enable AI analysis

For a better explanation of the project and technologies, set your API key in the same PowerShell terminal before starting the server:

```powershell
$env:GEMINI_API_KEY="your_gemini_api_key_here"
$env:GEMINI_MODEL="gemini-2.5-flash"
```

If you do not set a key, the extension still works with keyword-based analysis.

### 3. Start the backend

```powershell
python app.py
```

Leave this terminal open. The server listens only on your own computer at `127.0.0.1:8765`.

### 4. Load the Chrome extension

1. Open `chrome://extensions`.
2. Turn on **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension` folder inside this project.
5. Click the extension icon, paste a YouTube URL, and choose **Analyze full transcript**.

When the popup opens, it automatically fills the link from the current browser tab. You can replace it manually before starting analysis. After changing `manifest.json`, click **Reload** for the extension on `chrome://extensions`.

## Troubleshooting

- **Connection refused:** make sure `python app.py` is still running.
- **No transcript:** choose a video with captions enabled; some videos restrict transcript access.
- **Transcript fetch errors:** YouTube may change access behavior or throttle requests. Upgrade dependencies with `pip install -U youtube-transcript-api`.
- **AI analysis not working:** verify `GEMINI_API_KEY` is set in the same terminal that starts the backend. Without it, keyword analysis is used. You can change the model with `GEMINI_MODEL`.
- **Very long video:** the transcript is displayed in full, but optional AI analysis uses up to the first 100,000 characters to keep requests manageable.

## Privacy and security

The extension sends the URL to the local backend on your computer. By default, transcript analysis stays local. If you configure `GEMINI_API_KEY`, transcript text is sent to the Google Gemini API for analysis. Do not put an API key in extension JavaScript or share it publicly.
