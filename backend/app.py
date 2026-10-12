from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
import os, re, json, urllib.request

app = Flask(__name__)
CORS(app, resources={r"/analyze": {"origins": "*"}})

TECHNOLOGIES = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "SQL", "HTML", "CSS",
    "React", "Next.js", "Node.js", "Express.js", "Django", "Flask", "FastAPI",
    "Streamlit", "Tailwind CSS", "Bootstrap", "MongoDB", "MySQL", "PostgreSQL",
    "SQLite", "Firebase", "Redis", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "Git", "GitHub", "REST API", "GraphQL", "TensorFlow", "PyTorch", "Scikit-learn",
    "Pandas", "NumPy", "Matplotlib", "Power BI", "Tableau", "Machine Learning",
    "Deep Learning", "LangChain", "OpenAI API", "LLM", "RAG", "Vector Database",
    "Pandas", "Apache Spark", "Airflow", "Linux", "Bash", "Postman", "Figma"
]

@app.get("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "YouTube Learning Analyzer backend is running.",
        "endpoint": "POST /analyze"
    })

def video_id_from_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in ("youtu.be", "www.youtu.be"):
        vid = parsed.path.strip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if parsed.path == "/watch":
            vid = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/embed/", "/shorts/", "/live/")):
            parts = parsed.path.strip("/").split("/")
            vid = parts[1] if len(parts) > 1 else ""
        else:
            vid = ""
    else:
        raise ValueError(
            "It is just a prototype for YouTube; in future it will work for every video."
        )
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or ""):
        raise ValueError("That does not look like a valid YouTube video URL.")
    return vid

def get_transcript(video_id):
    # Works with current youtube-transcript-api versions.
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    candidates = list(transcript_list)
    if not candidates:
        raise RuntimeError("No captions/transcripts are available for this video.")
    chosen = None
    # Prefer English, then manually created captions, then any available language.
    for item in candidates:
        if getattr(item, "language_code", "").startswith("en") and not getattr(item, "is_generated", False):
            chosen = item
            break
    if chosen is None:
        for item in candidates:
            if getattr(item, "language_code", "").startswith("en"):
                chosen = item
                break
    if chosen is None:
        chosen = candidates[0]
    fetched = chosen.fetch()
    lines = []
    for entry in fetched:
        text = getattr(entry, "text", None)
        if text is None and isinstance(entry, dict):
            text = entry.get("text", "")
        if text:
            lines.append(str(text).replace("\\n", " "))
    return " ".join(lines), getattr(chosen, "language", "unknown")

def heuristic_analysis(transcript):
    lower = transcript.lower()
    tutorial_signals = re.findall(
        r"\b(tutorial|how to|let's build|we will build|we're building|install|"
        r"configure|code|programming|develop|developing|step by step)\b",
        lower
    )
    non_tutorial_signals = re.findall(
        r"\b(song|music|lyrics|official video|trailer|teaser|comedy|standup|"
        r"podcast|interview|vlog|gameplay|highlights|news)\b",
        lower
    )
    is_tutorial = len(tutorial_signals) >= 2 or (
        bool(tutorial_signals) and len(tutorial_signals) >= len(non_tutorial_signals)
    )
    found = []
    # Longer/multiword labels first to avoid missing familiar technology names.
    for tech in sorted(set(TECHNOLOGIES), key=len, reverse=True):
        pattern = re.escape(tech).replace(r"\ ", r"\s+")
        if re.search(r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])", transcript, re.I):
            found.append(tech)
    # Avoid a giant list; maintain useful order by first mention.
    found.sort(key=lambda t: lower.find(t.lower()))
    topics = []
    topic_patterns = [
        ("Project setup and environment", r"install|setup|environment|dependencies|getting started"),
        ("Frontend and user interface", r"frontend|user interface|component|css|html|react|tailwind"),
        ("Backend and APIs", r"backend|api|endpoint|server|route|request|response"),
        ("Database and data handling", r"database|sql|mongodb|postgres|mysql|schema|query"),
        ("Model training or AI integration", r"train|model|machine learning|llm|prompt|embedding|openai|prediction"),
        ("Testing and debugging", r"test|debug|error|fix|bug|validation"),
        ("Deployment", r"deploy|deployment|hosting|docker|aws|cloud|production"),
    ]
    for label, pattern in topic_patterns:
        if re.search(pattern, lower):
            topics.append(label)
    # Extract probable project name/description around project-introduction phrases.
    sentences = re.split(r"(?<=[.!?])\s+", transcript)
    candidates = [s.strip() for s in sentences if re.search(
        r"\b(build|building|create|creating|develop|developing|project|we're going to make|we will make)\b", s, re.I)]
    project = " ".join(candidates[:3]).strip()
    if len(project) > 700:
        project = project[:697] + "..."
    if not project:
        project = "The transcript does not contain a clear project-introduction phrase. Review the transcript below to identify the project."
    summary = "This is a keyword-based first pass. It identifies technologies and themes mentioned in captions, but cannot reliably tell whether each tool is taught in depth or merely mentioned."
    return found[:30], topics, project, summary, is_tutorial

