import requests
from config import WEATHER_API_KEY

def get_weather(city: str) -> dict:
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        res = requests.get(url, params={
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "metric"
        }, timeout=5)
        data = res.json()
        return {
            "description": data["weather"][0]["description"],
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "severity": round(min(data["wind"]["speed"] / 3, 10), 1)
        }
    except Exception as e:
        return {"description": "unavailable", "severity": 0, "error": str(e)}