import base64
import io
import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

APP_NAME = "BuildWise AI"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
try:
    MAX_UPLOAD_MB = max(1, min(int(os.getenv("MAX_UPLOAD_MB", "8")), 12))
except ValueError:
    MAX_UPLOAD_MB = 8

app = FastAPI(
    title="BuildWise AI — Multimodal Construction Intelligence",
    version="2.0.0",
    description="Lightweight construction decision-support demo powered by hosted Gemini AI.",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


class PlanRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=120)
    project_type: str = Field(min_length=1, max_length=100)
    duration_weeks: int = Field(ge=1, le=260)
    budget: Optional[float] = Field(default=None, ge=0)
    brief: str = Field(min_length=10, max_length=4000)


class AssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    context: str = Field(default="", max_length=2000)


class ValuationRequest(BaseModel):
    area: float = Field(gt=0, le=100000000)
    rate_per_sqft: float = Field(gt=0, le=100000000)
    currency: str = Field(default="INR", max_length=8)
    location: str = Field(default="", max_length=150)
    condition_factor: float = Field(default=1.0, ge=0.5, le=1.5)


class WeatherRequest(BaseModel):
    city: str = Field(min_length=1, max_length=100)
    activity: str = Field(default="general construction", max_length=300)


def gemini_text(prompt: str, image_part: Optional[dict] = None) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY.lower().startswith("replace_"):
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured. Add GEMINI_API_KEY to your local .env file or Render environment variables.",
        )
    parts = [{"text": prompt}]
    if image_part:
        parts.append(image_part)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    try:
        response = requests.post(
            url,
            json={
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {
                    "temperature": 0.25,
                    "maxOutputTokens": 1400,
                    "responseMimeType": "application/json",
                },
            },
            timeout=(8, 50),
        )
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Could not reach the Gemini API. Check the network and try again.")
    if response.status_code >= 400:
        message = "Gemini request failed."
        try:
            message = response.json().get("error", {}).get("message", message)
        except ValueError:
            pass
        raise HTTPException(status_code=502, detail=f"Gemini API error: {message[:350]}")
    try:
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Gemini returned an unexpected response. Please try again.")


def json_prompt(instructions: str) -> str:
    return (
        "You are BuildWise AI, a cautious construction decision-support assistant. "
        "Return valid JSON only with keys: title (string), summary (string), "
        "findings (array of strings), recommendations (array of strings), "
        "risks (array of strings), limitations (array of strings). "
        "Keep advice practical, concise, and clearly distinguish observations from assumptions. "
        "Do not claim to certify safety, diagnose structural integrity, or replace a licensed professional. "
        "If information is missing, say so. Instructions: " + instructions
    )


def process_image(data: bytes):
    if not data:
        raise HTTPException(status_code=400, detail="Please select an image.")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Image must be {MAX_UPLOAD_MB} MB or smaller.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image = image.convert("RGB")
            image.thumbnail((1280, 1280))
            out = io.BytesIO()
            image.save(out, format="JPEG", quality=82, optimize=True)
            return base64.b64encode(out.getvalue()).decode("ascii")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="That file could not be read as an image. Try a JPG, PNG, or WebP image.")


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = BASE_DIR / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    configured = bool(GEMINI_API_KEY and not GEMINI_API_KEY.lower().startswith("replace_"))
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": "2.0.0",
        "gemini_configured": configured,
        "gemini_model": GEMINI_MODEL,
        "max_upload_mb": MAX_UPLOAD_MB,
    }


