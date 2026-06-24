"""
Holidays endpoint: returns localized holidays for Dhanbad, Jharkhand.
"""

from fastapi import APIRouter
import json, os
from datetime import datetime

router = APIRouter()
BASE = os.path.dirname(os.path.dirname(__file__))

@router.get("/holidays")
def get_holidays(year: int = None):
    """
    Return localized holiday list for Dhanbad, Jharkhand.
    Includes national, state (Jharkhand), tribal, and industrial holidays.
    """
    holiday_file = os.path.join(BASE, "model", "holidays.json")
    with open(holiday_file) as f:
        holidays = json.load(f)

    if year:
        holidays = {k: v for k, v in holidays.items() if k.startswith(str(year))}

    formatted = []
    for date_str, name in sorted(holidays.items()):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        formatted.append({
            "date":      date_str,
            "name":      name,
            "day":       dt.strftime("%A"),
            "month":     dt.strftime("%B"),
            "type":      classify_holiday(name)
        })

    return {
        "location": "Dhanbad, Jharkhand, India",
        "total":    len(formatted),
        "note":     "Includes national, state (Jharkhand), tribal (Santali/Adivasi), Islamic, and industrial (BCCL) holidays",
        "holidays": formatted
    }

def classify_holiday(name: str) -> str:
    national = {"Republic Day", "Independence Day", "Gandhi Jayanti", "Labour Day"}
    tribal   = {"Karma Puja", "Hul Diwas", "Tusu Puja"}
    islamic  = {"Eid ul-Fitr", "Eid ul-Adha"}
    industrial = {"BCCL Closure", "Vishwakarma Puja"}
    if any(n in name for n in national):  return "National"
    if any(n in name for n in tribal):    return "Tribal/Adivasi"
    if any(n in name for n in islamic):   return "Islamic"
    if any(n in name for n in industrial):return "Industrial"
    if "Jharkhand" in name:               return "State"
    return "Hindu/Festival"
