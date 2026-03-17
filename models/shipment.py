from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Enum, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from database import Base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# NEW: Delivery Partner DB Model 
class DeliveryPartnerDB(Base):
    __tablename__ = "delivery_partners"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)
    email       = Column(String(100), unique=True, nullable=False, index=True)
    phone       = Column(String(20), nullable=False)
    password    = Column(String(255), nullable=False)   # bcrypt hash
    is_active   = Column(Boolean, default=True)
    created_at  = Column(TIMESTAMP, server_default=func.now())


class ShipmentDB(Base):
    __tablename__ = "shipments"

    id              = Column(Integer, primary_key=True, index=True)
    shipment_id     = Column(String(50), unique=True, nullable=False)
    origin          = Column(String(100), nullable=False)
    destination     = Column(String(100), nullable=False)
    carrier         = Column(String(100), nullable=False)
    eta             = Column(DateTime, nullable=False)
    sla_deadline    = Column(DateTime, nullable=False)
    status          = Column(Enum("on_time", "at_risk", "delayed"), default="on_time")
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    partner_id      = Column(Integer, ForeignKey("delivery_partners.id"), nullable=True)  # ← NEW
    created_at      = Column(TIMESTAMP, server_default=func.now())


class RiskAnalysisDB(Base):
    __tablename__ = "risk_analysis"

    id                    = Column(Integer, primary_key=True, index=True)
    shipment_id           = Column(String(50), ForeignKey("shipments.shipment_id"), nullable=False)
    risk_score            = Column(Integer, nullable=False)
    risk_level            = Column(Enum("High", "Medium", "Low"), nullable=False)
    reasons               = Column(JSON, nullable=False)
    recommendation        = Column(String(255), nullable=False)
    estimated_delay_hours = Column(Float, nullable=False)
    confidence            = Column(String(10))
    weather_data          = Column(JSON)
    traffic_data          = Column(JSON)
    news_data             = Column(JSON)
    recommended_route     = Column(JSON)
    analyzed_at           = Column(TIMESTAMP, server_default=func.now())


class UserDB(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(100), unique=True, nullable=False, index=True)
    user_type  = Column(Enum("admin", "user"), nullable=False, default="user")
    password   = Column(String(255), nullable=False)
    is_active  = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


#Pydantic Schemas 

class ShipmentCreate(BaseModel):
    shipment_id:  str
    origin:       str
    destination:  str
    carrier:      str
    eta:          datetime
    sla_deadline: datetime
    user_id:      Optional[int] = None
    partner_id:   Optional[int] = None   

class ShipmentOut(BaseModel):
    id:           int
    shipment_id:  str
    origin:       str
    destination:  str
    carrier:      str
    eta:          datetime
    sla_deadline: datetime
    status:       str
    user_id:      Optional[int] = None
    partner_id:   Optional[int] = None   
    created_at:   datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    name:      str
    email:     str
    password:  str
    user_type: str = "user"

class UserOut(BaseModel):
    id:         int
    name:       str
    email:      str
    user_type:  str
    is_active:  bool
    created_at: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email:    str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserOut

#  NEW: Delivery Partner Schemas 
class PartnerCreate(BaseModel):
    name:     str
    email:    str
    phone:    str
    password: str

class PartnerOut(BaseModel):
    id:         int
    name:       str
    email:      str
    phone:      str
    is_active:  bool
    created_at: datetime

    class Config:
        from_attributes = True

class PartnerTokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    partner:      PartnerOut