
import requests
from config import GNEWS_API_KEY

def get_disruption_news(origin: str, destination: str) -> list:
    try:
        query = f"port strike OR logistics delay OR transport disruption {origin} OR {destination}"

        url = "https://gnews.io/api/v4/search"
        res = requests.get(url, params={
            "q":        query,
            "token":    GNEWS_API_KEY,
            "lang":     "en",
            "max":      3,
            "sortby":   "publishedAt"
        }, timeout=5)

        articles = res.json().get("articles", [])
        return [
            {
                "title":     a["title"],
                "source":    a["source"]["name"],
                "published": a["publishedAt"],
                "url":       a["url"]
            }
            for a in articles[:3]
        ]

    except Exception as e:
        return [{"title": "News unavailable", "source": "error", "published": "", "url": ""}]
