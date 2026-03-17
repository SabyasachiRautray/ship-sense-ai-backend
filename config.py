import os
from dotenv import load_dotenv

load_dotenv()



GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GNEWS_API_KEY   = os.getenv("GNEWS_API_KEY")
ORS_API_KEY     = os.getenv("ORS_API_KEY")
NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY")

DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "3306")
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME     = os.getenv("DB_NAME", "shipsense")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"