@app.post("/api/analyze/image")
async def analyze_image(
    mode: str = Form(...),
    description: str = Form(default=""),
    image: UploadFile = File(...),
):
    if mode not in {"safety", "cracks"}:
        raise HTTPException(status_code=400, detail="Mode must be safety or cracks.")
    content_type = (image.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload an image file.")
    data = await image.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    image_data = process_image(data)
    if mode == "safety":
        instructions = (
            "Review this construction-site photo for visible potential hazards. "
            "Do not infer unseen conditions. Return JSON using the required schema. "
            f"User context: {description or 'No extra context provided.'} "
            "Mention urgent-looking visible hazards first, suggest practical precautions, and state that a competent site professional must verify."
        )
    else:
        instructions = (
            "Review this close-up construction surface photo for visible cracks or surface defects. "
            "Do not infer depth, load capacity, cause, or structural safety from an image alone. "
            f"User context: {description or 'No extra context provided.'} "
            "Describe only visible features, suggest documentation and when to consult a qualified structural engineer."
        )
    raw = gemini_text(
        json_prompt(instructions),
        {"inline_data": {"mime_type": "image/jpeg", "data": image_data}},
    )
    return {"mode": mode, "result": raw}


@app.post("/api/plan")
def create_plan(request: PlanRequest):
    budget = f"{request.budget:,.2f}" if request.budget is not None else "not supplied"
    prompt = json_prompt(
        f"Create an initial project plan for project '{request.project_name}', "
        f"type '{request.project_type}', target duration {request.duration_weeks} weeks, "
        f"budget {budget}. Project brief: {request.brief}. "
        "Include sensible phases, dependencies, deliverables, quality checks, and risks. "
        "Treat timelines as a draft requiring review by the project manager."
    )
    return {"result": gemini_text(prompt)}


@app.post("/api/assistant")
def assistant(request: AssistantRequest):
    prompt = json_prompt(
        "Answer this construction-related question clearly for a student or site coordinator. "
        f"Question: {request.question}. Additional context: {request.context or 'None supplied'}. "
        "Give actionable steps, relevant safety caveats, and identify when an expert is required."
    )
    return {"result": gemini_text(prompt)}


@app.post("/api/valuation")
def valuation(request: ValuationRequest):
    base = request.area * request.rate_per_sqft
    estimated = base * request.condition_factor
    return {
        "currency": request.currency.upper(),
        "area": request.area,
        "rate_per_sqft": request.rate_per_sqft,
        "condition_factor": request.condition_factor,
        "base_estimate": round(base, 2),
        "estimated_value": round(estimated, 2),
        "location": request.location,
        "note": "Arithmetic estimate based only on your inputs; not a market valuation or professional appraisal.",
    }


@app.post("/api/weather")
def weather_advice(request: WeatherRequest):
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": request.city, "count": 1, "language": "en", "format": "json"},
            timeout=(5, 12),
        )
        geo.raise_for_status()
        places = geo.json().get("results") or []
        if not places:
            raise HTTPException(status_code=404, detail="City not found. Try a nearby larger city.")
        place = places[0]
        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                "daily": "precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
                "forecast_days": 1,
                "timezone": "auto",
            },
            timeout=(5, 12),
        )
        forecast.raise_for_status()
        data = forecast.json()
        current = data.get("current", {})
        daily = data.get("daily", {})
        advice = []
        rain_probability = (daily.get("precipitation_probability_max") or [0])[0]
        wind = current.get("wind_speed_10m", 0)
        rain = current.get("precipitation", 0)
        if rain_probability >= 60 or rain > 0:
            advice.append("Review drainage, wet-surface slip risks, concrete protection, and weather-sensitive work before proceeding.")
        if wind >= 30:
            advice.append("Review lifting operations, scaffolds, and work at height against the site's approved wind limits.")
        if not advice:
            advice.append("Conditions shown do not trigger these simple weather flags, but check the site forecast and your approved method statement.")
        return {
            "city": f"{place.get('name', request.city)}, {place.get('country', '')}".strip(", "),
            "current": current,
            "today": {
                "precipitation_probability_max": rain_probability,
                "precipitation_sum_mm": (daily.get("precipitation_sum") or [None])[0],
                "wind_speed_max_kmh": (daily.get("wind_speed_10m_max") or [None])[0],
            },
            "activity": request.activity,
            "advisory": advice,
            "source": "Open-Meteo",
            "note": "General planning prompts only. Follow local warnings and the project's approved safety procedures.",
        }
    except HTTPException:
        raise
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Weather service is temporarily unavailable. Please try again.")