def gemini_analysis(transcript):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    prompt = (
        "Analyze this YouTube transcript for a learner. Return ONLY valid JSON with keys: "
        "title (short descriptive title inferred from transcript, or empty), "
        "is_tutorial (boolean; true only when the video teaches or demonstrates a technical project), "
        "technologies (array of technologies actually taught or used, each with a concise reason), "
        "project (what is being built, features, and intended purpose in 2-5 sentences; say unclear if needed), "
        "topics (array of 4-10 concise learning topics in order), "
        "summary (5-8 useful bullet-like sentences as a single string). "
        "Distinguish tools actually used from tools only mentioned. Do not invent details. "
        "Transcript:\n" + transcript[:100000]
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }).encode()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = json.loads(response.read().decode())
    candidates = raw.get("candidates", [])
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    output_text = "".join(part.get("text", "") for part in parts)
    if not output_text:
        raise RuntimeError("Gemini returned an empty analysis.")
    result = json.loads(output_text)
    techs = result.get("technologies", [])
    techs = [x if isinstance(x, str) else f"{x.get('name', 'Technology')}: {x.get('reason', '')}" for x in techs]
    return result, techs

@app.post("/analyze")
def analyze():
    try:
        body = request.get_json(silent=True) or {}
        url = (body.get("url") or "").strip()
        video_id = video_id_from_url(url)
        transcript, language = get_transcript(video_id)
        if not transcript.strip():
            return jsonify(error="The transcript was empty."), 422
        title = ""
        try:
            technologies, topics, project, summary, is_tutorial = heuristic_analysis(transcript)
            ai_result = gemini_analysis(transcript)
            if ai_result:
                result, technologies = ai_result
                is_tutorial = bool(result.get("is_tutorial", is_tutorial))
                topics = result.get("topics", topics)
                project = result.get("project", project)
                summary = result.get("summary", summary)
                title = result.get("title", "")
        except Exception as exc:
            # Keep the basic keyword analysis usable if AI configuration fails.
            technologies, topics, project, summary, is_tutorial = heuristic_analysis(transcript)
            if os.getenv("GEMINI_API_KEY"):
                summary += f" AI analysis was unavailable ({type(exc).__name__}); showing keyword-based results."
        return jsonify({
            "video_id": video_id, "title": title, "language": language,
            "is_tutorial": is_tutorial,
            "technologies": technologies, "topics": topics, "project": project,
            "summary": summary, "transcript": transcript,
            "transcript_words": len(transcript.split())
        })
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        message = str(exc)
        if "TranscriptsDisabled" in type(exc).__name__:
            message = "Captions are disabled for this video, so the transcript cannot be read."
        elif "NoTranscriptFound" in type(exc).__name__ or "NotTranslatable" in type(exc).__name__:
            message = "No usable transcript was found for this video."
        elif "VideoUnavailable" in type(exc).__name__:
            message = "The video is unavailable or private."
        elif not message:
            message = "Could not fetch transcript. Try a video with captions enabled."
        return jsonify(error=message), 422

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False)
