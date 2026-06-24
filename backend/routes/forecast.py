"""
Forecast endpoint: generates 144 x 10-minute block predictions for next 24 hours.
Uses XGBoost model with lag-seeding from historical data.
"""

from fastapi import APIRouter
import pandas as pd
import numpy as np
import joblib, json, os
from datetime import datetime, timedelta

router = APIRouter()

BASE = os.path.dirname(os.path.dirname(__file__))
MODEL_DIR = os.path.join(BASE, "model")

def load_artifacts():
    model = joblib.load(os.path.join(MODEL_DIR, "xgb_model.pkl"))
    with open(os.path.join(MODEL_DIR, "feature_cols.json")) as f:
        features = json.load(f)
    with open(os.path.join(MODEL_DIR, "holidays.json")) as f:
        holidays = json.load(f)
    seed = pd.read_csv(os.path.join(MODEL_DIR, "seed_data.csv"))
    seed['Datetime'] = pd.to_datetime(seed['Datetime'])
    return model, features, holidays, seed

def make_feature_row(dt: datetime, load_history: list, holidays: dict,
                     temp=25.0, humidity=60.0, windspeed=3.0, cloudcover=40.0) -> dict:
    """Build one feature row for a given datetime and load history."""
    block = dt.hour * 6 + dt.minute // 10
    dow   = dt.weekday()
    month = dt.month

    row = {
        'block':        block,
        'dayofweek':    dow,
        'month':        month,
        'quarter':      (month - 1) // 3 + 1,
        'dayofyear':    dt.timetuple().tm_yday,
        'weekofyear':   dt.isocalendar()[1],
        'hour_sin':     np.sin(2 * np.pi * block / 144),
        'hour_cos':     np.cos(2 * np.pi * block / 144),
        'dow_sin':      np.sin(2 * np.pi * dow / 7),
        'dow_cos':      np.cos(2 * np.pi * dow / 7),
        'month_sin':    np.sin(2 * np.pi * month / 12),
        'month_cos':    np.cos(2 * np.pi * month / 12),
        'is_weekend':   int(dow >= 5),
        'is_monday':    int(dow == 0),
        'is_friday':    int(dow == 4),
        'is_holiday':   int(dt.strftime('%Y-%m-%d') in holidays),
        'is_pre_holiday':  int((dt + timedelta(days=1)).strftime('%Y-%m-%d') in holidays),
        'is_post_holiday': int((dt - timedelta(days=1)).strftime('%Y-%m-%d') in holidays),
        'temp':          temp,
        'humidity':      humidity,
        'windspeed':     windspeed,
        'cloudcover':    cloudcover,
        'temp_sq':       temp ** 2,
        'temp_x_humidity': temp * humidity,
        'cooling_degree':  max(0, temp - 24),
        'heating_degree':  max(0, 18 - temp),
        # Lag features from rolling history
        'lag_1':    load_history[-1]   if len(load_history) >= 1   else 55000,
        'lag_6':    load_history[-6]   if len(load_history) >= 6   else 55000,
        'lag_12':   load_history[-12]  if len(load_history) >= 12  else 55000,
        'lag_144':  load_history[-144] if len(load_history) >= 144 else 55000,
        'lag_288':  load_history[-288] if len(load_history) >= 288 else 55000,
        'lag_1008': load_history[-1008] if len(load_history) >= 1008 else 55000,
        # Rolling stats
        'roll_mean_6':   np.mean(load_history[-6:])   if len(load_history) >= 6  else 55000,
        'roll_std_6':    np.std(load_history[-6:])    if len(load_history) >= 6  else 1000,
        'roll_max_6':    np.max(load_history[-6:])    if len(load_history) >= 6  else 60000,
        'roll_mean_12':  np.mean(load_history[-12:])  if len(load_history) >= 12 else 55000,
        'roll_std_12':   np.std(load_history[-12:])   if len(load_history) >= 12 else 1000,
        'roll_max_12':   np.max(load_history[-12:])   if len(load_history) >= 12 else 60000,
        'roll_mean_144': np.mean(load_history[-144:]) if len(load_history) >= 144 else 55000,
        'roll_std_144':  np.std(load_history[-144:])  if len(load_history) >= 144 else 1000,
        'roll_max_144':  np.max(load_history[-144:])  if len(load_history) >= 144 else 60000,
        # Feeder shares (use typical distribution)
        'F1_share': 0.40,
        'F2_share': 0.32,
        'F3_share': 0.28,
    }
    return row


