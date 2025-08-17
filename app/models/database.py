from sqlalchemy import create_engine, Column, String, Float, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
import uuid
import enum
import secrets

SQLALCHEMY_DATABASE_URL = "sqlite:///./payments.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    RISK_CHECK = "risk_check"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SettlementRail(str, enum.Enum):
    ESWATINI_SWITCH = "eswatini_switch"
    VISA_DIRECT = "visa_direct"

class MerchantStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"
    REJECTED = "rejected"

class BusinessType(str, enum.Enum):
    RETAIL = "retail"
    RESTAURANT = "restaurant"
    GROCERY = "grocery"
    SERVICE = "service"
    ONLINE = "online"
    OTHER = "other"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="SZL")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    risk_score = Column(Float)
    settlement_rail = Column(Enum(SettlementRail))
    settlement_response = Column(Text)
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String, nullable=False)
    step = Column(String, nullable=False)
    status = Column(String, nullable=False)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String, unique=True, nullable=False)
    business_name = Column(String, nullable=False)
    business_type = Column(Enum(BusinessType), nullable=False)
    owner_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    id_number = Column(String, nullable=False)
    bank_account = Column(String)
    api_key = Column(String, unique=True, nullable=False)
    api_secret = Column(String, nullable=False)
    status = Column(Enum(MerchantStatus), default=MerchantStatus.PENDING)
    fee_rate = Column(Float, default=0.02)  # 2% default fee
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)

class QRCode(Base):
    __tablename__ = "qr_codes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String, nullable=False)
    qr_code_id = Column(String, unique=True, nullable=False)
    amount = Column(Float)  # None for dynamic amount
    description = Column(String)
    is_dynamic = Column(Boolean, default=False)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Float, default=0)
    max_usage = Column(Float)  # None for unlimited
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Also create auth tables
    from app.models.auth_models import Base as AuthBase
    AuthBase.metadata.create_all(bind=engine)