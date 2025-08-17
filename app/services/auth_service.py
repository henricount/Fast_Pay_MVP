import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import bcrypt
import re
import json

from app.models.auth_models import User, UserSession, LoginAttempt, UserActivity
from app.models.auth_models import UserRole, UserStatus, VerificationStatus
from app.models.auth_schemas import UserRegistrationRequest, LoginRequest

class AuthenticationService:
    def __init__(self):
        self.jwt_secret = "FAST_PAY_JWT_SECRET_KEY_2024"  # In production, use environment variable
        self.jwt_algorithm = "HS256"
        self.access_token_expire_hours = 1
        self.refresh_token_expire_days = 30
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def generate_jwt_token(self, user_id: str, token_type: str = "access") -> Tuple[str, datetime]:
        """Generate JWT access or refresh token"""
        now = datetime.utcnow()
        
        if token_type == "access":
            expire_time = now + timedelta(hours=self.access_token_expire_hours)
        else:  # refresh token
            expire_time = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "user_id": user_id,
            "type": token_type,
            "iat": now,
            "exp": expire_time
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token, expire_time

    def verify_jwt_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check token type
            if payload.get('type') != token_type:
                return None
                
            # Check expiration
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                return None
                
            return payload
        except jwt.InvalidTokenError:
            return None

    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is strong"

    def generate_verification_token(self) -> str:
        """Generate secure verification token"""
        return secrets.token_urlsafe(32)

    def generate_verification_code(self) -> str:
        """Generate 6-digit verification code"""
        return f"{secrets.randbelow(900000) + 100000:06d}"

    def register_user(self, registration_data: UserRegistrationRequest, db: Session) -> Tuple[bool, str, Optional[User]]:
        """Register a new user"""
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(
                or_(User.email == registration_data.email, User.phone == registration_data.phone)
            ).first()
            
            if existing_user:
                if existing_user.email == registration_data.email:
                    return False, "Email address already registered", None
                else:
                    return False, "Phone number already registered", None
            
            # Validate password strength
            is_strong, message = self.validate_password_strength(registration_data.password)
            if not is_strong:
                return False, message, None
            
            # Create new user
            hashed_password = self.hash_password(registration_data.password)
            
            # Convert Pydantic enum to SQLAlchemy enum
            from app.models.auth_models import UserRole as SQLUserRole
            role_mapping = {
                "CITIZEN": SQLUserRole.CITIZEN,
                "MERCHANT": SQLUserRole.MERCHANT,
                "GOVERNMENT": SQLUserRole.GOVERNMENT,
                "ADMIN": SQLUserRole.ADMIN
            }
            
            new_user = User(
                email=registration_data.email.lower(),
                phone=registration_data.phone,
                password_hash=hashed_password,
                first_name=registration_data.first_name,
                last_name=registration_data.last_name,
                id_number=registration_data.id_number,
                date_of_birth=registration_data.date_of_birth,
                region=registration_data.region.value if registration_data.region else None,
                city=registration_data.city,
                address=registration_data.address,
                postal_code=registration_data.postal_code,
                role=role_mapping[registration_data.role.value],
                email_verification_token=self.generate_verification_token(),
                phone_verification_code=self.generate_verification_code()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # Log registration activity
            self.log_user_activity(new_user.user_id, "user_registered", "New user account created", db)
            
            return True, "User registered successfully", new_user
            
        except Exception as e:
            db.rollback()
            return False, f"Registration failed: {str(e)}", None

    def authenticate_user(self, login_data: LoginRequest, ip_address: str, user_agent: str, db: Session) -> Tuple[bool, str, Optional[Dict]]:
        """Authenticate user login"""
        try:
            # Log login attempt
            self.log_login_attempt(login_data.email, ip_address, user_agent, False, None, db)
            
            # Find user
            user = db.query(User).filter(User.email == login_data.email.lower()).first()
            
            if not user:
                self.log_login_attempt(login_data.email, ip_address, user_agent, False, "user_not_found", db)
                return False, "Invalid email or password", None
            
            # Check account status
            if user.status == UserStatus.BLOCKED:
                self.log_login_attempt(login_data.email, ip_address, user_agent, False, "account_blocked", db)
                return False, "Account is blocked. Please contact support.", None
            
            if user.status == UserStatus.SUSPENDED:
                self.log_login_attempt(login_data.email, ip_address, user_agent, False, "account_suspended", db)
                return False, "Account is suspended. Please contact support.", None
            
            # Check for too many failed attempts
            if user.failed_login_attempts >= self.max_failed_attempts:
                self.log_login_attempt(login_data.email, ip_address, user_agent, False, "too_many_attempts", db)
                return False, f"Account locked due to {self.max_failed_attempts} failed login attempts. Try again later.", None
            
            # Verify password
            if not self.verify_password(login_data.password, user.password_hash):
                # Increment failed attempts
                user.failed_login_attempts += 1
                db.commit()
                
                self.log_login_attempt(login_data.email, ip_address, user_agent, False, "invalid_password", db)
                return False, "Invalid email or password", None
            
            # Check if email verification required
            if not user.email_verified and user.role != UserRole.ADMIN:
                return False, "Please verify your email address before logging in", None
            
            # Successful login
            user.failed_login_attempts = 0
            user.last_login = datetime.utcnow()
            
            # Generate tokens
            access_token, access_expires = self.generate_jwt_token(user.user_id, "access")
            refresh_token, refresh_expires = self.generate_jwt_token(user.user_id, "refresh")
            
            # Create session
            session = UserSession(
                user_id=user.user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=refresh_expires,
                user_agent=user_agent,
                ip_address=ip_address,
                device_fingerprint=self.generate_device_fingerprint(user_agent, ip_address)
            )
            
            db.add(session)
            db.commit()
            
            # Log successful login
            self.log_login_attempt(login_data.email, ip_address, user_agent, True, None, db)
            self.log_user_activity(user.user_id, "user_login", f"Successful login from {ip_address}", db)
            
            # Prepare response
            user_data = {
                "user_id": user.user_id,
                "email": user.email,
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.value,
                "status": user.status.value,
                "email_verified": user.email_verified,
                "phone_verified": user.phone_verified,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
            
            return True, "Login successful", {
                "user": user_data,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": int(self.access_token_expire_hours * 3600),
                "session_id": session.session_id
            }
            
        except Exception as e:
            db.rollback()
            return False, f"Login failed: {str(e)}", None

    def refresh_access_token(self, refresh_token: str, db: Session) -> Tuple[bool, str, Optional[Dict]]:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = self.verify_jwt_token(refresh_token, "refresh")
            if not payload:
                return False, "Invalid or expired refresh token", None
            
            user_id = payload["user_id"]
            
            # Find active session
            session = db.query(UserSession).filter(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token == refresh_token,
                    UserSession.is_active == True
                )
            ).first()
            
            if not session:
                return False, "Session not found or expired", None
            
            # Generate new access token
            new_access_token, access_expires = self.generate_jwt_token(user_id, "access")
            
            # Update session
            session.access_token = new_access_token
            session.last_activity = datetime.utcnow()
            
            db.commit()
            
            return True, "Token refreshed successfully", {
                "access_token": new_access_token,
                "expires_in": int(self.access_token_expire_hours * 3600)
            }
            
        except Exception as e:
            return False, f"Token refresh failed: {str(e)}", None

    def logout_user(self, user_id: str, session_id: Optional[str], logout_all: bool, db: Session) -> Tuple[bool, str]:
        """Logout user and invalidate sessions"""
        try:
            if logout_all:
                # Invalidate all user sessions
                db.query(UserSession).filter(
                    and_(UserSession.user_id == user_id, UserSession.is_active == True)
                ).update({"is_active": False})
            else:
                # Invalidate specific session
                if session_id:
                    db.query(UserSession).filter(
                        and_(
                            UserSession.user_id == user_id,
                            UserSession.session_id == session_id,
                            UserSession.is_active == True
                        )
                    ).update({"is_active": False})
            
            db.commit()
            
            # Log logout activity
            self.log_user_activity(user_id, "user_logout", "User logged out", db)
            
            return True, "Logged out successfully"
            
        except Exception as e:
            return False, f"Logout failed: {str(e)}"

    def verify_email(self, verification_token: str, db: Session) -> Tuple[bool, str]:
        """Verify user email"""
        try:
            user = db.query(User).filter(User.email_verification_token == verification_token).first()
            
            if not user:
                return False, "Invalid verification token"
            
            user.email_verified = True
            user.email_verification_token = None
            
            # Activate account if it was pending
            if user.status == UserStatus.PENDING:
                user.status = UserStatus.ACTIVE
            
            db.commit()
            
            self.log_user_activity(user.user_id, "email_verified", "Email address verified", db)
            
            return True, "Email verified successfully"
            
        except Exception as e:
            return False, f"Email verification failed: {str(e)}"

    def verify_phone(self, user_id: str, verification_code: str, db: Session) -> Tuple[bool, str]:
        """Verify user phone number"""
        try:
            user = db.query(User).filter(
                and_(
                    User.user_id == user_id,
                    User.phone_verification_code == verification_code
                )
            ).first()
            
            if not user:
                return False, "Invalid verification code"
            
            user.phone_verified = True
            user.phone_verification_code = None
            
            db.commit()
            
            self.log_user_activity(user.user_id, "phone_verified", "Phone number verified", db)
            
            return True, "Phone number verified successfully"
            
        except Exception as e:
            return False, f"Phone verification failed: {str(e)}"

    def generate_device_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """Generate device fingerprint"""
        fingerprint_data = f"{user_agent}:{ip_address}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

    def log_login_attempt(self, email: str, ip_address: str, user_agent: str, success: bool, failure_reason: Optional[str], db: Session):
        """Log login attempt"""
        attempt = LoginAttempt(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason
        )
        db.add(attempt)
        db.commit()

    def log_user_activity(self, user_id: str, activity_type: str, description: str, db: Session, metadata: Optional[Dict] = None):
        """Log user activity"""
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            activity_metadata=json.dumps(metadata) if metadata else None
        )
        db.add(activity)
        db.commit()

    def get_user_by_token(self, access_token: str, db: Session) -> Optional[User]:
        """Get user by access token"""
        try:
            payload = self.verify_jwt_token(access_token, "access")
            if not payload:
                return None
            
            user_id = payload["user_id"]
            
            # Verify session is still active
            session = db.query(UserSession).filter(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.access_token == access_token,
                    UserSession.is_active == True
                )
            ).first()
            
            if not session:
                return None
            
            # Update last activity
            session.last_activity = datetime.utcnow()
            db.commit()
            
            # Get user
            user = db.query(User).filter(User.user_id == user_id).first()
            return user
            
        except Exception:
            return None