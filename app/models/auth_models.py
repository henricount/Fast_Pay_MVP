from sqlalchemy import Column, String, DateTime, Boolean, Enum, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import uuid

Base = declarative_base()

class UserRole(PyEnum):
    CITIZEN = "citizen"
    MERCHANT = "merchant" 
    GOVERNMENT = "government"
    ADMIN = "admin"

class UserStatus(PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"

class VerificationStatus(PyEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=lambda: f"USER_{uuid.uuid4().hex[:8].upper()}")
    
    # Basic Information
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    
    # Personal Details
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    id_number = Column(String, unique=True, nullable=True)  # Eswatini national ID
    date_of_birth = Column(DateTime, nullable=True)
    
    # Address Information
    region = Column(String, nullable=True)  # Hhohho, Manzini, Shiselweni, Lubombo
    city = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    postal_code = Column(String, nullable=True)
    
    # Account Status
    role = Column(Enum(UserRole), default=UserRole.CITIZEN)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING)
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    
    # Verification
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True)
    phone_verification_code = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User {self.user_id}: {self.email}>"

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    session_id = Column(String, primary_key=True, default=lambda: f"SESS_{uuid.uuid4().hex}")
    user_id = Column(String, nullable=False, index=True)
    
    # Session Information
    access_token = Column(String, nullable=False, unique=True)
    refresh_token = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    
    # Device/Browser Information
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    device_fingerprint = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Session {self.session_id}: {self.user_id}>"

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    
    attempt_id = Column(String, primary_key=True, default=lambda: f"ATT_{uuid.uuid4().hex[:8].upper()}")
    
    # Attempt Information
    email = Column(String, nullable=False, index=True)
    ip_address = Column(String, nullable=False)
    user_agent = Column(Text, nullable=True)
    
    # Result
    success = Column(Boolean, default=False)
    failure_reason = Column(String, nullable=True)  # invalid_password, account_blocked, etc.
    
    # Security
    suspicious_activity = Column(Boolean, default=False)
    blocked_by_rate_limit = Column(Boolean, default=False)
    
    # Timestamp
    attempted_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<LoginAttempt {self.attempt_id}: {self.email} - {'Success' if self.success else 'Failed'}>"

class UserActivity(Base):
    __tablename__ = "user_activities"
    
    activity_id = Column(String, primary_key=True, default=lambda: f"ACT_{uuid.uuid4().hex[:8].upper()}")
    user_id = Column(String, nullable=False, index=True)
    
    # Activity Information
    activity_type = Column(String, nullable=False)  # login, payment, service_use, etc.
    description = Column(Text, nullable=True)
    activity_metadata = Column(Text, nullable=True)  # JSON string with additional data
    
    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Activity {self.activity_id}: {self.user_id} - {self.activity_type}>"