# Personal AI Creator

Your own private, multipurpose AI program: chat, a trailer maker, a
music video maker, a sandboxed file assistant, a whitelisted computer
assistant, optional voice in/out, and a password-protected web GUI —
all running locally, under your control.

## Setup

1. Install Python 3.10+ and [ffmpeg](https://ffmpeg.org) (`apt install
   ffmpeg` / `brew install ffmpeg` / download for Windows).
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Get an API key from https://console.anthropic.com (or swap in
   another provider — see `ai_brain/ai_client.py`).
4. Copy `.env.example` to `.env` and paste your key in.
5. Run the CLI:
   ```
   python main.py
   ```
   or run the web version — backend and frontend are separate, so start
   both:
   ```
   python -m backend.app
   ```
   then in another terminal, serve the frontend as static files, e.g.:
   ```
   python -m http.server 8080 --directory frontend
   ```
   and visit http://localhost:8080. (Opening `frontend/index.html`
   directly from disk also works for local-only use.)

## Project structure

```
personal-ai/
├── main.py                    # CLI chat loop
├── ai_brain/
│   ├── config.py               # settings, loads .env, approved-apps list
│   ├── memory.py                # chat history, saved to disk
│   ├── commands.py              # "/command" system — the extension point
│   ├── ai_client.py             # talks to the AI API — swap providers here
│   ├── auth.py                  # password hashing + verification
│   ├── files.py                  # sandboxed file assistant
│   ├── computer.py               # whitelisted app launcher
│   ├── voice.py                   # speech in/out (optional deps)
│   └── creator/
│       ├── scene_planner.py        # AI plans trailer scenes
│       ├── music_video_planner.py  # AI plans music video scenes
│       ├── audio_analysis.py       # finds cut points in a song
│       ├── ffmpeg_tools.py         # the actual video/audio assembly
│       ├── trailer_builder.py      # orchestrates a trailer build
│       └── music_video_builder.py  # orchestrates a music video build
├── backend/
│   └── app.py                  # Flask JSON API — no HTML here at all
├── frontend/
│   ├── config.js                # the one place that knows the backend's URL
│   ├── api.js                   # all fetch() calls + token storage go through here
│   ├── index.html, login.html, projects.html
│   └── style.css
├── data/
│   ├── chat_history.json       # created automatically
│   └── projects/<name>/        # your media in, finished MP4 out
├── requirements.txt             # core dependencies
├── requirements-voice.txt        # optional: mic/speaker support
├── .env.example
└── .gitignore
```

## Commands (CLI and web GUI both use these)

| Command | What it does |
|---|---|
| `/help` | List commands |
| `/clear` | Clear chat memory |
| `/trailer <project> \| <idea>` | Build a trailer from images in `data/projects/<project>/media/` |
| `/musicvideo <project> \| <theme>` | Build a music video synced to a song in the same folder |
| `/file list [dir]`, `new <path>`, `mkdir <path>`, `rename <path> <name>`, `mv <path> <new>`, `rm <path>` | Sandboxed file operations, confined to `data/projects/` |
| `/open <name>` (or `/open list`) | Launch an app you've explicitly approved — see below |
| `/voice` | One spoken exchange (needs `requirements-voice.txt`) |
| `/quit` | Exit (CLI only) |
| anything else | Sent to the AI as a normal chat message |

## Trailer maker

1. Put your images (and optionally one music file) in:
   ```
   data/projects/mymovie/media/
   ```
2. Run: `/trailer mymovie | A lone astronaut discovers she is not alone on Mars`
3. The AI plans scene order/captions/durations; ffmpeg builds each
   image into a slow-zoom clip with a burned-in caption, crossfades
   them together, and mixes in your music with a fade-out. Output:
   `data/projects/mymovie/trailer.mp4`.

## Music video maker

1. Put your images and **exactly one song** in:
   ```
   data/projects/mysong/media/
   ```
2. Run: `/musicvideo mysong | <lyrics or a theme/mood description>`
3. Unlike the trailer, timing here comes from the song itself:
   `audio_analysis.py` decodes the track and finds real moments where
   the energy jumps (an approximation of beat/section detection,
   without needing a heavy library like librosa), and those become the
   scene cut points. The AI only decides which image and caption goes
   in which slot — the durations are locked to the song's actual
   structure. Cuts are hard (no crossfade) to stay tightly synced, and
   the full, untouched song is laid under the final video. Output:
   `data/projects/mysong/music_video.mp4`.

Both builders currently treat every input file as a still image — a
short video clip dropped into `media/` will be used as a single frozen
frame rather than played back. Making it use real moving footage is a
natural next upgrade.

## File assistant

Every path is resolved and checked against `data/projects/` before any
operation runs — `..`, absolute paths, or anything that would escape
that folder is refused outright, not just "restricted through the
CLI." Deleting requires the two-step `/file rm <path>` (shows what
would be deleted) then `/file rmconfirm <path>` (actually does it), so
nothing is destroyed by accident.

## Computer assistant

`/open` will run **nothing** until you explicitly whitelist it. Edit
`APPROVED_APPS` in `ai_brain/config.py`:
```python
APPROVED_APPS = {
    "notepad": r"C:\Windows\system32\notepad.exe",   # Windows
    "textedit": ["open", "-a", "TextEdit"],            # macOS
    "text_editor": "gedit",                              # Linux
}
```
Then `/open notepad` works and nothing not on this list does — there is
no general "run this command" ability by design.

## Voice

Optional — install with:
```
pip install -r requirements-voice.txt
```
Linux also needs system packages: `sudo apt install portaudio19-dev espeak`

**Honesty note:** this uses the standard, well-documented pattern for
`SpeechRecognition` (mic → text, via Google's free web API) and
`pyttsx3` (text → speech, offline). It could not be tested with real
audio hardware in the sandbox this project was built in — everything
else in this README describes things that were actually run and
verified; voice is the one piece you should treat as untested until you
try it on your own machine.

## Backend / frontend split

`backend/app.py` is a pure JSON API — it never renders HTML. `frontend/`
is fully static (plain HTML/CSS/JS, no build step) and talks to the API
over `fetch()`. This means:

- The backend can run anywhere (a server, a Raspberry Pi, your laptop)
  independent of where the frontend is hosted.
- The frontend is just files — open `index.html` directly, or serve it
  from any static host.
- Auth uses a **signed token**, not a cookie session — cookies get
  awkward once frontend and backend are different origins/ports. Login
  (`POST /api/login`) returns a token; the frontend stores it in
  `localStorage` (see `frontend/api.js`) and sends it as
  `Authorization: Bearer <token>` on every request after that. Tokens
  are signed with `itsdangerous` (already a Flask dependency, so no
  extra install) and expire after 7 days.
- If you host the frontend on a different origin than the default dev
  setup, set `FRONTEND_ORIGIN` (an env var for the backend) to that
  origin so CORS allows it — it defaults to `*` (any origin) for local
  development.
- Change `frontend/config.js`'s `API_BASE_URL` if the backend isn't at
  `http://localhost:5000`.

## Password protection

By default, both the CLI and the web GUI run **open** — no password
prompt — until you set one:
```
python -m ai_brain.auth set
```
This hashes your password (SHA-256, random per-install salt) and saves
only the hash to `.env` — the plaintext password is never written to
disk. Once set, the CLI asks for it on startup (3 attempts before
exiting) and the web GUI redirects to a login page until you sign in.

**Before hosting the web GUI anywhere reachable by others:**
- Set a password (above) — without one, anyone who reaches the API is
  in.
- `SECRET_KEY` in `backend/app.py` currently falls back to a placeholder
  string. Set a real `FLASK_SECRET_KEY` env var (any long random
  string) before hosting beyond localhost — without it, anyone who
  knows the placeholder could forge tokens.
- Set `FRONTEND_ORIGIN` to your actual frontend's origin instead of the
  default `*` once this isn't just local dev.
- Run the backend behind a real WSGI server (gunicorn, etc.) and HTTPS,
  not Flask's built-in dev server — it warns about this itself on
  startup.

## What's tested vs. what isn't

Built and actually run in the environment that produced this project:
chat loop, memory, all commands, trailer build (verified: valid 1280×720
MP4 with audio), music video build (verified: video duration matched
the source song's duration exactly), file assistant (verified: sandbox
escape attempts correctly blocked), computer assistant (verified:
unapproved apps correctly refused), and the full backend API — verified
via live requests: CORS preflight headers, unauthenticated 401s, wrong-
password rejection, correct-password token issuance, valid-token
success, forged-token rejection, and the download endpoint's
query-param token path.

Not testable in that environment, so treat as unverified until you try
them: voice I/O (no microphone/speaker in the sandbox), real
(non-still-image) video clip handling, and the frontend HTML/JS pages
in an actual browser (the backend API they call was fully tested via
direct requests, but no browser was available to click through the
pages themselves).

## Roadmap ideas from here

- Use real video clips as scenes, not just stills
- A proper beat-grid (not just onset/energy) for music videos, e.g. via
  librosa if you're comfortable installing it
- Multiple approved "computer" actions beyond just launching an app
  (e.g. reading a whitelisted folder)
- A project browser in the web GUI for re-editing an existing
  trailer/music-video's scene plan before rebuilding
