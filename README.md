# YouTube Shorts Bot

Fully automated YouTube Shorts production pipeline: **AI Script (GPT-4o-mini / Groq fallback) → Edge TTS voiceover → FLUX AI images → Dynamic captions → FFmpeg 9:16 render → YouTube Data API upload**, scheduled daily via GitHub Actions.

---

## Architecture

```
scripts/run_short.py          ← Orchestrator
  pipeline/groq_script.py     ← Scriptwriting (Primary: GPT-4o-mini / Fallback: Groq Cloud)
  pipeline/edge_tts_synth.py  ← Edge TTS: audio synthesis + millisecond sentence boundary timings
  pipeline/images.py          ← DeAPI.ai (Flux) image generation with Pollinations fallback
  pipeline/captions.py        ← Mathematical word timing, 2-3 word bursts, Bebas Neue ASS captions
  pipeline/render_short.py    ← FFmpeg: 9:16 full-bleed Ken Burns zoom + audio mixing + burned subs
  pipeline/youtube_upload.py  ← YouTube Data API v3 upload
  pipeline/channel_presets.py ← Channel presets, viral prompt rules, and topic pools
```

---

## Key Features & Optimizations

* **Priority + Fallback Scripting**: Uses `gpt-4o-mini` (via OpenAI or ChatAnywhere) as the primary scriptwriter. If quota is exhausted or rate-limited, it automatically falls back to Groq Cloud without halting the pipeline.
* **Full-Bleed 9:16 Immersion**: Renders native vertical visuals (`768×1360` scaled to `1080×1920`) with **zero black letterboxing**.
* **Seamless Infinite Looping**: Scripts are mathematically structured so the final sentence connects grammatically back into the opening hook, maximizing watch time and retention past 100%.
* **TTS Emoji Sanitizer**: Automatic regex stripping removes emojis, stage cues (like `[whispers]`), and markdown symbols before audio generation, preventing voice synthesizer hallucinations.
* **High-Readability Typography**: High-contrast, bold Bebas Neue subtitles split into rapid 2–3 word bursts, positioned safely above the YouTube Shorts interface buttons.
* **Dynamic Visual Pacing**: Generates 8 scene beats per Short (~4.5 seconds per image) to keep viewers visually engaged and eliminate mid-video swipe-aways.

---

## Quick Start (Local Setup)

```bash
git clone <this-repo>
cd YT_Bot
python -m venv .venv

# Activate venv:
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Mac / Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Copy example environment configuration:
cp .env.example .env
# Edit .env and paste your API keys
```

### Helpful Test Utilities

* **Test Script Generation (5s test)**:
  ```bash
  python scripts/test_script_generation.py ghost_stories
  ```
* **Check Supported Models on your Key**:
  ```bash
  python scripts/check_openai_models.py
  ```
* **Test Free Image Generation**:
  ```bash
  python scripts/test_pollinations_images.py
  ```

---

## API Keys & Services

| Service | Free? | What It's Used For | Where to Get It |
| :--- | :--- | :--- | :--- |
| **OpenAI / ChatAnywhere** | ✅ Free tier | Primary scriptwriter (`gpt-4o-mini`) | [chatanywhere.org](https://chatanywhere.org) or [platform.openai.com](https://platform.openai.com) |
| **Groq Cloud** | ✅ Free tier | Backup scriptwriter (`openai/gpt-oss-20b`) | [console.groq.com/keys](https://console.groq.com/keys) |
| **DeAPI.ai** | ⚠️ Paid (~$0.01/video) | Primary Flux image generation | [deapi.ai](https://deapi.ai) |
| **Pollinations.ai** | ✅ 100% Free | Automatic image generation fallback | No key required |
| **Edge TTS** | ✅ 100% Free | Voiceover / speech synthesis | No key required (Microsoft Edge voices) |
| **FFmpeg** | ✅ Open source | 9:16 video compilation & subtitle burning | `winget install Gyan.FFmpeg` or `brew install ffmpeg` |
| **YouTube Data API** | ✅ Free | Automated video upload | Google Cloud Console |

---

## YouTube Upload Setup (One-Time)

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **YouTube Data API v3**: [Direct Link](https://console.cloud.google.com/apis/library/youtube.googleapis.com).
3. Go to **Credentials** → **Create Credentials** → **OAuth client ID** → choose **Desktop app**.
4. Download the JSON and save it as `secrets/client_secret.json`.
5. Run the authentication script:
   ```bash
   python scripts/youtube_auth.py
   ```
6. A browser opens → sign in to your YouTube channel's Google account → grant permission.
7. The credentials will be saved to `secrets/youtube_token.json` and printed to your terminal.

---

## GitHub Actions (Daily Autopilot)

The workflow runs daily on GitHub Actions at **10:00 UTC** (or manually via the **Actions** tab).

### Required Secrets in GitHub:
Navigate to **GitHub Repository → Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Required? | Value / Description |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | **Recommended** | Your ChatAnywhere or OpenAI API key (`sk-...`) |
| `OPENAI_BASE_URL` | Optional | `https://api.chatanywhere.org/v1` (defaults to ChatAnywhere if unset) |
| `OPENAI_MODEL` | Optional | `gpt-4o-mini` |
| `GROQ_API_KEY` | **Required** | Your Groq Cloud API key (used as automatic fallback) |
| `DEAPI_TOKEN` | Optional | Your DeAPI token (if unset, automatically uses free Pollinations) |
| `YT_CLIENT_ID` | Required | Shared OAuth client ID from `youtube_auth.py` |
| `YT_CLIENT_SECRET_VALUE` | Required | Shared OAuth client secret from `youtube_auth.py` |
| `YT_REFRESH_TOKEN` | Required | Refresh token from `youtube_auth.py` |

---

## Channel Presets

| Channel ID | Genre / Niche |
| :--- | :--- |
| `ghost_stories` | Spooky / paranormal horror storytime (infinite loop, 8 scenes) |
| `facts` | Surprising, verified facts (bilingual Hindi + English support) |
| `hindi_myth` | Respectful Hindi mythology & devotional shorts (calendar-based) |
| `school_story` | School drama & suspense storytime |
| `psych_tradeoff` | Everyday psychology, cognitive biases, and habit mechanics |
| `history_micro` | Focused historical anecdotes and forgotten turning points |

Customize or add new presets in [`pipeline/channel_presets.py`](file:///D:/YT/Horror/YT_Bot/pipeline/channel_presets.py).
