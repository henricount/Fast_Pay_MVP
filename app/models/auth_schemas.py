from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from typing import Optional, List, Dict
from enum import Enum

# Enums
class UserRole(str, Enum):
    CITIZEN = "CITIZEN"
    MERCHANT = "MERCHANT"
    GOVERNMENT = "GOVERNMENT"
    ADMIN = "ADMIN"

class UserStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"

class EswatiniRegion(str, Enum):
    HHOHHO = "hhohho"
    MANZINI = "manzini"
    SHISELWENI = "shiselweni"
    LUBOMBO = "lubombo"

# Registration Schemas
class UserRegistrationRequest(BaseModel):
    email: str = Field(..., example="john.dlamini@example.com")
    phone: str = Field(..., example="+26876543210")
    password: str = Field(..., min_length=8, example="SecurePass123!")
    confirm_password: str = Field(..., example="SecurePass123!")
    
    # Personal Information
    first_name: str = Field(..., min_length=2, max_length=50, example="John")
    last_name: str = Field(..., min_length=2, max_length=50, example="Dlamini")
    id_number: Optional[str] = Field(None, example="8912345678901")
    date_of_birth: Optional[date] = Field(None, example="1989-12-15")
    
    # Address
    region: Optional[EswatiniRegion] = Field(None, example="hhohho")
    city: Optional[str] = Field(None, example="Mbabane")
    address: Optional[str] = Field(None, example="123 Allister Miller Street")
    postal_code: Optional[str] = Field(None, example="H100")
    
    # Role
    role: UserRole = Field(default=UserRole.CITIZEN, example="CITIZEN")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        # Basic email validation
        if '@' not in v or '.' not in v:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('phone')
    def validate_phone(cls, v):
        # Eswatini phone number validation
        v = v.replace(' ', '').replace('-', '')
        if not v.startswith('+268') and not v.startswith('268'):
            raise ValueError('Phone number must be Eswatini number (+268)')
        if len(v.replace('+268', '').replace('268', '')) != 8:
            raise ValueError('Invalid Eswatini phone number format')
        return v
    
    @validator('id_number')
    def validate_id_number(cls, v):
        if v and len(v) != 13:
            raise ValueError('Eswatini ID number must be 13 digits')
        return v

# Authentication Schemas
class LoginRequest(BaseModel):
    email: str = Field(..., example="john.dlamini@example.com")
    password: str = Field(..., example="SecurePass123!")
    remember_me: bool = Field(default=False, example=False)

class LoginResponse(BaseModel):
    success: bool = Field(..., example=True)
    message: str = Field(..., example="Login successful")
    user: Optional[Dict] = Field(..., example={})  # Will be populated with UserProfile data
    access_token: str = Field(..., example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...")
    refresh_token: str = Field(..., example="refresh_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...")
    expires_in: int = Field(..., example=3600)

class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., example="refresh_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...")

class TokenRefreshResponse(BaseModel):
    access_token: str = Field(..., example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...")
    expires_in: int = Field(..., example=3600)

# User Profile Schemas
class UserProfile(BaseModel):
    user_id: str = Field(..., example="USER_ABC12345")
    email: str = Field(..., example="john.dlamini@example.com")
    phone: str = Field(..., example="+26876543210")
    first_name: str = Field(..., example="John")
    last_name: str = Field(..., example="Dlamini")
    role: UserRole = Field(..., example="citizen")
    status: UserStatus = Field(..., example="active")
    email_verified: bool = Field(..., example=True)
    phone_verified: bool = Field(..., example=True)
    created_at: datetime = Field(..., example="2024-08-15T10:30:00Z")
    last_login: Optional[datetime] = Field(None, example="2024-08-15T15:45:00Z")

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone: Optional[str] = Field(None)
    region: Optional[EswatiniRegion] = Field(None)
    city: Optional[str] = Field(None)
    address: Optional[str] = Field(None)
    postal_code: Optional[str] = Field(None)

# Password Management
class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., example="OldPassword123!")
    new_password: str = Field(..., min_length=8, example="NewSecurePass456!")
    confirm_new_password: str = Field(..., example="NewSecurePass456!")
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v

class PasswordResetRequest(BaseModel):
    email: str = Field(..., example="john.dlamini@example.com")

class PasswordResetConfirm(BaseModel):
    reset_token: str = Field(..., example="reset_abc123def456")
    new_password: str = Field(..., min_length=8, example="NewSecurePass789!")
    confirm_new_password: str = Field(..., example="NewSecurePass789!")
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

# Verification Schemas
class EmailVerificationRequest(BaseModel):
    verification_token: str = Field(..., example="email_verify_abc123")

class PhoneVerificationRequest(BaseModel):
    verification_code: str = Field(..., min_length=6, max_length=6, example="123456")

class ResendVerificationRequest(BaseModel):
    type: str = Field(..., example="email")  # "email" or "phone"

# Session Management
class SessionInfo(BaseModel):
    session_id: str = Field(..., example="SESS_abc123def456")
    device_info: Optional[str] = Field(None, example="Chrome on Windows")
    ip_address: Optional[str] = Field(None, example="192.168.1.100")
    created_at: datetime = Field(..., example="2024-08-15T10:30:00Z")
    last_activity: datetime = Field(..., example="2024-08-15T15:45:00Z")
    is_current: bool = Field(..., example=True)

class ActiveSessionsResponse(BaseModel):
    sessions: List[SessionInfo]
    total_count: int = Field(..., example=3)

class LogoutRequest(BaseModel):
    logout_all_devices: bool = Field(default=False, example=False)

# Security & Activity
class SecurityAlert(BaseModel):
    alert_id: str = Field(..., example="ALERT_ABC123")
    type: str = Field(..., example="suspicious_login")
    description: str = Field(..., example="Login from new device")
    severity: str = Field(..., example="medium")
    created_at: datetime = Field(..., example="2024-08-15T15:45:00Z")
    resolved: bool = Field(..., example=False)

class UserActivity(BaseModel):
    activity_id: str = Field(..., example="ACT_ABC123")
    activity_type: str = Field(..., example="payment_made")
    description: str = Field(..., example="Payment of E450.00 to EWSC")
    created_at: datetime = Field(..., example="2024-08-15T15:45:00Z")

class ActivityHistoryResponse(BaseModel):
    activities: List[UserActivity]
    total_count: int = Field(..., example=25)
    page: int = Field(..., example=1)
    pages: int = Field(..., example=3)

# Registration Response
class RegistrationResponse(BaseModel):
    success: bool = Field(..., example=True)
    message: str = Field(..., example="Registration successful. Please verify your email.")
    user_id: str = Field(..., example="USER_ABC12345")
    verification_required: bool = Field(..., example=True)

# Standard API Responses
class StandardResponse(BaseModel):
    success: bool = Field(..., example=True)
    message: str = Field(..., example="Operation completed successfully")

class ErrorResponse(BaseModel):
    success: bool = Field(default=False, example=False)
    error: str = Field(..., example="Authentication failed")
    details: Optional[str] = Field(None, example="Invalid email or password")

# Remove forward reference configuration as we've fixed the circular reference