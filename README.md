# BuildWise AI — Multimodal Construction Intelligence Platform

BuildWise AI is a lightweight, full-stack construction decision-support demo. It combines a responsive web interface, a FastAPI backend, and Google's hosted Gemini API. It is designed to avoid loading large AI models onto the web server, which helps reduce memory pressure on small hosting instances.

## Features

- **Site safety review:** Upload a construction-site photo and describe the situation to receive potential hazards and suggested precautions.
- **Crack and surface review:** Upload a close-up photo and receive cautious visual observations and recommended next steps.
- **Project planner:** Generate project phases, dependencies, quality checks, and risks from a short project brief.
- **Property valuation estimator:** Calculate a transparent estimate from area and a user-provided price per unit. This is a calculator, not an appraisal.
- **Construction assistant:** Ask a construction-related question and receive structured guidance.
- **Weather-aware advisory:** Look up current forecast information through Open-Meteo and request practical planning considerations.
- **Responsive dashboard:** Feature navigation, status indicators, sample prompts, and a browser-local recent activity list.

## Technology

- Python 3.11+
- FastAPI + Uvicorn
- Gemini API (hosted inference; no local LLM)
- Pillow for image resizing
- HTML, CSS, and vanilla JavaScript
- Open-Meteo forecast and geocoding APIs

## Project structure

```text
Multimodal_Construction_Intelligence_Platform_v2/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── static/
│       └── index.html
├── .env.example
├── .gitignore
├── Dockerfile
├── render.yaml
├── requirements.txt
└── README.md
```

## Requirements

- Windows 10/11, macOS, or Linux
- Python 3.11 or later
- VS Code (recommended)
- A Google AI Studio Gemini API key for AI features
- Internet access

## Run locally on Windows / VS Code

Open the extracted project folder in VS Code, then open **Terminal → New Terminal**.

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt terminal and run:

```bat
.venv\Scripts\activate.bat
```

### 2. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Gemini

Copy `.env.example` to `.env` in the project root. In PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace `replace_with_your_gemini_api_key` with your actual key from Google AI Studio: https://aistudio.google.com/apikey

**Keep `.env` private. Never commit it to GitHub or paste your API key into a public issue.**

### 4. Start the application

```powershell
python -m uvicorn app.main:app --reload
```

Open:
- App: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

The dashboard and non-AI valuation calculator can open without a Gemini key. AI endpoints need a valid key. Weather lookup uses Open-Meteo and needs internet access.

## Push to GitHub

Create an empty repository on GitHub first. Then, in the project terminal:

```powershell
git init
git add .
git commit -m "Build BuildWise AI construction intelligence platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Replace the remote URL with your repository URL. If `origin` already exists, use:

```powershell
git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Before pushing, run `git status` and confirm `.env` is not listed.

## Deploy on Render

The repository includes a `Dockerfile` and `render.yaml`.

1. Push the project to GitHub.
2. Sign in to https://render.com and choose **New + → Web Service**.
3. Connect your GitHub repository.
4. Choose Docker runtime (Render should detect the Dockerfile).
5. Keep the root directory blank.
6. Choose the Free plan if you want to start without cost; free resources may sleep when idle and are limited.
7. Add environment variable `GEMINI_API_KEY` with your real Gemini key. Do not include quote marks.
8. Keep `GEMINI_MODEL` as `gemini-2.5-flash` and `MAX_UPLOAD_MB` as `8`.
9. Deploy and wait for the build to finish.
10. Test `https://YOUR-RENDER-URL/api/health`, then open the root URL and test each feature.

The included `render.yaml` may also be used as a Render Blueprint. If you configure the service manually, use the Docker runtime and the included Dockerfile.

## OOM-conscious design

- AI inference runs through the hosted Gemini API; no local LLM weights are downloaded.
- No PyTorch, TensorFlow, vector database, or embedding model is installed.
- Image uploads are capped and resized to a maximum 1280-pixel dimension before being sent to Gemini.
- Dependencies are intentionally small, and Docker pip installation disables its cache.
- API calls have timeouts and the app handles upstream failures.

These measures reduce memory use but **cannot guarantee zero OOM failures** on every host. Free-tier memory limits, traffic, image payloads, and provider behavior still matter.

## API endpoints

- `GET /api/health` — application and Gemini configuration status
- `POST /api/analyze/image` — image plus prompt, with `mode=safety` or `mode=cracks`
- `POST /api/plan` — project planning
- `POST /api/assistant` — construction question and answer
- `POST /api/weather` — city forecast and optional construction advice
- `POST /api/valuation` — local estimate calculator

## Important limitations

- AI image analysis is a preliminary aid, not a certified safety inspection or structural engineering assessment.
- The valuation output is based only on values entered by the user and is not a professional appraisal or market-data feed.
- Weather information is supplied by Open-Meteo and may not reflect hyperlocal site conditions.
- Gemini API availability, quotas, and billing policies apply. Check current terms in Google AI Studio.
- The generated project is a runnable implementation, but you should test it with your own API key and verify deployment logs before submitting it for evaluation.

## Suggested submission checklist

- [ ] Local application starts successfully
- [ ] `/api/health` responds
- [ ] Gemini key is configured only in `.env` locally / Render environment settings online
- [ ] Site safety image review tested
- [ ] Crack review tested
- [ ] Planner and assistant tested
- [ ] Weather lookup tested
- [ ] GitHub repository contains no secrets
- [ ] Render deployment is live
- [ ] Demo URL and GitHub URL added to Skillwallet
