from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.shipment import ShipmentDB, ShipmentCreate, ShipmentOut ,RiskAnalysisDB
from services.auth import get_current_user
from models.shipment import UserDB
from typing import List

router = APIRouter(prefix="/shipments", tags=["Shipments"])


@router.get("/", response_model=List[ShipmentOut])
def get_all_shipments(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    
    if current_user.user_type == "admin":
        return db.query(ShipmentDB).order_by(ShipmentDB.created_at.desc()).all()
    return db.query(ShipmentDB).filter(
        ShipmentDB.user_id == current_user.id
    ).order_by(ShipmentDB.created_at.desc()).all()


@router.get("/user/{user_id}", response_model=List[ShipmentOut])
def get_shipments_by_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    # Users can only fetch their own, admin can fetch anyone's
    if current_user.user_type != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    shipments = db.query(ShipmentDB).filter(
        ShipmentDB.user_id == user_id
    ).order_by(ShipmentDB.created_at.desc()).all()

    if not shipments:
        return []

    return shipments


@router.get("/{shipment_id}", response_model=ShipmentOut)
def get_shipment(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    shipment = db.query(ShipmentDB).filter(
        ShipmentDB.shipment_id == shipment_id
    ).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if current_user.user_type != "admin" and shipment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return shipment

@router.post("/", response_model=ShipmentOut)
def create_shipment(
    payload: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    existing = db.query(ShipmentDB).filter(
        ShipmentDB.shipment_id == payload.shipment_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Shipment ID already exists")

    assigned_user_id = payload.user_id if (
        current_user.user_type == "admin" and payload.user_id
    ) else current_user.id

    shipment = ShipmentDB(
        shipment_id  = payload.shipment_id,
        origin       = payload.origin,
        destination  = payload.destination,
        carrier      = payload.carrier,
        eta          = payload.eta,
        sla_deadline = payload.sla_deadline,
        user_id      = assigned_user_id,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


@router.delete("/{shipment_id}")
def delete_shipment(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    shipment = db.query(ShipmentDB).filter(
        ShipmentDB.shipment_id == shipment_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if current_user.user_type != "admin" and shipment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete related risk analysis first
    db.query(RiskAnalysisDB).filter(
        RiskAnalysisDB.shipment_id == shipment_id
    ).delete()

    # Then delete shipment
    db.delete(shipment)

    db.commit()

    return {"message": f"Shipment {shipment_id} deleted"}