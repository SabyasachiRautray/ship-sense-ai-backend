from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.shipment import (
    DeliveryPartnerDB, ShipmentDB, RiskAnalysisDB,
    PartnerCreate, PartnerOut, PartnerTokenResponse, LoginRequest
)
from services.auth import (
    hash_password, verify_password,
    create_access_token, get_current_partner, require_admin
)
from typing import List

router = APIRouter(prefix="/partners", tags=["Delivery Partners"])



@router.post("/", response_model=PartnerOut, status_code=201)
def create_partner(
    payload: PartnerCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    existing = db.query(DeliveryPartnerDB).filter(
        DeliveryPartnerDB.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    partner = DeliveryPartnerDB(
        name     = payload.name,
        email    = payload.email,
        phone    = payload.phone,
        password = hash_password(payload.password),
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


#  Partner login 
@router.post("/login", response_model=PartnerTokenResponse)
def partner_login(payload: LoginRequest, db: Session = Depends(get_db)):
    partner = db.query(DeliveryPartnerDB).filter(
        DeliveryPartnerDB.email == payload.email
    ).first()
    if not partner or not verify_password(payload.password, partner.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not partner.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")

    token = create_access_token({
        "sub":  partner.email,
        "role": "partner"         # ← different role from user
    })
    return {"access_token": token, "token_type": "bearer", "partner": partner}


#  Get all partners 
@router.get("/", response_model=List[PartnerOut])
def get_all_partners(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    return db.query(DeliveryPartnerDB).filter(
        DeliveryPartnerDB.is_active == True
    ).all()


# Get partner's own shipments 
@router.get("/my-shipments")
def get_my_shipments(
    db: Session = Depends(get_db),
    partner: DeliveryPartnerDB = Depends(get_current_partner)
):
    shipments = db.query(ShipmentDB).filter(
        ShipmentDB.partner_id == partner.id
    ).order_by(ShipmentDB.created_at.desc()).all()

    result = []
    for s in shipments:
        latest = db.query(RiskAnalysisDB).filter(
            RiskAnalysisDB.shipment_id == s.shipment_id
        ).order_by(RiskAnalysisDB.analyzed_at.desc()).first()

        result.append({
            "shipment_id":   s.shipment_id,
            "origin":        s.origin,
            "destination":   s.destination,
            "carrier":       s.carrier,
            "eta":           str(s.eta),
            "sla_deadline":  str(s.sla_deadline),
            "status":        s.status,
            "latest_analysis": {
                "risk_score":        latest.risk_score,
                "risk_level":        latest.risk_level,
                "recommendation":    latest.recommendation,
                "recommended_route": latest.recommended_route,
                "confidence":        latest.confidence,
            } if latest else None
        })

    return {"partner": partner.name, "shipments": result}


#  Assign partner to a shipment 
@router.patch("/assign/{shipment_id}")
def assign_partner(
    shipment_id: str,
    partner_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    shipment = db.query(ShipmentDB).filter(
        ShipmentDB.shipment_id == shipment_id
    ).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    partner = db.query(DeliveryPartnerDB).filter(
        DeliveryPartnerDB.id == partner_id
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    shipment.partner_id = partner_id
    db.commit()
    return {"message": f"Partner {partner.name} assigned to {shipment_id}"}