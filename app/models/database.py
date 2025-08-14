from sqlalchemy import create_engine, Column, String, Float, DateTime, Enum, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
import uuid
import enum

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)