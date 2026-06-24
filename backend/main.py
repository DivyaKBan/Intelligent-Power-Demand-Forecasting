"""
APU Power Demand Forecasting — FastAPI Backend
Endpoints:
  GET /api/forecast    → 144 x 10-min blocks for next 24 hours
  GET /api/weather     → current + 24h weather for Dhanbad
  GET /api/holidays    → upcoming holidays
  GET /api/metrics     → model performance metrics
  GET /health          → health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os, json
from routes.forecast import router as forecast_router
from routes.weather  import router as weather_router
from routes.holidays import router as holidays_router

app = FastAPI(
    title="APU Power Demand Forecasting API",
    description="10-minute interval electricity demand forecasting for Dhanbad, Jharkhand",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — allow all origins for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(forecast_router, prefix="/api", tags=["Forecast"])
app.include_router(weather_router,  prefix="/api", tags=["Weather"])
app.include_router(holidays_router, prefix="/api", tags=["Holidays"])

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "APU Forecast API running. Visit /docs for API documentation."}

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "APU Power Demand Forecasting", "location": "Dhanbad, Jharkhand"}

@app.get("/api/metrics", tags=["Model"])
def model_metrics():
    """Return model performance metrics from training."""
    return {
        "model": "XGBoost Regressor",
        "test_period": "Last 30 days of 2017",
        "metrics": {
            "MAE_kW": 353,
            "RMSE_kW": 528,
            "MAPE_percent": 0.55,
            "R2": 0.9989
        },
        "features_used": 43,
        "training_rows": 49000,
        "target": "Total Load (sum of F1+F2+F3 132KV feeders)"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
