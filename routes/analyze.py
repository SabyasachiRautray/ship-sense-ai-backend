from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.shipment import ShipmentDB, RiskAnalysisDB, DeliveryPartnerDB
from services.weather import get_weather
from services.traffic import get_traffic
from services.news import get_disruption_news
from services.gemini import analyze_with_gemini
from services.notify import notify_partner
import concurrent.futures

router = APIRouter(prefix="/analyze", tags=["Analysis"])


@router.post("/{shipment_id}")
def analyze_shipment(shipment_id: str, db: Session = Depends(get_db)):

    # 1. Fetch the shipment
    shipment = db.query(ShipmentDB).filter(
        ShipmentDB.shipment_id == shipment_id
    ).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    data = {
        "shipment_id":  shipment.shipment_id,
        "origin":       shipment.origin,
        "destination":  shipment.destination,
        "carrier":      shipment.carrier,
        "eta":          str(shipment.eta),
        "sla_deadline": str(shipment.sla_deadline),
    }

    # 2. Fetch all live signals in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        f_weather = executor.submit(get_weather, data["origin"])
        f_traffic = executor.submit(get_traffic, data["origin"], data["destination"])
        f_news    = executor.submit(get_disruption_news, data["origin"], data["destination"])

    try:
        weather = f_weather.result(timeout=15)
    except Exception:
        weather = {"description": "unavailable", "temp": "N/A", "wind_speed": 0, "severity": 0}

    try:
        traffic = f_traffic.result(timeout=15)
    except Exception:
        traffic = {"road": {"distance_km": 500, "duration_hours": 9.0, "estimated_delay_hours": 1.5, "congestion_level": "Medium", "alternate_route": None}, "air": {"available": False}, "water": {"available": False}, "fastest_mode": "road", "fastest_hours": 9.0}

    try:
        news = f_news.result(timeout=15)
    except Exception:
        news = []

    # 3. Run Llama analysis
    result = analyze_with_gemini(data, weather, traffic, news)

    # 4. Find all shipments on the same route
    same_route_shipments = db.query(ShipmentDB).filter(
        ShipmentDB.origin      == shipment.origin,
        ShipmentDB.destination == shipment.destination,
        ShipmentDB.shipment_id != shipment_id       # exclude current
    ).all()

    route_shipment_ids = [s.shipment_id for s in same_route_shipments] + [shipment_id]

    # 5. Delete ALL old analyses for every shipment on this route
    db.query(RiskAnalysisDB).filter(
        RiskAnalysisDB.shipment_id.in_(route_shipment_ids)
    ).delete(synchronize_session=False)

    # 6. Create ONE shared analysis and apply to ALL shipments on route
    for sid in route_shipment_ids:
        analysis = RiskAnalysisDB(
            shipment_id           = sid,
            risk_score            = result["risk_score"],
            risk_level            = result["risk_level"],
            reasons               = result["reasons"],
            recommendation        = result["recommendation"],
            estimated_delay_hours = result["estimated_delay_hours"],
            confidence            = result.get("confidence", "N/A"),
            weather_data          = weather,
            traffic_data          = traffic,
            news_data             = news,
            recommended_route     = result.get("recommended_route"),
        )
        db.add(analysis)

    # 7. Update status for ALL shipments on this route
    new_status = "at_risk" if result["risk_level"] in ("High", "Medium") else "on_time"

    for s in same_route_shipments:
        s.status = new_status

    shipment.status = new_status
    db.flush()

    # 8. Notify delivery partner if High Risk
    if result["risk_level"] == "High":
        # Find any partner assigned to shipments on this route
        partner_ids = set()
        for s in same_route_shipments + [shipment]:
            if s.partner_id:
                partner_ids.add(s.partner_id)

        for pid in partner_ids:
            partner = db.query(DeliveryPartnerDB).filter(
                DeliveryPartnerDB.id == pid
            ).first()
            if partner:
                notify_partner(
                    partner_name        = partner.name,
                    partner_email       = partner.email,
                    partner_phone       = partner.phone,
                    route               = f"{shipment.origin} → {shipment.destination}",
                    affected_shipments  = route_shipment_ids,
                    risk_score          = result["risk_score"],
                    recommendation      = result["recommendation"],
                    recommended_route   = result.get("recommended_route", {}),
                )

    db.commit()

    return {
        "shipment_id":          shipment_id,
        "route":                f"{shipment.origin} → {shipment.destination}",
        "affected_shipments":   route_shipment_ids,
        "partner_notified":     result["risk_level"] == "High" and len(partner_ids) > 0 if 'partner_ids' in locals() else False,
        "signals": {
            "weather": weather,
            "traffic": traffic,
            "news":    news,
        },
        "analysis": result
    }