from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models.shipment import RiskAnalysisDB, ShipmentDB

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("/")
def get_alerts(db: Session = Depends(get_db)):
    # Get latest analysis per shipment where risk > 70
    results = (
        db.query(RiskAnalysisDB, ShipmentDB)
        .join(ShipmentDB, RiskAnalysisDB.shipment_id == ShipmentDB.shipment_id)
        .filter(RiskAnalysisDB.risk_score >= 70)
        .order_by(desc(RiskAnalysisDB.risk_score))
        .all()
    )

    alerts = []
    for analysis, shipment in results:
        alerts.append({
            "shipment_id":   shipment.shipment_id,
            "origin":        shipment.origin,
            "destination":   shipment.destination,
            "carrier":       shipment.carrier,
            "sla_deadline":  str(shipment.sla_deadline),
            "risk_score":    analysis.risk_score,
            "risk_level":    analysis.risk_level,
            "recommendation":analysis.recommendation,
            "confidence":    analysis.confidence,
        })

    return {"total_alerts": len(alerts), "alerts": alerts}