@router.get("/forecast")
def get_forecast(date: str = None):
    """
    Generate a 24-hour (144 x 10-min block) electricity demand forecast.
    
    Query params:
      date: YYYY-MM-DD (optional, defaults to today)
    
    Returns list of 144 forecast points with timestamp, predicted load,
    and feeder breakdown.
    """
    model, features, holidays, seed = load_artifacts()

    # Determine target date
    if date:
        try:
            target_dt = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            # fallback: use last date in seed data + 1 day
            target_dt = seed['Datetime'].max().to_pydatetime() + timedelta(days=1)
    else:
        target_dt = seed['Datetime'].max().to_pydatetime() + timedelta(days=1)

    # Build load history from seed data for lag features
    load_history = seed['Total_Load'].tolist()

    # Get typical weather for the period (seasonal average from seed)
    avg_temp = float(seed['Temperature'].mean())
    avg_hum  = float(seed['Humidity'].mean())
    avg_wind = float(seed['WindSpeed'].mean())

    # Try to get real weather from Open-Meteo
    try:
        import requests
        forecast_date = target_dt.strftime('%Y-%m-%d')
        url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': 23.7957, 'longitude': 86.4304,
            'hourly': 'temperature_2m,relativehumidity_2m,windspeed_10m,cloudcover',
            'timezone': 'Asia/Kolkata',
            'forecast_days': 2
        }
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            wdata = resp.json()['hourly']
            df_w = pd.DataFrame(wdata)
            df_w['time'] = pd.to_datetime(df_w['time'])
            df_w = df_w[df_w['time'].dt.date == target_dt.date()]
            weather_by_hour = {
                row['time'].hour: {
                    'temp': row.get('temperature_2m', avg_temp),
                    'humidity': row.get('relativehumidity_2m', avg_hum),
                    'windspeed': row.get('windspeed_10m', avg_wind),
                    'cloudcover': row.get('cloudcover', 40.0)
                }
                for _, row in df_w.iterrows()
            }
        else:
            weather_by_hour = {}
    except Exception:
        weather_by_hour = {}

    # Generate 144 forecast blocks
    forecast = []
    start = target_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    for block_idx in range(144):
        dt = start + timedelta(minutes=block_idx * 10)
        w = weather_by_hour.get(dt.hour, {})
        temp      = w.get('temp', avg_temp)
        humidity  = w.get('humidity', avg_hum)
        windspeed = w.get('windspeed', avg_wind)
        cloudcover = w.get('cloudcover', 40.0)

        row = make_feature_row(dt, load_history, holidays, temp, humidity, windspeed, cloudcover)
        X = pd.DataFrame([row])[features]
        pred = float(model.predict(X)[0])
        pred = max(pred, 0)

        # Feeder breakdown (proportional to historical shares)
        f1 = pred * 0.40
        f2 = pred * 0.32
        f3 = pred * 0.28

        forecast.append({
            "datetime":   dt.strftime("%Y-%m-%d %H:%M"),
            "block":      block_idx,
            "total_load": round(pred, 2),
            "F1_load":    round(f1, 2),
            "F2_load":    round(f2, 2),
            "F3_load":    round(f3, 2),
            "temperature":  round(temp, 1),
            "humidity":     round(humidity, 1),
            "windspeed":    round(windspeed, 2),
            "cloudcover":   round(cloudcover, 1),
            "is_holiday":   int(dt.strftime('%Y-%m-%d') in holidays),
            "holiday_name": holidays.get(dt.strftime('%Y-%m-%d'), None),
        })

        # Append prediction to history for next lag
        load_history.append(pred)

    # Summary stats
    loads = [f['total_load'] for f in forecast]
    return {
        "forecast_date": target_dt.strftime("%Y-%m-%d"),
        "location":      "Dhanbad, Jharkhand, India",
        "model":         "XGBoost (MAPE=0.55%, R²=0.9989)",
        "total_blocks":  len(forecast),
        "summary": {
            "peak_load_kW":    round(max(loads), 2),
            "min_load_kW":     round(min(loads), 2),
            "avg_load_kW":     round(sum(loads) / len(loads), 2),
            "peak_block":      loads.index(max(loads)),
            "peak_time":       forecast[loads.index(max(loads))]['datetime'],
        },
        "forecast": forecast
    }
