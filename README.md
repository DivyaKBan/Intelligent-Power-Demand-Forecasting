# ⚡ APU Intelligent Power Demand Forecasting
### Apex Power & Utilities — Dhanbad, Jharkhand, India

A full-stack, containerized electricity demand forecasting system that predicts load for every **10-minute block** of the day (144 blocks/24 hours) across three 132KV feeders using XGBoost, with live weather integration and localized Jharkhand holiday awareness.

---

## 📊 Model Performance

| Metric | Value |
|--------|-------|
| **R²** | **0.9989** |
| **MAPE** | **0.55%** |
| MAE | 353 kW |
| RMSE | 528 kW |
| Test period | Last 30 days of 2017 |
| Training rows | ~49,000 |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│    Single-Page Dashboard (Chart.js + vanilla JS)            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (REST)
┌──────────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                              │
│  /api/forecast  →  XGBoost model (xgb_model.pkl)           │
│  /api/weather   →  Open-Meteo API (Dhanbad coordinates)     │
│  /api/holidays  →  Jharkhand localized holiday calendar     │
│  /api/metrics   →  Model performance stats                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Trained Artifacts (backend/model/)              │
│  xgb_model.pkl     feature_cols.json                        │
│  holidays.json     seed_data.csv                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone / unzip the repository
cd apu_forecast

# Build and start
docker compose up --build

# Open the dashboard
open http://localhost:8000
```

The container includes all pre-trained model artifacts — no training step needed.

---

### Option 2: Local Python

**Prerequisites:** Python 3.10+

```bash
cd apu_forecast

# Install dependencies
pip install -r backend/requirements.txt

# Run the Jupyter notebook FIRST to train & save the model
cd notebook
jupyter notebook EDA_and_Model_Training.ipynb
# Run all cells — this creates backend/model/xgb_model.pkl

# Start the API server
cd ..
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Open in browser
open http://localhost:8000
```

---

## 📁 Project Structure

```
apu_forecast/
│
├── 📓 notebook/
│   └── EDA_and_Model_Training.ipynb    ← Full EDA, cleaning, training
│
├── 🐍 backend/
│   ├── main.py                          ← FastAPI app entry point
│   ├── requirements.txt
│   ├── routes/
│   │   ├── forecast.py                  ← /api/forecast endpoint
│   │   ├── weather.py                   ← /api/weather endpoint
│   │   └── holidays.py                  ← /api/holidays endpoint
│   └── model/
│       ├── xgb_model.pkl               ← Trained XGBoost (auto-generated)
│       ├── feature_cols.json            ← Feature list (43 features)
│       ├── holidays.json                ← Jharkhand holiday calendar
│       └── seed_data.csv               ← Last 7 days for lag priming
│
├── 🌐 frontend/
│   └── index.html                       ← Single-page dashboard
│
├── 📦 data/
│   └── Utility_consumption.csv         ← Source data (52,416 rows)
│
├── 🐳 Dockerfile
├── 🐳 docker-compose.yml
└── 📖 README.md
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/forecast` | GET | 144-block 24h forecast |
| `/api/forecast?date=2017-12-15` | GET | Forecast for specific date |
| `/api/weather` | GET | 24h weather for Dhanbad |
| `/api/holidays` | GET | Full holiday calendar |
| `/api/holidays?year=2017` | GET | Holidays filtered by year |
| `/api/metrics` | GET | Model performance metrics |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI (auto-generated) |

### Sample Response — `/api/forecast`
```json
{
  "forecast_date": "2017-12-31",
  "location": "Dhanbad, Jharkhand, India",
  "model": "XGBoost (MAPE=0.55%, R²=0.9989)",
  "total_blocks": 144,
  "summary": {
    "peak_load_kW": 68432.5,
    "min_load_kW": 41200.3,
    "avg_load_kW": 55890.1,
    "peak_time": "2017-12-31 19:00"
  },
  "forecast": [
    {
      "datetime": "2017-12-31 00:00",
      "block": 0,
      "total_load": 43210.5,
      "F1_load": 17284.2,
      "F2_load": 13827.4,
      "F3_load": 12098.9,
      "temperature": 12.3,
      "humidity": 72.0,
      "is_holiday": 0,
      "holiday_name": null
    }
    // ... 143 more blocks
  ]
}
```

---

## 🧠 Model Details

### Algorithm: XGBoost Regressor
Selected based on EDA findings:
- **Non-linear temperature-load relationship** confirmed in scatter plots → trees handle this natively
- **Tabular data** with heterogeneous features (time, weather, flags) — GBDTs outperform deep learning here
- **Interpretable** — feature importance charts available for grid operators
- **Fast** — trains in <30 seconds, artifact is ~1MB

### Feature Engineering (43 features)
| Category | Features |
|----------|----------|
| **Time** | Block (0–143), dow, month, quarter, dayofyear, weekofyear |
| **Cyclical** | sin/cos encodings for block, day-of-week, month |
| **Calendar flags** | is_weekend, is_monday, is_friday |
| **Holidays** | is_holiday, is_pre_holiday, is_post_holiday |
| **Weather** | temp, humidity, windspeed, cloudcover, temp², temp×humidity, cooling/heating degree |
| **Lag features** | lag_1, 6, 12, 144, 288, 1008 blocks |
| **Rolling stats** | mean, std, max over 6, 12, 144 blocks |
| **Feeder shares** | F1/F2/F3 proportion of total load |

### Localized Jharkhand Holidays (22 events)
Includes:
- **National**: Republic Day, Independence Day, Gandhi Jayanti, Labour Day
- **State**: Jharkhand Foundation Day, Hul Diwas
- **Tribal/Adivasi**: Karma Puja, Tusu Puja (Makar Sankranti)
- **Hindu**: Holi, Diwali, Chhath Puja, Durga Puja, Ganesh Chaturthi
- **Islamic**: Eid ul-Fitr, Eid ul-Adha
- **Industrial**: BCCL New Year closure, Vishwakarma Puja

---

## 🌐 Netlify Deployment (Frontend Only)

The frontend is a pure HTML/JS file — no build step needed.

1. Go to [netlify.com](https://netlify.com) → **Add new site** → **Deploy manually**
2. Drag and drop the `frontend/` folder
3. Edit `frontend/index.html` line:
   ```js
   const API = 'https://your-backend-url.com';  // change from window.location.origin
   ```
4. For the backend, deploy to **Render**, **Railway**, or **Fly.io** (all support Docker)

---

## 📈 Dashboard Features

- **Live 24-hour forecast chart** with feeder breakdown (F1/F2/F3)
- **Holiday annotations** on the forecast chart (orange dots)
- **Weather cards** — hourly temperature, humidity, wind, cloud cover (Open-Meteo)
- **Feeder donut chart** — percentage breakdown by 132KV feeder
- **Hourly pattern bar chart** — color-coded by load intensity
- **KPI cards** — peak, min, avg load + peak time
- **Holiday table** — all 22 Jharkhand events with type and demand impact rating
- **Model metrics card** — R², MAPE, MAE, RMSE

---

## ⚙️ Environment Notes

- Weather data: [Open-Meteo](https://open-meteo.com) — free, no API key required
- If the weather API is unreachable (offline/Docker without internet), the system falls back to seasonal averages
- The model uses seed data (last 7 days) to prime lag features for future forecasts

---

*Built for Exascale Deeptech & AI Pvt. Ltd. — Data Developer Intern Assignment*
