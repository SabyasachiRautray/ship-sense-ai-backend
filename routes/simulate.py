from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.shipment import ShipmentDB, RiskAnalysisDB

router = APIRouter(prefix="/simulate", tags=["Demo"])

@router.post("/disruption/{shipment_id}")
def simulate_disruption(shipment_id: str, db: Session = Depends(get_db)):
    """
    Demo button — instantly sets a shipment to HIGH risk
    with a realistic port strike scenario
    """
    shipment = db.query(ShipmentDB).filter(ShipmentDB.shipment_id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Inject a simulated high-risk analysis
    analysis = RiskAnalysisDB(
        shipment_id           = shipment_id,
        risk_score            = 92,
        risk_level            = "High",
        reasons               = [
            f"SIMULATED: Port strike detected at {shipment.origin}",
            "All outbound freight halted for 24–48 hours",
            f"No alternative routes available from {shipment.origin} to {shipment.destination}"
        ],
        recommendation        = "assign alternative carrier",
        estimated_delay_hours = 36.0,
        confidence            = "92%",
        weather_data          = {"description": "simulated", "severity": 0},
        traffic_data          = {"route": "blocked", "estimated_delay_hours": 36},
        news_data             = [{"title": f"Port workers strike at {shipment.origin}", "source": "Simulated News"}],
    )

    shipment.status = "delayed"
    db.add(analysis)
    db.commit()

    return {
        "message":    f"Disruption simulated for {shipment_id}",
        "risk_score": 92,
        "risk_level": "High",
        "recommendation": "assign alternative carrier"
    }