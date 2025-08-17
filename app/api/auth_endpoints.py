from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.models.database import get_db
from app.models.auth_models import User, UserSession
from app.models.auth_schemas import (
    UserRegistrationRequest, RegistrationResponse, LoginRequest, LoginResponse,
    TokenRefreshRequest, TokenRefreshResponse, PasswordChangeRequest,
    PasswordResetRequest, PasswordResetConfirm, EmailVerificationRequest,
    PhoneVerificationRequest, ResendVerificationRequest, UserProfile,
    UserProfileUpdate, LogoutRequest, StandardResponse, ErrorResponse,
    ActiveSessionsResponse, ActivityHistoryResponse
)
from app.services.auth_service import AuthenticationService

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
auth_service = AuthenticationService()
security = HTTPBearer()

def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

def get_user_agent(request: Request) -> str:
    """Get user agent string"""
    return request.headers.get("User-Agent", "Unknown")

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_user_by_token(token, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# Registration & Authentication

@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    registration_data: UserRegistrationRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user account"""
    success, message, user = auth_service.register_user(registration_data, db)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return RegistrationResponse(
        success=True,
        message=message,
        user_id=user.user_id,
        verification_required=True
    )

@router.post("/login", response_model=LoginResponse)
async def login_user(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and create session"""
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    success, message, auth_data = auth_service.authenticate_user(
        login_data, ip_address, user_agent, db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
    
    return LoginResponse(
        success=True,
        message=message,
        user=auth_data["user"],
        access_token=auth_data["access_token"],
        refresh_token=auth_data["refresh_token"],
        expires_in=auth_data["expires_in"]
    )

@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    success, message, token_data = auth_service.refresh_access_token(
        refresh_data.refresh_token, db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
    
    return TokenRefreshResponse(
        access_token=token_data["access_token"],
        expires_in=token_data["expires_in"]
    )

@router.post("/logout", response_model=StandardResponse)
async def logout_user(
    logout_data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user and invalidate session(s)"""
    success, message = auth_service.logout_user(
        current_user.user_id, None, logout_data.logout_all_devices, db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return StandardResponse(success=True, message=message)

# User Profile Management

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserProfile(
        user_id=current_user.user_id,
        email=current_user.email,
        phone=current_user.phone,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        status=current_user.status,
        email_verified=current_user.email_verified,
        phone_verified=current_user.phone_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.put("/profile", response_model=StandardResponse)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    try:
        # Update fields if provided
        if profile_data.first_name:
            current_user.first_name = profile_data.first_name
        if profile_data.last_name:
            current_user.last_name = profile_data.last_name
        if profile_data.phone:
            # Validate new phone number doesn't exist
            existing = db.query(User).filter(
                User.phone == profile_data.phone,
                User.user_id != current_user.user_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already in use"
                )
            current_user.phone = profile_data.phone
            current_user.phone_verified = False  # Require re-verification
        if profile_data.region:
            current_user.region = profile_data.region.value
        if profile_data.city:
            current_user.city = profile_data.city
        if profile_data.address:
            current_user.address = profile_data.address
        if profile_data.postal_code:
            current_user.postal_code = profile_data.postal_code
        
        db.commit()
        
        # Log activity
        auth_service.log_user_activity(
            current_user.user_id, "profile_updated", "User profile updated", db
        )
        
        return StandardResponse(success=True, message="Profile updated successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )

# Password Management

@router.post("/change-password", response_model=StandardResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not auth_service.verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    is_strong, message = auth_service.validate_password_strength(password_data.new_password)
    if not is_strong:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    # Update password
    current_user.password_hash = auth_service.hash_password(password_data.new_password)
    db.commit()
    
    # Log activity
    auth_service.log_user_activity(
        current_user.user_id, "password_changed", "User password changed", db
    )
    
    return StandardResponse(success=True, message="Password changed successfully")

@router.post("/reset-password", response_model=StandardResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset"""
    user = db.query(User).filter(User.email == reset_data.email.lower()).first()
    
    if user:
        # Generate reset token
        reset_token = auth_service.generate_verification_token()
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        # Log activity
        auth_service.log_user_activity(
            user.user_id, "password_reset_requested", "Password reset requested", db
        )
        
        # TODO: Send email with reset token
        # In production, you would send an email here
    
    # Always return success for security (don't reveal if email exists)
    return StandardResponse(
        success=True,
        message="If the email exists, password reset instructions have been sent"
    )

@router.post("/reset-password/confirm", response_model=StandardResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    user = db.query(User).filter(
        User.password_reset_token == reset_data.reset_token
    ).first()
    
    if not user or user.password_reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Validate new password
    is_strong, message = auth_service.validate_password_strength(reset_data.new_password)
    if not is_strong:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    # Update password
    user.password_hash = auth_service.hash_password(reset_data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.failed_login_attempts = 0  # Reset failed attempts
    db.commit()
    
    # Log activity
    auth_service.log_user_activity(
        user.user_id, "password_reset_completed", "Password reset completed", db
    )
    
    return StandardResponse(success=True, message="Password reset successfully")

# Email & Phone Verification

@router.post("/verify-email", response_model=StandardResponse)
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify email address"""
    success, message = auth_service.verify_email(verification_data.verification_token, db)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return StandardResponse(success=True, message=message)

@router.post("/verify-phone", response_model=StandardResponse)
async def verify_phone(
    verification_data: PhoneVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify phone number"""
    success, message = auth_service.verify_phone(
        current_user.user_id, verification_data.verification_code, db
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return StandardResponse(success=True, message=message)

@router.post("/resend-verification", response_model=StandardResponse)
async def resend_verification(
    resend_data: ResendVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend verification code/token"""
    if resend_data.type == "email":
        if current_user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Generate new token
        current_user.email_verification_token = auth_service.generate_verification_token()
        db.commit()
        
        # TODO: Send email
        message = "Verification email sent"
        
    elif resend_data.type == "phone":
        if current_user.phone_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone already verified"
            )
        
        # Generate new code
        current_user.phone_verification_code = auth_service.generate_verification_code()
        db.commit()
        
        # TODO: Send SMS
        message = "Verification SMS sent"
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification type"
        )
    
    return StandardResponse(success=True, message=message)

# Session Management

@router.get("/sessions", response_model=ActiveSessionsResponse)
async def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's active sessions"""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.user_id,
        UserSession.is_active == True
    ).order_by(UserSession.last_activity.desc()).all()
    
    session_list = []
    for session in sessions:
        session_list.append({
            "session_id": session.session_id,
            "device_info": session.user_agent,
            "ip_address": session.ip_address,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "is_current": True  # You could detect current session
        })
    
    return ActiveSessionsResponse(sessions=session_list, total_count=len(sessions))

# Account Status

@router.get("/status", response_model=dict)
async def get_account_status(current_user: User = Depends(get_current_user)):
    """Get account verification and status information"""
    return {
        "user_id": current_user.user_id,
        "status": current_user.status.value,
        "verification_status": current_user.verification_status.value,
        "email_verified": current_user.email_verified,
        "phone_verified": current_user.phone_verified,
        "verification_required": not (current_user.email_verified and current_user.phone_verified),
        "account_complete": (
            current_user.email_verified and 
            current_user.phone_verified and 
            current_user.status == "active"
        )
    }