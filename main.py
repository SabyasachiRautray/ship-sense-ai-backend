import os
import ssl
import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from routes import shipments, analyze, alerts, simulate, auth,partners

# Auto-create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ShipSense AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(shipments.router)
app.include_router(analyze.router)
app.include_router(alerts.router)
app.include_router(simulate.router)
app.include_router(partners.router)

@app.get("/")
def root():
    return {"message": "ShipSense AI is running"}